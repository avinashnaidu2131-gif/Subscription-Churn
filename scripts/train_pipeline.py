"""
Orchestration script: generates 15,000 synthetic records with realistic interaction dynamics,
trains the CatBoost model with Stratified 5-Fold Cross-Validation, calibrates probabilities
using Isotonic Regression, reports evaluation metrics (ROC-AUC, Log-Loss, ECE, Brier),
saves artifacts, and produces the global SHAP summary plot.

Run this once to build all production artifacts:
    python scripts/train_pipeline.py
    uvicorn app.api.main:app --reload --port 8000
"""
import sys
from pathlib import Path

# Allow running as `python scripts/train_pipeline.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import SYNTHETIC_DATA_PATH  # noqa: E402
from app.data.generator import generate_synthetic_data  # noqa: E402
from app.ml.explain import explain_model  # noqa: E402
from app.ml.model import RetryModel  # noqa: E402
from app.optimizer.retry_optimizer import RetryOptimizer  # noqa: E402


def main():
    print("=================================================================")
    print("  PRODUCTION RETRY MODEL TRAINING & CALIBRATION PIPELINE")
    print("=================================================================\n")

    print("[1/5] Generating high-fidelity synthetic data (15,000 records)...")
    df = generate_synthetic_data()
    df.to_csv(SYNTHETIC_DATA_PATH, index=False)
    print(f"      -> {len(df):,} records successfully saved to {SYNTHETIC_DATA_PATH}")

    print("\n[2/5] Running Stratified 5-Fold CV & Isotonic Calibration...")
    model = RetryModel()
    X_train, X_test, metadata = model.train(df, n_splits=5, iterations=400)

    print("\n[3/5] Persisting production artifacts (.cbm, .joblib, metadata.json)...")
    model.save()

    print("\n[4/5] Generating global SHAP explainability plot...")
    explain_model(model, X_test)

    print("\n[5/5] Running end-to-end verification via Expected Value Optimizer...")
    optimizer = RetryOptimizer(model)

    # Verification 1: Circuit breaker on hard decline (UPI mandate revoked)
    hard_result = optimizer.optimize("upi_mandate_revoked", "sbi", invoice_amount_usd=149.0)
    print("\n  [Circuit Breaker Verification]")
    print(f"    Code: upi_mandate_revoked -> Terminal: {hard_result['terminal_decision']}, Action: {hard_result['routing_action']}")
    print(f"    Suggested Action: {hard_result['suggested_action']}")

    # Verification 2: SBI CBS downtime recovery (bank_server_down)
    sbi_result = optimizer.optimize(
        decline_code="bank_server_down",
        issuing_bank="sbi",
        invoice_amount_usd=149.0,  # Swiggy One
        card_type="upi",
        card_network="upi_autopay",
        current_gateway="cashfree",
        retry_attempt_number=1,
    )
    print("\n  [Expected Value Optimization Verification (SBI CBS Downtime)]")
    win_sbi = sbi_result["winning_schedule"]
    print(f"    Code: bank_server_down (SBI UPI AutoPay INR 149)")
    print(f"    Winning Slot: {win_sbi['day_of_week']} {win_sbi['hour_of_day']:02d}:00 via {win_sbi['payment_gateway'].upper()}")
    print(f"    Predicted P(success): {win_sbi['predicted_success_probability']:.3f} (Baseline: {sbi_result['baseline_probability']:.3f}, Lift: +{sbi_result['recovery_lift']:.3f})")
    print(f"    Net Expected Value: +INR {win_sbi['expected_recovery_value_usd']:.2f}")
    if sbi_result.get("shap_explanation"):
        print(f"    NL Rationale: \"{sbi_result['shap_explanation']['rationale']}\"")

    print("\n=================================================================")
    print("  PIPELINE COMPLETE. Ready for production serving:")
    print("    uvicorn app.api.main:app --reload --port 8000")
    print("=================================================================")


if __name__ == "__main__":
    main()

