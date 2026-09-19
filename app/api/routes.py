"""API routes for the FT-04 churn retry middleware."""
from fastapi import APIRouter, HTTPException

from app.api.schemas import OptimizeRetryResponse, TransactionInput
from app.domain.bank_network_map import BANK_NETWORK_MAP, get_bank_pattern
from app.domain.decline_taxonomy import DECLINE_TAXONOMY, categorize_decline_code
from app.state import get_optimizer

router = APIRouter()


@router.post("/optimize-retry", response_model=OptimizeRetryResponse)
def optimize_retry_endpoint(payload: TransactionInput):
    """Given a failed transaction, returns a ranked, localized retry schedule (or a no-retry verdict)."""
    if payload.decline_code not in DECLINE_TAXONOMY:
        raise HTTPException(status_code=400, detail=f"Unknown decline_code. Known codes: {list(DECLINE_TAXONOMY)}")
    if payload.issuing_bank not in BANK_NETWORK_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown issuing_bank. Known banks: {list(BANK_NETWORK_MAP)}")

    optimizer = get_optimizer()
    result = optimizer.optimize(
        decline_code=payload.decline_code,
        issuing_bank=payload.issuing_bank,
        invoice_amount_usd=payload.invoice_amount_usd,
        card_type=payload.card_type,
        card_network=payload.card_network,
        current_gateway=payload.current_gateway,
        retry_attempt_number=payload.retry_attempt_number,
        elapsed_days_since_first_decline=payload.elapsed_days_since_first_decline,
        bin_country=payload.bin_country,
    )

    return OptimizeRetryResponse(
        transaction_id=payload.transaction_id,
        decline_code=payload.decline_code,
        issuing_bank=payload.issuing_bank,
        retryable=result["retryable"],
        terminal_decision=result.get("terminal_decision", False),
        routing_action=result.get("routing_action", "customer_self_serve_dunning"),
        reason=result["reason"],
        suggested_action=result["suggested_action"],
        predicted_success_probability=result.get("predicted_success_probability", 0.0),
        expected_recovery_value_usd=result.get("expected_recovery_value_usd", 0.0),
        recovery_lift=result.get("recovery_lift", 0.0),
        recovery_lift_percentage=result.get("recovery_lift_percentage", 0.0),
        baseline_probability=result.get("baseline_probability", 0.0),
        winning_schedule=result.get("winning_schedule"),
        recommendations=result.get("recommendations", []),
        shap_explanation=result.get("shap_explanation"),
        circuit_breaker=result.get("circuit_breaker"),
    )



@router.get("/decline-codes")
def list_decline_codes():
    """Exposes the full decline-code categorization taxonomy."""
    return {code: categorize_decline_code(code) for code in DECLINE_TAXONOMY}


@router.get("/decline-codes/{decline_code}")
def get_decline_code(decline_code: str):
    try:
        return categorize_decline_code(decline_code)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/bank-patterns")
def list_bank_patterns():
    """Exposes the full issuing-bank / card-network pattern map."""
    return {bank: get_bank_pattern(bank) for bank in BANK_NETWORK_MAP}


@router.get("/bank-patterns/{issuing_bank}")
def get_bank_pattern_endpoint(issuing_bank: str):
    try:
        return get_bank_pattern(issuing_bank)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
def health():
    optimizer = get_optimizer(raise_if_missing=False)
    return {"status": "ok", "model_loaded": optimizer is not None}
