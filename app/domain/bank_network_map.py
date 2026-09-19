"""
Issuing-bank / UPI App / card-network pattern map localized for the Indian financial ecosystem.

Real recovery systems in India see sharp differences in mandate success across:
- PSU vs Private banks (SBI/HDFC nightly Core Banking Solution batch maintenance windows)
- UPI AutoPay TPAPs/PSPs (PhonePe, Google Pay, Paytm, CRED)
- RuPay vs Visa/Mastercard mandate rails
- Indian Standard Time (IST / Asia/Kolkata) daytime business windows vs midnight batch outages
"""
from typing import Dict, List, Optional

# Region/country -> IANA timezone. Defaults to Indian Standard Time (IST).
REGION_TIMEZONES: Dict[str, str] = {
    "IN": "Asia/Kolkata",
    "US": "America/New_York",
    "UK": "Europe/London",
    "GB": "Europe/London",
    "DE": "Europe/Berlin",
    "CA": "America/Toronto",
    "SG": "Asia/Singapore",
    "AE": "Asia/Dubai",
}

DEFAULT_TIMEZONE = "Asia/Kolkata"

BANK_NETWORK_MAP: Dict[str, dict] = {
    # Top Indian Issuing Commercial Banks
    "hdfc_bank": {
        "display_name": "HDFC Bank",
        "network": "rupay/visa/mastercard/upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "high",
        "is_upi_psp": False,
        "cbs_maintenance_hours": [0, 1, 2, 3],  # 00:00 - 03:30 AM IST nightly maintenance
    },
    "sbi": {
        "display_name": "State Bank of India (SBI)",
        "network": "rupay/visa/mastercard/upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "high",
        "is_upi_psp": False,
        "cbs_maintenance_hours": [0, 1, 2, 3, 4],  # 00:00 - 04:30 AM IST CBS maintenance downtime
    },
    "icici_bank": {
        "display_name": "ICICI Bank",
        "network": "rupay/visa/mastercard/upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "medium",
        "is_upi_psp": False,
        "cbs_maintenance_hours": [1, 2],
    },
    "axis_bank": {
        "display_name": "Axis Bank",
        "network": "rupay/visa/mastercard/upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "medium",
        "is_upi_psp": False,
        "cbs_maintenance_hours": [1, 2],
    },
    "kotak_mahindra": {
        "display_name": "Kotak Mahindra Bank",
        "network": "rupay/visa/mastercard/upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "low",
        "is_upi_psp": False,
        "cbs_maintenance_hours": [1, 2],
    },

    # Indian UPI Apps / PSP Mandate Routers (NPCI Third Party App Providers)
    "phonepe": {
        "display_name": "PhonePe UPI AutoPay",
        "network": "upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "low",
        "is_upi_psp": True,
        "cbs_maintenance_hours": [],
    },
    "gpay": {
        "display_name": "Google Pay UPI AutoPay",
        "network": "upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "low",
        "is_upi_psp": True,
        "cbs_maintenance_hours": [],
    },
    "paytm": {
        "display_name": "Paytm UPI AutoPay",
        "network": "upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "medium",
        "is_upi_psp": True,
        "cbs_maintenance_hours": [],
    },
    "cred": {
        "display_name": "CRED Pay Mandates",
        "network": "upi_autopay",
        "region": "IN",
        "country": "IN",
        "decline_sensitivity": "low",
        "is_upi_psp": True,
        "cbs_maintenance_hours": [],
    },
}

# Aliases for backward compatibility and human-readable queries
_BANK_ALIASES: Dict[str, str] = {
    "hdfc": "hdfc_bank",
    "hdfc bank": "hdfc_bank",
    "state bank of india": "sbi",
    "icici": "icici_bank",
    "icici bank": "icici_bank",
    "axis": "axis_bank",
    "axis bank": "axis_bank",
    "kotak": "kotak_mahindra",
    "kotak bank": "kotak_mahindra",
    "google pay": "gpay",
    "phone pe": "phonepe",
}

ISSUING_BANKS: List[str] = list(BANK_NETWORK_MAP.keys())

# Sensitivity -> allowed retry budget per week & Bayesian confidence offsets
SENSITIVITY_ADJUSTMENTS: Dict[str, dict] = {
    "low": {"max_retries_per_week": 5, "confidence_penalty": 0.00},
    "medium": {"max_retries_per_week": 4, "confidence_penalty": 0.03},
    "high": {"max_retries_per_week": 2, "confidence_penalty": 0.08},
}


def get_bank_pattern(issuing_bank: str) -> dict:
    """
    Returns network/region/country/timezone/maintenance metadata for an Indian bank or UPI PSP.
    Handles exact names and aliases gracefully.
    """
    key = issuing_bank.strip().lower().replace(" ", "_")
    if key in _BANK_ALIASES:
        key = _BANK_ALIASES[key]

    if key not in BANK_NETWORK_MAP:
        # Fallback to standard Indian banking defaults
        return {
            "issuing_bank": issuing_bank,
            "display_name": issuing_bank,
            "network": "rupay/visa/mastercard/upi_autopay",
            "region": "IN",
            "country": "IN",
            "decline_sensitivity": "medium",
            "timezone": DEFAULT_TIMEZONE,
            "is_upi_psp": False,
            "cbs_maintenance_hours": [1, 2],
            "max_retries_per_week": 4,
            "confidence_penalty": 0.03,
        }

    pattern = {"issuing_bank": key, **BANK_NETWORK_MAP[key]}
    tz_key = pattern.get("country", pattern.get("region", "IN"))
    pattern["timezone"] = REGION_TIMEZONES.get(tz_key, DEFAULT_TIMEZONE)
    pattern.update(SENSITIVITY_ADJUSTMENTS[pattern["decline_sensitivity"]])
    return pattern
