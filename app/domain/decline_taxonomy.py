"""
Strict Decline Taxonomy & Circuit Breaker.
Localized for Indian RBI e-Mandates, UPI AutoPay, and Bank CBS Outages.

Categorizes raw processor decline codes into deterministic operational classes
and executes a rule-based circuit breaker BEFORE any machine learning inference:

1. Hard Declines:
   - stolen_card, lost_card, account_closed, fraudulent, expired_card, invalid_cvv
   - upi_mandate_revoked: User revoked recurring mandate on PhonePe/GPay/BHIM (Permanently unrecoverable).
   - rbi_afa_limit_exceeded: RBI circular limit exceeded (> ₹15,000) requiring mandatory step-up OTP.
   Never retry. Force success probability to 0.0, flag as UNRECOVERABLE, and route directly
   to customer self-serve dunning.

2. Soft Liquidity Declines (insufficient_funds, card_velocity_exceeded):
   Route to Indian salary/payroll replenishment scheduler (end-of-month / 1st-5th / 7th-10th).

3. Soft Technical/Transient Declines:
   - network_error, gateway_timeout, issuer_unavailable, processing_error
   - bank_server_down: Core Banking Solution (CBS) downtime (notorious with SBI/HDFC at 00:00-04:00 IST).
   Requires exponential backoff to morning daytime operational hours (09:00-18:00 IST).

4. Soft Authorization Declines (do_not_honor, generic_decline):
   Route to daytime active hours and alternate acquiring gateway failover (Razorpay <-> Cashfree <-> PayU).
"""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional

from app.config import MAX_RETRY_ATTEMPTS


class DeclineCategory(str, Enum):
    HARD_DECLINE = "hard_decline"
    SOFT_LIQUIDITY = "soft_liquidity"
    SOFT_TECHNICAL = "soft_technical"
    SOFT_AUTHORIZATION = "soft_authorization"


class DunningRoute(str, Enum):
    CUSTOMER_SELF_SERVE_DUNNING = "customer_self_serve_dunning"
    PAYROLL_BALANCE_SCHEDULER = "payroll_balance_scheduler"
    SHORT_INTERVAL_EXPONENTIAL_BACKOFF = "short_interval_exponential_backoff"
    DAYTIME_FAILOVER_SCHEDULER = "daytime_failover_scheduler"


@dataclass
class CircuitBreakerDecision:
    allow_ml_inference: bool
    is_unrecoverable: bool
    force_probability_zero: bool
    routing_action: str
    decline_category: str
    reason: str
    suggested_action: str
    backoff_intervals_minutes: Optional[List[int]] = None
    min_wait_hours: Optional[int] = None

    def to_dict(self) -> dict:
        return asdict(self)


