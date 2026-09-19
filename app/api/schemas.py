"""Pydantic request/response models for the production API layer."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import (
    CARD_NETWORKS,
    CARD_TYPES,
    PAYMENT_GATEWAYS,
)
from app.domain.bank_network_map import ISSUING_BANKS
from app.domain.decline_taxonomy import DECLINE_CODES


class TransactionInput(BaseModel):
    transaction_id: str
    decline_code: str = Field(..., description=f"Decline code from taxonomy: {DECLINE_CODES}")
    issuing_bank: str = Field(..., description=f"Card issuing bank: {ISSUING_BANKS}")
    invoice_amount_usd: float = Field(149.00, description="Gross charge invoice amount in INR (₹)")
    card_type: str = Field("upi", description=f"Card product type: {CARD_TYPES}")
    card_network: str = Field("upi_autopay", description=f"Payment network / mandate rail: {CARD_NETWORKS}")
    current_gateway: str = Field("razorpay", description=f"Acquiring gateway: {PAYMENT_GATEWAYS}")
    retry_attempt_number: int = Field(1, description="Current retry attempt number (1-4)")
    elapsed_days_since_first_decline: float = Field(0.0, description="Days elapsed since initial charge failure")
    bin_country: Optional[str] = Field("IN", description="ISO-2 country code of card BIN (e.g. IN)")
    original_timestamp: Optional[str] = Field(
        None, description="ISO timestamp of the original failed charge (informational only)"
    )


class RetryRecommendation(BaseModel):
    payment_gateway: str
    recommended_retry_datetime_utc: str
    recommended_retry_datetime_local: str
    local_timezone: str
    predicted_success_probability: float
    expected_recovery_value_usd: Optional[float] = None
    gateway_auth_fee_usd: Optional[float] = None
    fatigue_cost_usd: Optional[float] = None
    hour_of_day: Optional[int] = None
    day_of_week: Optional[str] = None
    is_payday_proximity: Optional[int] = None
    is_banking_settlement_window: Optional[int] = None


class OptimizeRetryResponse(BaseModel):
    transaction_id: str
    decline_code: str
    issuing_bank: str
    retryable: bool
    terminal_decision: bool = False
    routing_action: str
    reason: str
    suggested_action: str
    predicted_success_probability: float = 0.0
    expected_recovery_value_usd: float = 0.0
    recovery_lift: float = 0.0
    recovery_lift_percentage: float = 0.0
    baseline_probability: float = 0.0
    winning_schedule: Optional[RetryRecommendation] = None
    recommendations: List[RetryRecommendation] = []
    shap_explanation: Optional[Dict[str, Any]] = None
    circuit_breaker: Optional[Dict[str, Any]] = None

