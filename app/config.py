"""
Central configuration: feature schema, category vocabularies, gateway parameters, and file paths.
Localized specifically for the Indian financial market and recurring payment ecosystem (UPI AutoPay & RBI e-mandates).
"""
from pathlib import Path
from typing import Dict, List

RANDOM_SEED = 42
N_SAMPLES = 15000

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "app" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = ARTIFACTS_DIR / "retry_model.cbm"
CALIBRATED_MODEL_PATH = ARTIFACTS_DIR / "calibrated_model.joblib"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"
SHAP_PLOT_PATH = ARTIFACTS_DIR / "shap_summary.png"
SYNTHETIC_DATA_PATH = ARTIFACTS_DIR / "synthetic_retry_data.csv"

# --- Feature schema (shared across data gen / training / inference) --------
CAT_FEATURES: List[str] = [
    "decline_code",
    "issuing_bank",
    "bin_country",
    "card_type",
    "card_network",
    "current_gateway",
]

NUMERIC_FEATURES: List[str] = [
    "invoice_amount_usd",  # Retained column name for compatibility, values represent INR (₹)
    "day_of_month",
    "day_of_week",
    "hour_of_day",
    "is_payday_proximity",
    "is_banking_settlement_window",
    "retry_attempt_number",
    "elapsed_days_since_first_decline",
]

FEATURE_COLUMNS: List[str] = CAT_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN: str = "retry_success"

# --- Categorical Vocabularies: Indian Financial Ecosystem -------------------
# Primary Indian Payment Gateways
PAYMENT_GATEWAYS: List[str] = ["razorpay", "payu", "cashfree", "billdesk"]

# Payment methods and card products prevalent in India
CARD_TYPES: List[str] = ["debit", "credit", "prepaid", "upi"]
CARD_NETWORKS: List[str] = ["visa", "mastercard", "rupay", "upi_autopay"]
BIN_COUNTRIES: List[str] = ["IN", "US", "SG", "AE", "GB"]

DAYS_OF_WEEK: List[str] = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# --- Gateway Authorization Fees & Cost Parameters (in INR ₹) ----------------
# Razorpay 2% flat mandate fee vs Cashfree tiered routing (₹1.20) vs PayU/Billdesk
GATEWAY_AUTH_FEES: Dict[str, float] = {
    "razorpay": 2.00,   # Baseline mandate execution fee (₹2.00 / 2% pricing)
    "payu": 1.80,       # PayU standard mandate auth fee (₹1.80)
    "cashfree": 1.20,   # Cashfree tiered routing for UPI AutoPay (₹1.20)
    "billdesk": 2.50,   # BillDesk PSU bank clearing fee (₹2.50)
}


def calculate_gateway_fee(gateway: str, invoice_amount: float) -> float:
    """
    Computes dynamic acquiring fee structure:
    - Razorpay: 2% flat fee with ₹2.00 floor
    - Cashfree: ₹1.20 flat mandate fee (tiered routing advantage)
    - PayU: ₹1.80 flat fee
    - Billdesk: ₹2.50 flat enterprise fee
    """
    g = gateway.lower().strip()
    if g == "razorpay":
        return max(2.00, round(invoice_amount * 0.02, 2))
    if g == "cashfree":
        return 1.20
    if g == "payu":
        return 1.80
    if g == "billdesk":
        return 2.50
    return GATEWAY_AUTH_FEES.get(g, 2.00)


# Fatigue cost parameters (in INR ₹) to model customer notification fatigue & NPCI/bank velocity penalties
BASE_FATIGUE_COST: float = 5.00              # Base customer friction penalty (₹5.00)
FATIGUE_COST_PER_ATTEMPT: float = 7.50       # Attempt penalty decay (₹7.50 per attempt)
MAX_RETRY_ATTEMPTS: int = 4