DECLINE_TAXONOMY: Dict[str, dict] = {
    # --- Hard Declines (Never retry, direct customer action required) ---
    "upi_mandate_revoked": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "mandate_lifecycle",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "UPI AutoPay mandate was revoked by the customer in their UPI app (PhonePe/GPay/Paytm). Retries are illegal under NPCI guidelines.",
    },
    "rbi_afa_limit_exceeded": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "regulatory_compliance",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "RBI e-Mandate AFA limit exceeded (> INR 15,000). Automated recurring execution prohibited without step-up OTP authentication.",
    },
    "stolen_card": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "fraud_security",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "Card reported stolen. Retrying triggers severe card brand network fines and gateway penalties.",
    },
    "lost_card": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "fraud_security",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "Card reported lost by cardholder. Unrecoverable via automated payment retries.",
    },
    "account_closed": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "account_lifecycle",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "Cardholder account permanently closed. Fresh payment method or new UPI mandate required.",
    },
    "fraudulent": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "fraud_security",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "Issuer risk engine or NPCI confirmed fraudulent activity. Immediate terminal block.",
    },
    "expired_card": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "card_lifecycle",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "Card expired. No automated retry can succeed; card update required.",
    },
    "invalid_cvv": {
        "category": DeclineCategory.HARD_DECLINE.value,
        "reason_group": "customer_action_required",
        "retryable": False,
        "is_unrecoverable": True,
        "route": DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
        "min_wait_hours": None,
        "description": "CVV mismatch. Cardholder must re-enter security code.",
    },

    # --- Soft Liquidity Declines (Payroll / Balance Replenishment) ---
    "insufficient_funds": {
        "category": DeclineCategory.SOFT_LIQUIDITY.value,
        "reason_group": "funds_availability",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.PAYROLL_BALANCE_SCHEDULER.value,
        "min_wait_hours": 12,
        "description": "Lacking account balance. High correlation with Indian salary disbursement cycles (end-of-month, 1st, 7th).",
    },
    "card_velocity_exceeded": {
        "category": DeclineCategory.SOFT_LIQUIDITY.value,
        "reason_group": "issuer_limits",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.PAYROLL_BALANCE_SCHEDULER.value,
        "min_wait_hours": 24,
        "description": "Daily or rolling card/UPI spending velocity hit. Clears with midnight calendar reset.",
    },

    # --- Soft Technical / Transient Declines (Exponential Backoff to Daytime) ---
    "bank_server_down": {
        "category": DeclineCategory.SOFT_TECHNICAL.value,
        "reason_group": "core_banking_downtime",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
        "backoff_intervals_minutes": [60, 180, 360],
        "min_wait_hours": 4,
        "description": "Issuer CBS (Core Banking Solution) server down or in nightly batch maintenance (common with SBI/HDFC at 00:00-04:00 IST). Requires exponential backoff to daytime hours.",
    },
    "network_error": {
        "category": DeclineCategory.SOFT_TECHNICAL.value,
        "reason_group": "technical_connectivity",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
        "backoff_intervals_minutes": [15, 60, 240],
        "min_wait_hours": 0,
        "description": "Network socket or TLS handshake timeout between gateway, NPCI switch, and issuer.",
    },
    "gateway_timeout": {
        "category": DeclineCategory.SOFT_TECHNICAL.value,
        "reason_group": "technical_connectivity",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
        "backoff_intervals_minutes": [15, 60, 240],
        "min_wait_hours": 0,
        "description": "Payment gateway processing timeout. Rapidly recoverable within minutes.",
    },
    "issuer_unavailable": {
        "category": DeclineCategory.SOFT_TECHNICAL.value,
        "reason_group": "technical_connectivity",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
        "backoff_intervals_minutes": [15, 60, 240],
        "min_wait_hours": 0,
        "description": "Issuing bank authorization switch offline for maintenance or peak traffic load.",
    },
    "processing_error": {
        "category": DeclineCategory.SOFT_TECHNICAL.value,
        "reason_group": "technical_connectivity",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
        "backoff_intervals_minutes": [15, 60, 240],
        "min_wait_hours": 0,
        "description": "Transient switch processing error. Safe to retry with exponential backoff.",
    },

    # --- Soft Authorization Declines (Daytime Active Hours & Gateway Failover) ---
    "do_not_honor": {
        "category": DeclineCategory.SOFT_AUTHORIZATION.value,
        "reason_group": "issuer_policy",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.DAYTIME_FAILOVER_SCHEDULER.value,
        "min_wait_hours": 4,
        "description": "Generic issuer block. Best retried during daytime customer-active hours (09:00-18:00 IST) or via alternate gateway failover.",
    },
    "generic_decline": {
        "category": DeclineCategory.SOFT_AUTHORIZATION.value,
        "reason_group": "issuer_policy",
        "retryable": True,
        "is_unrecoverable": False,
        "route": DunningRoute.DAYTIME_FAILOVER_SCHEDULER.value,
        "min_wait_hours": 4,
        "description": "General refusal. Recovers when routed through alternate acquiring gateways during daytime hours.",
    },
}

DECLINE_CODES: List[str] = list(DECLINE_TAXONOMY.keys())


