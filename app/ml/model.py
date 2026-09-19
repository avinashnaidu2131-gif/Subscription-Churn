"""
CatBoost Model & Probability Calibration Pipeline for Algorithmic Dunning.

Production ML pipeline implementing:
- Native handling of high-cardinality categorical features (decline_code, issuing_bank,
  bin_country, card_type, card_network, current_gateway).
- Stratified 5-Fold Cross-Validation for unbiased performance estimation.
- Isotonic Probability Calibration via CalibratedClassifierCV(method='isotonic')
  to align raw model logits with empirical recovery distributions.
- Comprehensive evaluation metrics: ROC-AUC, Log-Loss, Expected Calibration Error (ECE),
  and Brier Score.
- Complete artifact persistence: uncalibrated base CatBoost model (for TreeExplainer),
  calibrated probability estimator, and model metadata with optimal decision thresholds.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, train_test_split

from app.config import (
    ARTIFACTS_DIR,
    CALIBRATED_MODEL_PATH,
    CAT_FEATURES,
    FEATURE_COLUMNS,
    METADATA_PATH,
    MODEL_PATH,
    NUMERIC_FEATURES,
    RANDOM_SEED,
    TARGET_COLUMN,
)


def compute_expected_calibration_error(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> float:
    """
    Computes Expected Calibration Error (ECE) across `n_bins` uniform confidence intervals:
    ECE = sum_{b=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        if i == n_bins - 1:
            mask = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            mask = (y_prob >= bin_lower) & (y_prob < bin_upper)

        bin_size = int(np.sum(mask))
        if bin_size > 0:
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return float(ece)


class RetryModel:
    """
    Production-grade retry probability estimator combining CatBoost gradient boosting
    with Isotonic Probability Calibration.
    """

    def __init__(
        self,
        base_model: Optional[CatBoostClassifier] = None,
        calibrated_model: Optional[CalibratedClassifierCV] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.base_model: Optional[CatBoostClassifier] = base_model
        self.calibrated_model: Optional[CalibratedClassifierCV] = calibrated_model
        self.metadata: Dict[str, Any] = metadata or {}
        self.cat_feature_names: List[str] = CAT_FEATURES
        self.cat_feature_idx: List[int] = [FEATURE_COLUMNS.index(c) for c in CAT_FEATURES]
        self.optimal_threshold: float = 0.25

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures all FEATURE_COLUMNS are present and types are aligned."""
        X = df[FEATURE_COLUMNS].copy()
        for col in self.cat_feature_names:
            X[col] = X[col].astype(str)
        for col in NUMERIC_FEATURES:
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(0.0)
        return X

    def train(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
        iterations: int = 400,
        verbose: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Executes Stratified 5-Fold Cross-Validation, evaluates uncalibrated and calibrated metrics,
        trains the final base CatBoost model with isotonic calibration, and calculates optimal threshold.
        """
        X = self._prepare_features(df)
        y = df[TARGET_COLUMN].values.astype(int)

        print(f"[Model] Starting Stratified {n_splits}-Fold Cross-Validation on {len(df)} records...")
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)

        cv_fold_metrics: List[Dict[str, float]] = []
        oof_raw_preds = np.zeros(len(df))
        oof_cal_preds = np.zeros(len(df))

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
            X_fold_train, y_fold_train = X.iloc[train_idx], y[train_idx]
            X_fold_val, y_fold_val = X.iloc[val_idx], y[val_idx]

            fold_cb = CatBoostClassifier(
                iterations=iterations,
                depth=6,
                learning_rate=0.06,
                loss_function="Logloss",
                eval_metric="AUC",
                cat_features=self.cat_feature_idx,
                random_seed=RANDOM_SEED + fold,
                verbose=False,
            )
            fold_cb.fit(
                X_fold_train,
                y_fold_train,
                eval_set=(X_fold_val, y_fold_val),
                early_stopping_rounds=40,
                verbose=False,
            )

            # Fit isotonic calibration on validation fold
            fold_cal = CalibratedClassifierCV(
                estimator=fold_cb,
                method="isotonic",
                cv="prefit",
            )
            fold_cal.fit(X_fold_val, y_fold_val)

            raw_val_prob = fold_cb.predict_proba(X_fold_val)[:, 1]
            cal_val_prob = fold_cal.predict_proba(X_fold_val)[:, 1]

            oof_raw_preds[val_idx] = raw_val_prob
            oof_cal_preds[val_idx] = cal_val_prob

            fold_auc = roc_auc_score(y_fold_val, cal_val_prob)
            fold_loss = log_loss(y_fold_val, cal_val_prob)
            fold_ece = compute_expected_calibration_error(y_fold_val, cal_val_prob)
            fold_brier = brier_score_loss(y_fold_val, cal_val_prob)

            cv_fold_metrics.append({
                "fold": fold,
                "roc_auc": float(fold_auc),
                "log_loss": float(fold_loss),
                "ece": float(fold_ece),
                "brier_score": float(fold_brier),
            })
            if verbose:
                print(f"  Fold {fold}: AUC={fold_auc:.4f}, Loss={fold_loss:.4f}, ECE={fold_ece:.4f}, Brier={fold_brier:.4f}")

        # Aggregate Out-of-Fold (OOF) Metrics
        oof_auc = roc_auc_score(y, oof_cal_preds)
        oof_loss = log_loss(y, oof_cal_preds)
        oof_ece_uncal = compute_expected_calibration_error(y, oof_raw_preds)
        oof_ece_cal = compute_expected_calibration_error(y, oof_cal_preds)
        oof_brier = brier_score_loss(y, oof_cal_preds)

        print("\n[Model] Cross-Validation Performance Summary:")
        print(f"  Mean ROC-AUC:               {oof_auc:.4f}")
        print(f"  Mean Log-Loss:              {oof_loss:.4f}")
        print(f"  Raw Expected Calib Error:   {oof_ece_uncal:.4f}")
        print(f"  Calibrated Exp Calib Error: {oof_ece_cal:.4f} (ECE Reduction: {(oof_ece_uncal - oof_ece_cal) / oof_ece_uncal * 100:.1f}%)")
        print(f"  Mean Brier Score:           {oof_brier:.4f}")

        # Train Final Base Model and Calibrator on 80/20 train/calibration split
        X_train, X_calib, y_train, y_calib = train_test_split(
            X, y, test_size=0.20, random_state=RANDOM_SEED, stratify=y
        )

        self.base_model = CatBoostClassifier(
            iterations=iterations,
            depth=6,
            learning_rate=0.06,
            loss_function="Logloss",
            eval_metric="AUC",
            cat_features=self.cat_feature_idx,
            random_seed=RANDOM_SEED,
            verbose=False,
        )
        self.base_model.fit(
            X_train,
            y_train,
            eval_set=(X_calib, y_calib),
            early_stopping_rounds=50,
            verbose=False,
        )

        self.calibrated_model = CalibratedClassifierCV(
            estimator=self.base_model,
            method="isotonic",
            cv="prefit",
        )
        self.calibrated_model.fit(X_calib, y_calib)

        # Optimal Threshold via Youden's J-statistic on holdout
        calib_probs = self.calibrated_model.predict_proba(X_calib)[:, 1]
        fpr, tpr, thresholds = roc_curve(y_calib, calib_probs)
        j_scores = tpr - fpr
        best_idx = int(np.argmax(j_scores))
        self.optimal_threshold = float(np.clip(thresholds[best_idx], 0.10, 0.50))
        print(f"  Optimal Decision Threshold: {self.optimal_threshold:.4f} (Youden's J: {j_scores[best_idx]:.3f})")

        self.metadata = {
            "model_type": "CatBoostClassifier + CalibratedClassifierCV(isotonic)",
            "n_samples": int(len(df)),
            "feature_columns": FEATURE_COLUMNS,
            "cat_features": CAT_FEATURES,
            "numeric_features": NUMERIC_FEATURES,
            "cv_k": n_splits,
            "metrics": {
                "roc_auc": round(float(oof_auc), 4),
                "log_loss": round(float(oof_loss), 4),
                "ece_uncalibrated": round(float(oof_ece_uncal), 4),
                "ece_calibrated": round(float(oof_ece_cal), 4),
                "brier_score": round(float(oof_brier), 4),
            },
            "fold_metrics": cv_fold_metrics,
            "optimal_threshold": round(self.optimal_threshold, 4),
            "trained_at_utc": datetime.utcnow().isoformat(),
        }

        return X_train, X_calib, self.metadata

    def predict_proba(self, candidates: pd.DataFrame) -> np.ndarray:
        """
        Returns calibrated probability of retry success P(retry_success = 1 | x).
        Uses calibrated model when available, falling back to base CatBoost probabilities.
        """
        X = self._prepare_features(candidates)
        if self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)[:, 1]
        elif self.base_model is not None:
            return self.base_model.predict_proba(X)[:, 1]
        else:
            raise RuntimeError("Cannot predict: Model is not trained or loaded.")

    def predict_raw_margins(self, candidates: pd.DataFrame) -> np.ndarray:
        """Returns uncalibrated tree margin scores f(x) for SHAP TreeExplainer."""
        if self.base_model is None:
            raise RuntimeError("Base CatBoost model is not trained or loaded.")
        X = self._prepare_features(candidates)
        pool = Pool(X, cat_features=self.cat_feature_idx)
        return self.base_model.predict(pool, prediction_type="RawFormulaVal")

    def save(
        self,
        model_path: Path = MODEL_PATH,
        calibrated_path: Path = CALIBRATED_MODEL_PATH,
        metadata_path: Path = METADATA_PATH,
    ) -> None:
        """Persists CatBoost base model, joblib calibrated estimator, and metadata."""
        if self.base_model is not None:
            self.base_model.save_model(str(model_path))
            print(f"[Model] Base CatBoost model saved to {model_path}")

        if self.calibrated_model is not None:
            joblib.dump(self.calibrated_model, str(calibrated_path))
            print(f"[Model] Calibrated classifier saved to {calibrated_path}")

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)
            print(f"[Model] Metadata and threshold saved to {metadata_path}")

    def load(
        self,
        model_path: Path = MODEL_PATH,
        calibrated_path: Path = CALIBRATED_MODEL_PATH,
        metadata_path: Path = METADATA_PATH,
    ) -> "RetryModel":
        """Loads base model, calibrated model, and metadata from disk."""
        if Path(model_path).exists():
            self.base_model = CatBoostClassifier()
            self.base_model.load_model(str(model_path))
            print(f"[Model] Loaded base CatBoost model from {model_path}")
        else:
            print(f"[Model] Warning: {model_path} not found.")

        if Path(calibrated_path).exists():
            self.calibrated_model = joblib.load(str(calibrated_path))
            print(f"[Model] Loaded calibrated model from {calibrated_path}")
        else:
            print(f"[Model] Warning: {calibrated_path} not found.")

        if Path(metadata_path).exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            self.optimal_threshold = self.metadata.get("optimal_threshold", 0.25)
            print(f"[Model] Loaded metadata and threshold ({self.optimal_threshold}) from {metadata_path}")

        return self

