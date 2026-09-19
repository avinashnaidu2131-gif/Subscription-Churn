"""
Local SHAP Attribution & Natural Language Reasoning for Algorithmic Dunning.

Uses shap.TreeExplainer on the uncalibrated tree base to extract local feature
contributions (f(x) - E[f(x)]) for the winning retry schedule (t*, g*).
Generates a structured attribution dictionary and a concise, human-readable
rationale explaining why the optimal schedule was selected.
"""
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # headless backend for server environments
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from catboost import Pool

from app.config import FEATURE_COLUMNS, SHAP_PLOT_PATH
from app.ml.model import RetryModel


def explain_local_schedule(
    retry_model: RetryModel,
    winning_row: pd.DataFrame,
    initial_row: Optional[pd.DataFrame] = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Computes local SHAP attributions using TreeExplainer on the uncalibrated base CatBoost model.

    Returns:
      - base_value: Expected value E[f(x)] in logit/margin space
      - prediction_margin: Model score f(x)
      - top_positive_features: Features pushing probability upwards
      - top_negative_features: Features pulling probability downwards
      - rationale: Human-readable narrative summarizing the optimization decision
    """
    if retry_model.base_model is None:
        raise ValueError("Base CatBoost model is required for TreeExplainer.")

    # Prepare DataFrame matching FEATURE_COLUMNS
    X_target = winning_row[FEATURE_COLUMNS].copy()
    pool = Pool(X_target, cat_features=retry_model.cat_feature_idx)

    explainer = shap.TreeExplainer(retry_model.base_model)
    shap_matrix = explainer.shap_values(pool)

    if isinstance(shap_matrix, list):
        # In multi-class, index 1 is positive class
        shap_vals = np.array(shap_matrix[1])[0]
    elif len(shap_matrix.shape) == 2:
        shap_vals = shap_matrix[0]
    else:
        shap_vals = shap_matrix

    expected_val = float(explainer.expected_value if not isinstance(explainer.expected_value, list) else explainer.expected_value[0])
    margin = float(expected_val + np.sum(shap_vals))

    total_magnitude = float(np.sum(np.abs(shap_vals))) + 1e-7

    feature_records = []
    for col, val, s in zip(FEATURE_COLUMNS, X_target.iloc[0].values, shap_vals):
        if isinstance(val, (np.integer, int)):
            clean_val = int(val)
        elif isinstance(val, (np.floating, float)):
            clean_val = round(float(val), 2)
        elif isinstance(val, (np.bool_, bool)):
            clean_val = bool(val)
        else:
            clean_val = str(val)

        attribution_pct = (float(s) / total_magnitude) * 100.0
        sign_prefix = "+" if attribution_pct > 0 else ""
        feature_records.append({
            "feature": col,
            "value": clean_val,
            "shap_value": round(float(s), 4),
            "attribution_pct": round(float(attribution_pct), 1),
            "formatted_attribution": f"{sign_prefix}{attribution_pct:.1f}%",
        })


    pos_features = sorted([f for f in feature_records if f["shap_value"] > 0], key=lambda x: x["shap_value"], reverse=True)
    neg_features = sorted([f for f in feature_records if f["shap_value"] < 0], key=lambda x: x["shap_value"])

    top_pos = pos_features[:top_k]
    top_neg = neg_features[:top_k]

    # Synthesize concise, human-readable rationale
    rationale = _generate_natural_language_rationale(
        winning_row=winning_row.iloc[0],
        initial_row=initial_row.iloc[0] if initial_row is not None and not initial_row.empty else None,
        top_pos=top_pos,
        top_neg=top_neg,
    )

    return {
        "base_value": round(expected_val, 4),
        "prediction_margin": round(margin, 4),
        "top_positive_features": top_pos,
        "top_negative_features": top_neg,
        "rationale": rationale,
    }


def _generate_natural_language_rationale(
    winning_row: pd.Series,
    initial_row: Optional[pd.Series],
    top_pos: List[Dict[str, Any]],
    top_neg: List[Dict[str, Any]],
) -> str:
    """Constructs an actionable, professional explanation for the merchant/ops team."""
    hour = int(winning_row.get("hour_of_day", 0))
    time_str = f"{hour:02d}:00"
    gateway = str(winning_row.get("current_gateway", "")).capitalize()

    day_of_week_val = winning_row.get("day_of_week", 0)
    day_name_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    day_name = day_name_map.get(day_of_week_val, f"Day {day_of_week_val}")

    decline_code = str(winning_row.get("decline_code", "generic_decline"))
    card_type = str(winning_row.get("card_type", "card"))
    country = str(winning_row.get("bin_country", "domestic"))

    action_prefix = f"Shifted retry to {day_name} {time_str} via {gateway}"

    pos_reasons = []
    for feat in top_pos:
        f_name = feat["feature"]
        attr = feat["formatted_attribution"]
        if f_name == "is_banking_settlement_window" and winning_row.get("is_banking_settlement_window", 0) == 1:
            pos_reasons.append(f"overnight interbank settlement clearance ({attr} attribution)")
        elif f_name == "is_payday_proximity" and winning_row.get("is_payday_proximity", 0) == 1:
            pos_reasons.append(f"payroll balance replenishment window ({attr} attribution)")
        elif f_name == "current_gateway":
            pos_reasons.append(f"optimal gateway authorization routing ({attr} attribution)")
        elif f_name == "elapsed_days_since_first_decline":
            pos_reasons.append(f"transient cooldown absorption ({attr} attribution)")
        elif f_name == "card_type":
            pos_reasons.append(f"{card_type} re-authorization dynamics ({attr} attribution)")

    if not pos_reasons and top_pos:
        pos_reasons.append(f"{top_pos[0]['feature']} ({top_pos[0]['formatted_attribution']} attribution)")

    primary_benefit = f"Capitalizes on {pos_reasons[0]}" if pos_reasons else "Maximizes calibrated recovery probability"

    # Contextual routing / mitigation reason
    secondary_clause = ""
    if initial_row is not None:
        init_gateway = str(initial_row.get("current_gateway", "")).capitalize()
        if init_gateway != gateway:
            secondary_clause = f" while routing around {init_gateway} issuer-declines for {country} {card_type} cards."
    if not secondary_clause and top_neg:
        neg_feat = top_neg[0]
        if neg_feat["feature"] == "retry_attempt_number":
            secondary_clause = f" while actively managing card fatigue decay (attempt {winning_row.get('retry_attempt_number', 1)})."
        else:
            secondary_clause = f" while buffering against {neg_feat['feature']} friction."

    return f"{action_prefix}: {primary_benefit}{secondary_clause}"


def explain_model(retry_model: RetryModel, X_test: pd.DataFrame, out_path=SHAP_PLOT_PATH) -> None:
    """
    Saves a global SHAP summary plot visualizing overall feature attributions across the holdout set.
    """
    if retry_model.base_model is None:
        print("[SHAP] Warning: Base CatBoost model is missing. Skipping global summary plot.")
        return

    X = X_test[FEATURE_COLUMNS].copy()
    pool = Pool(X, cat_features=retry_model.cat_feature_idx)
    explainer = shap.TreeExplainer(retry_model.base_model)
    shap_values = explainer.shap_values(pool)

    plt.figure()
    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[SHAP] Summary plot saved to {out_path}")

