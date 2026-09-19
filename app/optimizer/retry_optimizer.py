"""
Expected Value Schedule Optimizer for Algorithmic Dunning.

Replaces naive static heuristics with dynamic candidate grid search:
- Search space: Upcoming 72 hours in 2-hour increments across all available gateways (S = T x G).
- Circuit breaker pre-execution: Immediately routes hard declines and exhausted retries to
  customer self-serve dunning (forcing P=0.0 and EV=0.0 without ML overhead).
- Net Expected Recovery Value (EV) evaluation:
    EV(t, g) = P(success | t, g, x) * Invoice Amount - Gateway Auth Fee(g) - Fatigue Cost
- Termination recommendation if max EV <= 0 to preserve merchant margin.
- Recovery Lift calculation: Delta between winning P(success | t*, g*) and naive immediate retry P(success | t0, g0).
- Local SHAP attribution and natural language dunning rationale generation.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.config import (
    BASE_FATIGUE_COST,
    DAYS_OF_WEEK,
    FATIGUE_COST_PER_ATTEMPT,
    FEATURE_COLUMNS,
    GATEWAY_AUTH_FEES,
    PAYMENT_GATEWAYS,
    calculate_gateway_fee,
)
from app.data.generator import compute_banking_settlement_window, compute_payday_proximity
from app.domain.bank_network_map import get_bank_pattern
from app.domain.decline_taxonomy import (
    DeclineCategory,
    DunningRoute,
    evaluate_circuit_breaker,
)
from app.ml.explain import explain_local_schedule
from app.ml.model import RetryModel


@dataclass
class RetryCandidateSlot:
    payment_gateway: str
    recommended_retry_datetime_utc: str
    recommended_retry_datetime_local: str
    local_timezone: str
    hour_of_day: int
    day_of_week: str
    is_payday_proximity: int
    is_banking_settlement_window: int
    predicted_success_probability: float
    expected_recovery_value_usd: float
    gateway_auth_fee_usd: float
    fatigue_cost_usd: float


class RetryOptimizer:
    """
    Optimizes payment retry schedules to maximize Net Expected Recovery Value.
    """

    def __init__(self, model: RetryModel):
        self.model = model

    def _build_candidate_matrix(
        self,
        decline_code: str,
        issuing_bank: str,
        bin_country: str,
        card_type: str,
        card_network: str,
        invoice_amount_usd: float,
        retry_attempt_number: int,
        elapsed_days_since_first_decline: float,
        now_local: datetime,
        min_wait_hours: Optional[int],
    ) -> pd.DataFrame:
        """
        Builds candidate search matrix S = T x G for the next 72 hours in 2-hour increments
        across all configured payment acquiring gateways.
        """
        min_hours = min_wait_hours or 0
        earliest_time = now_local + timedelta(hours=min_hours)

        # 72 hours in 2-hour increments (0, 2, 4, ..., 72)
        hour_offsets = list(range(0, 74, 2))

        rows = []
        for gateway in PAYMENT_GATEWAYS:
            for offset in hour_offsets:
                candidate_dt = now_local + timedelta(hours=offset)

                # Skip candidate slots that violate minimum cooldown (except offset=0 for baseline)
                if offset > 0 and candidate_dt < earliest_time:
                    continue

                additional_elapsed_days = offset / 24.0
                total_elapsed_days = elapsed_days_since_first_decline + additional_elapsed_days

                day_of_month = candidate_dt.day
                day_of_week = candidate_dt.weekday()
                hour_of_day = candidate_dt.hour

                is_payday = compute_payday_proximity(day_of_month, day_of_week)
                is_settlement = compute_banking_settlement_window(hour_of_day)

                rows.append({
                    "decline_code": decline_code,
                    "issuing_bank": issuing_bank,
                    "bin_country": bin_country,
                    "card_type": card_type,
                    "card_network": card_network,
                    "invoice_amount_usd": float(invoice_amount_usd),
                    "day_of_month": day_of_month,
                    "day_of_week": day_of_week,
                    "hour_of_day": hour_of_day,
                    "is_payday_proximity": is_payday,
                    "is_banking_settlement_window": is_settlement,
                    "current_gateway": gateway,
                    "retry_attempt_number": retry_attempt_number,
                    "elapsed_days_since_first_decline": round(total_elapsed_days, 4),
                    "candidate_local_dt": candidate_dt,
                    "hour_offset": offset,
                })

        return pd.DataFrame(rows)

    def optimize(
        self,
        decline_code: str,
        issuing_bank: str,
        invoice_amount_usd: float = 49.00,
        card_type: str = "debit",
        card_network: str = "visa",
        current_gateway: str = "stripe",
        retry_attempt_number: int = 1,
        elapsed_days_since_first_decline: float = 0.0,
        bin_country: Optional[str] = None,
        reference_time_utc: Optional[datetime] = None,
        top_n: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes deterministic circuit breaker, candidate grid evaluation, EV maximization,
        recovery lift computation, and local SHAP explainability.
        """
        # 1. Deterministic Circuit Breaker Check
        cb_decision = evaluate_circuit_breaker(decline_code, retry_attempt_number)
        bank_pattern = get_bank_pattern(issuing_bank)
        resolved_country = bin_country or bank_pattern.get("country", "US")

        if not cb_decision.allow_ml_inference or cb_decision.is_unrecoverable:
            return {
                "retryable": False,
                "terminal_decision": True,
                "circuit_breaker": cb_decision.to_dict(),
                "reason": cb_decision.reason,
                "suggested_action": cb_decision.suggested_action,
                "routing_action": cb_decision.routing_action,
                "winning_schedule": None,
                "expected_recovery_value_usd": 0.0,
                "predicted_success_probability": 0.0,
                "recovery_lift": 0.0,
                "recovery_lift_percentage": 0.0,
                "baseline_probability": 0.0,
                "recommendations": [],
                "shap_explanation": None,
            }

        # 2. Setup Timezone and Reference Clock
        tz = ZoneInfo(bank_pattern["timezone"])
        if reference_time_utc is not None:
            now_local = reference_time_utc.astimezone(tz)
        else:
            now_local = datetime.now(tz)

        # 3. Generate Search Matrix (Next 72h in 2h increments across gateways)
        candidates_df = self._build_candidate_matrix(
            decline_code=decline_code,
            issuing_bank=issuing_bank,
            bin_country=resolved_country,
            card_type=card_type,
            card_network=card_network,
            invoice_amount_usd=invoice_amount_usd,
            retry_attempt_number=retry_attempt_number,
            elapsed_days_since_first_decline=elapsed_days_since_first_decline,
            now_local=now_local,
            min_wait_hours=cb_decision.min_wait_hours,
        )

        if candidates_df.empty:
            return {
                "retryable": False,
                "terminal_decision": True,
                "circuit_breaker": cb_decision.to_dict(),
                "reason": "No viable retry slots found within the search matrix.",
                "suggested_action": "Expand the search horizon or verify cooldown parameters.",
                "routing_action": cb_decision.routing_action,
                "winning_schedule": None,
                "expected_recovery_value_usd": 0.0,
                "predicted_success_probability": 0.0,
                "recovery_lift": 0.0,
                "recovery_lift_percentage": 0.0,
                "baseline_probability": 0.0,
                "recommendations": [],
                "shap_explanation": None,
            }

        # 4. Predict Calibrated Probabilities P(success | t, g, x)
        proba = self.model.predict_proba(candidates_df[FEATURE_COLUMNS])
        candidates_df["predicted_success_probability"] = proba

        # 5. Calculate Net Expected Recovery Value EV(t, g)
        # EV = P(success | t, g) * Amount - AuthFee(g) - FatigueCost(k)
        fatigue_cost = float(
            BASE_FATIGUE_COST + FATIGUE_COST_PER_ATTEMPT * max(0, retry_attempt_number - 1)
        )

        candidates_df["gateway_auth_fee"] = candidates_df["current_gateway"].map(
            lambda g: calculate_gateway_fee(g, float(invoice_amount_usd))
        )
        candidates_df["fatigue_cost"] = fatigue_cost
        candidates_df["expected_recovery_value"] = (
            candidates_df["predicted_success_probability"] * float(invoice_amount_usd)
            - candidates_df["gateway_auth_fee"]
            - candidates_df["fatigue_cost"]
        )

        # 6. Baseline Naive Immediate Retry (t0, g0)
        baseline_slice = candidates_df[
            (candidates_df["hour_offset"] == 0)
            & (candidates_df["current_gateway"] == current_gateway)
        ]
        if not baseline_slice.empty:
            baseline_row = baseline_slice.iloc[0:1]
            baseline_prob = float(baseline_row["predicted_success_probability"].iloc[0])
            baseline_ev = float(baseline_row["expected_recovery_value"].iloc[0])
        else:
            # Construct synthetic baseline row if offset 0 was filtered
            baseline_row = pd.DataFrame([{
                "decline_code": decline_code,
                "issuing_bank": issuing_bank,
                "bin_country": resolved_country,
                "card_type": card_type,
                "card_network": card_network,
                "invoice_amount_usd": float(invoice_amount_usd),
                "day_of_month": now_local.day,
                "day_of_week": now_local.weekday(),
                "hour_of_day": now_local.hour,
                "is_payday_proximity": compute_payday_proximity(now_local.day, now_local.weekday()),
                "is_banking_settlement_window": compute_banking_settlement_window(now_local.hour),
                "current_gateway": current_gateway,
                "retry_attempt_number": retry_attempt_number,
                "elapsed_days_since_first_decline": elapsed_days_since_first_decline,
            }])
            baseline_prob = float(self.model.predict_proba(baseline_row[FEATURE_COLUMNS])[0])
            baseline_fee = calculate_gateway_fee(current_gateway, float(invoice_amount_usd))
            baseline_ev = float(baseline_prob * float(invoice_amount_usd) - baseline_fee - fatigue_cost)

        # 7. Select Winning Schedule (t*, g*) Maximizing EV
        sorted_candidates = candidates_df.sort_values("expected_recovery_value", ascending=False)
        winning_candidate = sorted_candidates.iloc[0:1]
        best_ev = float(winning_candidate["expected_recovery_value"].iloc[0])
        best_prob = float(winning_candidate["predicted_success_probability"].iloc[0])

        # Terminal Decision Check: If max EV <= 0, recommend terminating retries
        is_terminal = best_ev <= 0.0
        if is_terminal:
            suggested_action = (
                f"Terminate retries. Net Expected Recovery Value is negative (${best_ev:.2f}). "
                "Retrying incurs auth fees and card brand fatigue exceeding expected recovery."
            )
        else:
            suggested_action = (
                f"Execute retry at optimal schedule via {winning_candidate['current_gateway'].iloc[0].capitalize()}. "
                f"Projected Net EV: +${best_ev:.2f}."
            )

        # 8. Recovery Lift vs Baseline
        recovery_lift = float(best_prob - baseline_prob)
        recovery_lift_pct = float((recovery_lift / (baseline_prob + 1e-6)) * 100.0)

        # 9. Local SHAP Attribution & Natural Language Reasoning
        shap_explanation = None
        if not is_terminal and self.model.base_model is not None:
            try:
                shap_explanation = explain_local_schedule(
                    retry_model=self.model,
                    winning_row=winning_candidate,
                    initial_row=baseline_row,
                    top_k=3,
                )
            except Exception as e:
                print(f"[Optimizer] Local SHAP explanation warning: {e}")

        # 10. Assemble Structured Recommendations (Ranked Top-N)
        # Deduplicate across distinct days/gateways to present diverse options
        deduped_candidates = (
            sorted_candidates.drop_duplicates(subset=["current_gateway", "hour_of_day"])
            .head(top_n)
        )

        recommendations: List[Dict[str, Any]] = []
        for _, row in deduped_candidates.iterrows():
            loc_dt: datetime = row["candidate_local_dt"]
            utc_dt = loc_dt.astimezone(ZoneInfo("UTC"))
            slot = RetryCandidateSlot(
                payment_gateway=row["current_gateway"],
                recommended_retry_datetime_utc=utc_dt.isoformat(),
                recommended_retry_datetime_local=loc_dt.isoformat(),
                local_timezone=bank_pattern["timezone"],
                hour_of_day=int(row["hour_of_day"]),
                day_of_week=DAYS_OF_WEEK[int(row["day_of_week"])],
                is_payday_proximity=int(row["is_payday_proximity"]),
                is_banking_settlement_window=int(row["is_banking_settlement_window"]),
                predicted_success_probability=round(float(row["predicted_success_probability"]), 4),
                expected_recovery_value_usd=round(float(row["expected_recovery_value"]), 2),
                gateway_auth_fee_usd=round(float(row["gateway_auth_fee"]), 2),
                fatigue_cost_usd=round(float(row["fatigue_cost"]), 2),
            )
            recommendations.append(asdict(slot))

        winning_slot = recommendations[0] if recommendations else None

        return {
            "retryable": not is_terminal,
            "terminal_decision": is_terminal,
            "circuit_breaker": cb_decision.to_dict(),
            "routing_action": cb_decision.routing_action,
            "reason": cb_decision.reason,
            "suggested_action": suggested_action,
            "winning_schedule": winning_slot,
            "expected_recovery_value_usd": round(best_ev, 2),
            "predicted_success_probability": round(best_prob, 4),
            "recovery_lift": round(recovery_lift, 4),
            "recovery_lift_percentage": round(recovery_lift_pct, 1),
            "baseline_probability": round(baseline_prob, 4),
            "baseline_ev_usd": round(baseline_ev, 2),
            "recommendations": recommendations,
            "shap_explanation": shap_explanation,
        }