def evaluate_circuit_breaker(
    decline_code: str,
    retry_attempt_number: int = 1,
) -> CircuitBreakerDecision:
    """
    Deterministic rule-based circuit breaker executed prior to any ML inference.

    - Hard Declines (stolen, lost, closed, fraudulent, upi_mandate_revoked, rbi_afa_limit_exceeded):
      Forces P=0.0, UNRECOVERABLE flag, and immediate customer self-serve dunning.
    - Max Attempts Exceeded: Trips circuit breaker to prevent card brand/NPCI penalties.
    - Soft Declines: Determines target scheduling path (liquidity, transient backoff, or daytime failover).
    """
    if decline_code not in DECLINE_TAXONOMY:
        raise KeyError(f"Unknown decline_code '{decline_code}'. Known codes: {DECLINE_CODES}")

    meta = DECLINE_TAXONOMY[decline_code]
    category = meta["category"]

    # 1. Check card brand / NPCI retry attempt ceiling
    if retry_attempt_number > MAX_RETRY_ATTEMPTS:
        return CircuitBreakerDecision(
            allow_ml_inference=False,
            is_unrecoverable=True,
            force_probability_zero=True,
            routing_action=DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
            decline_category=category,
            reason=f"Exceeded maximum allowed retry attempts ({MAX_RETRY_ATTEMPTS}). Customer fatigue limit reached.",
            suggested_action="Halt automated retries. Route to customer self-serve dunning portal to avoid gateway & network penalties.",
        )

    # 2. Hard Declines (including UPI mandate revoked and RBI AFA limit exceeded)
    if category == DeclineCategory.HARD_DECLINE.value:
        return CircuitBreakerDecision(
            allow_ml_inference=False,
            is_unrecoverable=True,
            force_probability_zero=True,
            routing_action=DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value,
            decline_category=category,
            reason=f"Hard decline: {meta['description']}",
            suggested_action="Do not retry. Route immediately to customer self-serve dunning to prevent network penalties and auth fees.",
        )

    # 3. Soft Liquidity Declines
    if category == DeclineCategory.SOFT_LIQUIDITY.value:
        return CircuitBreakerDecision(
            allow_ml_inference=True,
            is_unrecoverable=False,
            force_probability_zero=False,
            routing_action=DunningRoute.PAYROLL_BALANCE_SCHEDULER.value,
            decline_category=category,
            min_wait_hours=meta.get("min_wait_hours", 12),
            reason=meta["description"],
            suggested_action="Schedule retry aligned with Indian payroll disbursement cycles and morning banking settlement clearances.",
        )

    # 4. Soft Technical / Transient Declines (CBS downtimes, server down, network)
    if category == DeclineCategory.SOFT_TECHNICAL.value:
        return CircuitBreakerDecision(
            allow_ml_inference=True,
            is_unrecoverable=False,
            force_probability_zero=False,
            routing_action=DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value,
            decline_category=category,
            backoff_intervals_minutes=meta.get("backoff_intervals_minutes", [60, 180, 360]),
            min_wait_hours=meta.get("min_wait_hours", 0),
            reason=meta["description"],
            suggested_action="Route to exponential backoff windows, steering clear of midnight bank maintenance windows.",
        )

    # 5. Soft Authorization Declines
    return CircuitBreakerDecision(
        allow_ml_inference=True,
        is_unrecoverable=False,
        force_probability_zero=False,
        routing_action=DunningRoute.DAYTIME_FAILOVER_SCHEDULER.value,
        decline_category=category,
        min_wait_hours=meta.get("min_wait_hours", 4),
        reason=meta["description"],
        suggested_action="Route to daytime active hours (09:00-18:00 IST) and evaluate alternate gateway failover (Razorpay/Cashfree/PayU).",
    )


def categorize_decline_code(decline_code: str) -> dict:
    """Returns the full taxonomy entry for a decline_code, raising if unknown."""
    if decline_code not in DECLINE_TAXONOMY:
        raise KeyError(f"Unknown decline_code '{decline_code}'. Known codes: {DECLINE_CODES}")
    return {"decline_code": decline_code, **DECLINE_TAXONOMY[decline_code]}


def is_retryable(decline_code: str) -> bool:
    return DECLINE_TAXONOMY[decline_code]["retryable"]


def min_wait_hours(decline_code: str) -> Optional[int]:
    return DECLINE_TAXONOMY[decline_code]["min_wait_hours"]
