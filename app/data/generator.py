"""
High-Fidelity Synthetic Data Generator for Algorithmic Dunning & Retry Optimization.
Localized specifically for the Indian financial ecosystem:
- Acquiring Gateways: razorpay, payu, cashfree, billdesk
- Payment Methods / Rails: upi_autopay, rupay, visa, mastercard
- Issuing Banks & UPI Apps: hdfc_bank, sbi, icici_bank, axis_bank, kotak_mahindra, phonepe, gpay, paytm, cred
- Decline Codes: upi_mandate_revoked, rbi_afa_limit_exceeded, bank_server_down, insufficient_funds, etc.
- Subscription Services: swiggy_one (₹149), zomato_gold (₹999), hotstar_premium (₹1499), jiocinema_family (₹89), zerodha_streak (₹690)
- Explicit Core Banking CBS maintenance interactions: Retrying an SBI/HDFC UPI mandate at 2:00 AM
  collapses to <2% success, whereas shifting to 10:00 AM daytime yields a massive recovery lift (>80%).
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.config import (
    BIN_COUNTRIES,
    CARD_NETWORKS,
    CARD_TYPES,
    FEATURE_COLUMNS,
    N_SAMPLES,
    PAYMENT_GATEWAYS,
    RANDOM_SEED,
    TARGET_COLUMN,
)
from app.domain.bank_network_map import BANK_NETWORK_MAP, ISSUING_BANKS, get_bank_pattern
from app.domain.decline_taxonomy import (
    DECLINE_CODES,
    DECLINE_TAXONOMY,
    DeclineCategory,
    evaluate_circuit_breaker,
)

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Real-world Indian subscription tiers
INDIAN_SUBSCRIPTION_TIERS: List[Dict[str, any]] = [
    {"service": "swiggy_one", "amount": 149.00, "weight": 0.30},
    {"service": "zomato_gold", "amount": 999.00, "weight": 0.25},
    {"service": "hotstar_premium", "amount": 1499.00, "weight": 0.20},
    {"service": "jiocinema_family", "amount": 89.00, "weight": 0.15},
    {"service": "zerodha_streak", "amount": 690.00, "weight": 0.10},
]


def compute_payday_proximity(day_of_month: int, day_of_week: int) -> int:
    """
    Returns 1 if the day falls within major Indian payroll disbursement windows:
    - Month-end (28th through 31st)
    - 1st through 5th of the month (corporate salary disbursement)
    - 7th through 10th of the month (PSU, government, and SME payroll cycle)
    """
    if day_of_month in [28, 29, 30, 31, 1, 2, 3, 4, 5, 7, 8, 9, 10]:
        return 1
    return 0


def compute_banking_settlement_window(hour_of_day: int) -> int:
    """
    Returns 1 if the hour corresponds to morning banking operational hours (09:00 - 13:00 IST).
    In India, NEFT batches and morning core banking liquidity peak during these business hours.
    """
    return 1 if 9 <= hour_of_day <= 13 else 0


def generate_synthetic_data(n: int = N_SAMPLES) -> pd.DataFrame:
    """
    Builds `n` high-fidelity transaction records containing realistic Indian recurring subscription churn,
    UPI AutoPay mandate failures, SBI/HDFC CBS downtime interactions, and empirical retry recovery probabilities.
    """
    # Distribution of decline codes mirroring real Indian payment gateway logs
    decline_weights = {
        "insufficient_funds": 0.32,          # High in mid-month liquidity drops
        "bank_server_down": 0.18,            # Extremely prevalent with SBI/HDFC midnight batch jobs
        "upi_mandate_revoked": 0.08,         # Customer cancelled autopay in UPI app (Hard decline)
        "rbi_afa_limit_exceeded": 0.03,      # Exceeded ₹15,000 threshold without OTP (Hard decline)
        "network_error": 0.08,               # NPCI switch / telecom transient glitch
        "do_not_honor": 0.08,                # Bank risk engine block
        "gateway_timeout": 0.05,             # Processor timeout
        "card_velocity_exceeded": 0.04,      # Daily limit reached
        "issuer_unavailable": 0.04,          # Bank switch down
        "processing_error": 0.03,            # Generic gateway error
        "generic_decline": 0.03,             # Generic bank rejection
        "stolen_card": 0.01,                 # Fraud / lost
        "lost_card": 0.01,
        "account_closed": 0.01,
        "fraudulent": 0.005,
        "expired_card": 0.005,
        "invalid_cvv": 0.005,
    }
    codes = list(decline_weights.keys())
    weights = np.array([decline_weights[c] for c in codes])
    weights /= weights.sum()

    # Issuing bank & UPI PSP probabilities
    bank_weights_map = {
        "sbi": 0.28,             # Largest bank in India (30%+ retail market share)
        "hdfc_bank": 0.22,       # Largest private sector bank
        "icici_bank": 0.14,      # Major private bank
        "axis_bank": 0.10,
        "kotak_mahindra": 0.08,
        "phonepe": 0.06,         # UPI AutoPay router
        "gpay": 0.05,
        "paytm": 0.04,
        "cred": 0.03,
    }
    banks = list(bank_weights_map.keys())
    bank_weights = np.array([bank_weights_map[b] for b in banks])
    bank_weights /= bank_weights.sum()

    sub_plans = INDIAN_SUBSCRIPTION_TIERS
    sub_weights = np.array([p["weight"] for p in sub_plans])
    sub_weights /= sub_weights.sum()

    now = datetime.utcnow()
    rows = []

    for _ in range(n):
        decline_code = np.random.choice(codes, p=weights)
        issuing_bank = np.random.choice(banks, p=bank_weights)
        bank_meta = get_bank_pattern(issuing_bank)
        bin_country = "IN"

        is_upi_psp = bank_meta.get("is_upi_psp", False)

        # Payment network and card product distribution
        if is_upi_psp:
            card_network = "upi_autopay"
            card_type = "upi"
        else:
            card_network = np.random.choice(["upi_autopay", "rupay", "visa", "mastercard"], p=[0.45, 0.25, 0.18, 0.12])
            if card_network == "upi_autopay":
                card_type = "upi"
            else:
                card_type = np.random.choice(["debit", "credit", "prepaid"], p=[0.65, 0.30, 0.05])

        # Acquiring gateway in India
        current_gateway = np.random.choice(PAYMENT_GATEWAYS)

        # Retry attempt count
        retry_attempt_number = int(np.random.choice([1, 2, 3, 4], p=[0.45, 0.30, 0.15, 0.10]))

        # Elapsed days since first decline
        if retry_attempt_number == 1:
            if random.random() < 0.40:
                elapsed_days = float(np.random.uniform(0.01, 1.0 / 24.0))  # within 1 hour
            else:
                elapsed_days = float(np.random.uniform(0.1, 1.5))
        elif retry_attempt_number == 2:
            elapsed_days = float(np.random.uniform(1.0, 4.0))
        elif retry_attempt_number == 3:
            elapsed_days = float(np.random.uniform(3.0, 8.0))
        else:
            elapsed_days = float(np.random.uniform(7.0, 14.0))

        # Invoice amount: Sample from familiar Indian subscription tiers
        if decline_code == "rbi_afa_limit_exceeded":
            # Must be > ₹15,000 to trigger RBI AFA threshold
            invoice_amount = float(random.choice([15999.00, 18500.00, 24999.00, 49999.00]))
            subscription_service = "enterprise_annual"
        else:
            chosen_sub = np.random.choice(sub_plans, p=sub_weights)
            invoice_amount = float(chosen_sub["amount"])
            subscription_service = chosen_sub["service"]

        # Temporal retry attributes in Indian Standard Time (IST)
        day_of_month = random.randint(1, 31)
        day_of_week = random.randint(0, 6)  # 0=Monday, 6=Sunday
        hour_of_day = random.randint(0, 23)

        is_payday = compute_payday_proximity(day_of_month, day_of_week)
        is_settlement = compute_banking_settlement_window(hour_of_day)

        # --- Calculate Ground Truth Success Probability with Indian Market Interactions ---
        cb_decision = evaluate_circuit_breaker(decline_code, retry_attempt_number)

        if cb_decision.is_unrecoverable or cb_decision.force_probability_zero:
            p_success = 0.0
        else:
            category = cb_decision.decline_category

            # -----------------------------------------------------------------
            # 1. SBI & HDFC Core Banking Solution (CBS) Nightly Maintenance Interaction
            # Retrying SBI/HDFC at 2:00 AM (00:00 - 04:00 IST) collapes to ~1-2%.
            # Shifting to 10:00 AM yields a massive success lift (>80%).
            # -----------------------------------------------------------------
            cbs_outage_hours = [23, 0, 1, 2, 3, 4]
            is_cbs_night_window = hour_of_day in cbs_outage_hours
            is_peak_daytime_window = 9 <= hour_of_day <= 13  # 10:00 AM local morning window

            if decline_code == "bank_server_down":
                if is_cbs_night_window:
                    # 2:00 AM SBI/HDFC maintenance failure
                    p_base = 0.015 if issuing_bank == "sbi" else 0.04
                elif is_peak_daytime_window:
                    # 10:00 AM massive recovery lift!
                    p_base = 0.85
                elif 9 <= hour_of_day <= 18:
                    p_base = 0.72
                else:
                    p_base = 0.35

            elif decline_code == "insufficient_funds":
                # Indian Salary / Liquidity Interaction
                if is_payday == 1 and is_settlement == 1:
                    p_base = 0.62  # Morning settlement on salary day
                elif is_payday == 1:
                    p_base = 0.44
                elif is_settlement == 1:
                    p_base = 0.22
                else:
                    p_base = 0.09

            elif decline_code == "card_velocity_exceeded":
                # Velocity counters reset daily at midnight
                p_base = 0.48 if elapsed_days >= 1.0 else 0.12

            elif category == DeclineCategory.SOFT_TECHNICAL.value:
                # network_error, gateway_timeout, issuer_unavailable
                if is_cbs_night_window and issuing_bank in ["sbi", "hdfc_bank"]:
                    p_base = 0.03
                elif elapsed_days <= (1.0 / 24.0):  # within 1 hour
                    p_base = 0.80
                elif elapsed_days <= (4.0 / 24.0):
                    p_base = 0.65
                elif is_peak_daytime_window:
                    p_base = 0.75
                else:
                    p_base = 0.30

            elif category == DeclineCategory.SOFT_AUTHORIZATION.value:
                # Daytime customer-active hours (09:00 - 18:00)
                if 9 <= hour_of_day <= 18:
                    p_base = 0.42
                else:
                    p_base = 0.14

            else:
                p_base = 0.30

            # -----------------------------------------------------------------
            # 2. UPI AutoPay & Indian Bank Specific Modifiers
            # -----------------------------------------------------------------
            if card_network == "upi_autopay":
                if issuing_bank == "sbi" and is_cbs_night_window:
                    p_base = min(p_base, 0.02)  # Strict failure at 2:00 AM for SBI UPI mandates
                elif issuing_bank == "sbi" and hour_of_day == 10:
                    p_base = max(p_base, 0.82)  # High success lift at 10:00 AM

                # Gateway routing advantage for UPI AutoPay
                if current_gateway in ["cashfree", "razorpay"]:
                    p_base += 0.10  # Dedicated NPCI direct mandate switches
                elif current_gateway == "billdesk" and issuing_bank == "sbi":
                    p_base += 0.08  # Billdesk strong connectivity with SBI
            elif card_network == "rupay":
                if current_gateway in ["razorpay", "billdesk"]:
                    p_base += 0.06

            # Bank sensitivity adjustments
            sensitivity = bank_meta.get("decline_sensitivity", "medium")
            if sensitivity == "high":
                p_base -= 0.05
            elif sensitivity == "low":
                p_base += 0.04

            # Attempt fatigue decay: alpha = 0.68^(k-1)
            alpha = (0.68) ** (retry_attempt_number - 1)
            p_success = float(np.clip(p_base * alpha, 0.0, 0.98))

        # Sample binary success
        success = int(np.random.binomial(1, p_success))

        original_ts = now - timedelta(days=elapsed_days + random.uniform(0, 30))

        rows.append({
            "transaction_id": str(uuid.uuid4()),
            "original_timestamp": original_ts.isoformat(),
            "bin_country": bin_country,
            "card_type": card_type,
            "card_network": card_network,
            "issuing_bank": issuing_bank,
            "invoice_amount_usd": invoice_amount,
            "day_of_month": day_of_month,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "is_payday_proximity": is_payday,
            "is_banking_settlement_window": is_settlement,
            "current_gateway": current_gateway,
            "retry_attempt_number": retry_attempt_number,
            "elapsed_days_since_first_decline": round(elapsed_days, 4),
            "decline_code": decline_code,
            "retry_success": success,
        })

    df = pd.DataFrame(rows)
    return df
