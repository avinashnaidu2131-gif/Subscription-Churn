"""
Comprehensive test suite for the algorithmic churn retry middleware localized for the Indian financial market:
- Decline Taxonomy & Deterministic Circuit Breaker (including UPI mandate revoked & RBI AFA limit exceeded)
- High-Fidelity Synthetic Data Generator & SBI 2:00 AM vs 10:00 AM CBS Interaction Dynamics
- CatBoost Classifier & Isotonic Calibration Pipeline
- Net Expected Recovery Value Schedule Optimizer with Indian Gateways (Razorpay, PayU, Cashfree, BillDesk)
- Local SHAP Attribution & Natural Language Reasoning
"""
import unittest
from datetime import datetime
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from app.config import (
    FEATURE_COLUMNS,
    GATEWAY_AUTH_FEES,
    PAYMENT_GATEWAYS,
    TARGET_COLUMN,
)
from app.data.generator import (
    compute_banking_settlement_window,
    compute_payday_proximity,
    generate_synthetic_data,
)
from app.domain.bank_network_map import BANK_NETWORK_MAP, ISSUING_BANKS, get_bank_pattern
from app.domain.decline_taxonomy import (
    DECLINE_CODES,
    DECLINE_TAXONOMY,
    DeclineCategory,
    DunningRoute,
    evaluate_circuit_breaker,
)
from app.ml.explain import explain_local_schedule
from app.ml.model import RetryModel, compute_expected_calibration_error
from app.optimizer.retry_optimizer import RetryOptimizer


class TestDeclineTaxonomy(unittest.TestCase):
    def test_hard_declines_circuit_breaker(self):
        hard_codes = [
            "stolen_card",
            "lost_card",
            "account_closed",
            "fraudulent",
            "expired_card",
            "upi_mandate_revoked",
            "rbi_afa_limit_exceeded",
        ]
        for code in hard_codes:
            decision = evaluate_circuit_breaker(code, retry_attempt_number=1)
            self.assertFalse(decision.allow_ml_inference, f"ML inference should be blocked for {code}")
            self.assertTrue(decision.is_unrecoverable, f"{code} should be flagged as unrecoverable")
            self.assertTrue(decision.force_probability_zero, f"P should be forced to 0 for {code}")
            self.assertEqual(decision.routing_action, DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value)
            self.assertEqual(decision.decline_category, DeclineCategory.HARD_DECLINE.value)

    def test_max_attempts_exceeded_trips_circuit_breaker(self):
        decision = evaluate_circuit_breaker("insufficient_funds", retry_attempt_number=5)
        self.assertFalse(decision.allow_ml_inference)
        self.assertTrue(decision.is_unrecoverable)
        self.assertEqual(decision.routing_action, DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value)

    def test_soft_liquidity_routing(self):
        decision = evaluate_circuit_breaker("insufficient_funds", retry_attempt_number=1)
        self.assertTrue(decision.allow_ml_inference)
        self.assertFalse(decision.is_unrecoverable)
        self.assertEqual(decision.routing_action, DunningRoute.PAYROLL_BALANCE_SCHEDULER.value)
        self.assertEqual(decision.decline_category, DeclineCategory.SOFT_LIQUIDITY.value)
        self.assertGreaterEqual(decision.min_wait_hours, 12)

    def test_soft_technical_routing(self):
        for code in ["network_error", "gateway_timeout", "issuer_unavailable", "bank_server_down"]:
            decision = evaluate_circuit_breaker(code, retry_attempt_number=1)
            self.assertTrue(decision.allow_ml_inference)
            self.assertEqual(decision.routing_action, DunningRoute.SHORT_INTERVAL_EXPONENTIAL_BACKOFF.value)
            self.assertIn(code, DECLINE_CODES)

    def test_soft_authorization_routing(self):
        for code in ["do_not_honor", "generic_decline"]:
            decision = evaluate_circuit_breaker(code, retry_attempt_number=1)
            self.assertTrue(decision.allow_ml_inference)
            self.assertEqual(decision.routing_action, DunningRoute.DAYTIME_FAILOVER_SCHEDULER.value)


class TestSyntheticDataGenerator(unittest.TestCase):
    def test_generator_schema_and_size(self):
        df = generate_synthetic_data(n=250)
        self.assertEqual(len(df), 250)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)
        self.assertIn(TARGET_COLUMN, df.columns)
        self.assertIn("transaction_id", df.columns)

    def test_hard_declines_zero_conversion(self):
        df = generate_synthetic_data(n=1000)
        hard_rows = df[df["decline_code"].isin([
            "stolen_card",
            "lost_card",
            "account_closed",
            "fraudulent",
            "upi_mandate_revoked",
            "rbi_afa_limit_exceeded",
        ])]
        if not hard_rows.empty:
            self.assertEqual(hard_rows["retry_success"].sum(), 0, "Hard declines must have 0% retry success")

    def test_payday_and_settlement_helpers(self):
        # 1st of month is payday in India
        self.assertEqual(compute_payday_proximity(1, 2), 1)
        self.assertEqual(compute_payday_proximity(7, 3), 1)
        self.assertEqual(compute_payday_proximity(30, 4), 1)
        # 15th of month Wednesday is not standard Indian payday
        self.assertEqual(compute_payday_proximity(15, 2), 0)

        # 10:00 is banking settlement window (09:00 - 13:00)
        self.assertEqual(compute_banking_settlement_window(10), 1)
        # 02:00 is midnight batch window
        self.assertEqual(compute_banking_settlement_window(2), 0)

    def test_sbi_cbs_outage_vs_daytime_lift(self):
        df = generate_synthetic_data(n=3000)
        # Check SBI records with bank_server_down or UPI mandates
        sbi_midnight = df[
            (df["issuing_bank"] == "sbi")
            & (df["decline_code"] == "bank_server_down")
            & (df["hour_of_day"].isin([1, 2, 3]))
        ]
        sbi_daytime = df[
            (df["issuing_bank"] == "sbi")
            & (df["decline_code"] == "bank_server_down")
            & (df["hour_of_day"].isin([10, 11, 12]))
        ]
        if not sbi_midnight.empty and not sbi_daytime.empty:
            midnight_rate = sbi_midnight["retry_success"].mean()
            daytime_rate = sbi_daytime["retry_success"].mean()
            self.assertGreater(daytime_rate, midnight_rate, "Daytime 10:00 AM retry must have higher success than midnight 2:00 AM")


class TestRetryModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = generate_synthetic_data(n=300)
        cls.model = RetryModel()
        cls.X_train, cls.X_test, cls.metadata = cls.model.train(
            cls.df, n_splits=2, iterations=30
        )

    def test_metrics_populated(self):
        metrics = self.metadata["metrics"]
        self.assertIn("roc_auc", metrics)
        self.assertIn("log_loss", metrics)
        self.assertIn("ece_uncalibrated", metrics)
        self.assertIn("ece_calibrated", metrics)
        self.assertIn("brier_score", metrics)
        self.assertGreater(metrics["roc_auc"], 0.50)

    def test_calibrated_predictions_bounded(self):
        probs = self.model.predict_proba(self.X_test)
        self.assertTrue(np.all(probs >= 0.0))
        self.assertTrue(np.all(probs <= 1.0))

    def test_raw_margins_exist(self):
        margins = self.model.predict_raw_margins(self.X_test.iloc[0:2])
        self.assertEqual(len(margins), 2)


class TestRetryOptimizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = generate_synthetic_data(n=300)
        cls.model = RetryModel()
        cls.model.train(cls.df, n_splits=2, iterations=30)
        cls.optimizer = RetryOptimizer(cls.model)

    def test_hard_decline_bypasses_ml(self):
        for code in ["stolen_card", "upi_mandate_revoked", "rbi_afa_limit_exceeded"]:
            result = self.optimizer.optimize(code, "sbi")
            self.assertFalse(result["retryable"])
            self.assertTrue(result["terminal_decision"])
            self.assertEqual(result["predicted_success_probability"], 0.0)
            self.assertEqual(result["expected_recovery_value_usd"], 0.0)
            self.assertEqual(result["routing_action"], DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value)
            self.assertIsNone(result["winning_schedule"])

    def test_soft_liquidity_optimization(self):
        result = self.optimizer.optimize(
            decline_code="insufficient_funds",
            issuing_bank="sbi",
            invoice_amount_usd=999.00,  # Zomato Gold
            card_type="upi",
            card_network="upi_autopay",
            current_gateway="razorpay",
            retry_attempt_number=1,
        )
        self.assertTrue(result["retryable"])
        self.assertFalse(result["terminal_decision"])
        self.assertGreater(result["expected_recovery_value_usd"], 0.0)
        self.assertIsNotNone(result["winning_schedule"])
        self.assertIn(result["winning_schedule"]["payment_gateway"], PAYMENT_GATEWAYS)
        self.assertIsNotNone(result["shap_explanation"])
        self.assertIn("rationale", result["shap_explanation"])

    def test_bank_server_down_optimization(self):
        result = self.optimizer.optimize(
            decline_code="bank_server_down",
            issuing_bank="sbi",
            invoice_amount_usd=149.00,  # Swiggy One
            card_type="upi",
            card_network="upi_autopay",
            current_gateway="cashfree",
            retry_attempt_number=1,
        )
        self.assertTrue(result["retryable"])
        self.assertIsNotNone(result["winning_schedule"])


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.api.main import app
        from app.state import set_model

        # Ensure model is initialized
        model = RetryModel().load()
        set_model(model)
        cls.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["model_loaded"])

    def test_decline_codes_endpoint(self):
        res = self.client.get("/decline-codes")
        self.assertEqual(res.status_code, 200)
        self.assertIn("insufficient_funds", res.json())
        self.assertIn("upi_mandate_revoked", res.json())
        self.assertIn("rbi_afa_limit_exceeded", res.json())
        self.assertIn("bank_server_down", res.json())

    def test_bank_patterns_endpoint(self):
        res = self.client.get("/bank-patterns")
        self.assertEqual(res.status_code, 200)
        self.assertIn("sbi", res.json())
        self.assertIn("hdfc_bank", res.json())

    def test_optimize_retry_hard_decline(self):
        res = self.client.post("/optimize-retry", json={
            "transaction_id": "test_txn_upi_revoked",
            "decline_code": "upi_mandate_revoked",
            "issuing_bank": "sbi",
            "invoice_amount_usd": 149.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["retryable"])
        self.assertTrue(data["terminal_decision"])
        self.assertEqual(data["routing_action"], DunningRoute.CUSTOMER_SELF_SERVE_DUNNING.value)

    def test_optimize_retry_soft_decline(self):
        res = self.client.post("/optimize-retry", json={
            "transaction_id": "test_txn_soft",
            "decline_code": "insufficient_funds",
            "issuing_bank": "hdfc_bank",
            "invoice_amount_usd": 999.00,
            "card_type": "upi",
            "card_network": "upi_autopay",
            "current_gateway": "razorpay",
            "retry_attempt_number": 1
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["retryable"])
        self.assertIsNotNone(data["winning_schedule"])
        self.assertIn("shap_explanation", data)
        self.assertIn("rationale", data["shap_explanation"])


if __name__ == "__main__":
    unittest.main()
