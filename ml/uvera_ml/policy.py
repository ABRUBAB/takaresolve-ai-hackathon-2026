"""Decision policy: turns model outputs into a state, an action list and a human-review flag.

Business rules live in configs/rules/actions.yaml, NOT inside the model (Guideline p9 section 12).
The customer is never blocked; a hold only happens if a human approves it.
"""
from __future__ import annotations

from uvera_ml.common import load_config


def risk_level(score: float, thresholds: dict) -> str:
    """Thresholds are on the continuous model score (frozen on validation); calibrated p is for display."""
    if score > thresholds["red_score"]:
        return "high"
    if score > thresholds["amber_score"]:
        return "medium"
    return "low"


def decide(score: float, conformal_state: str, ood: bool, thresholds: dict, amount: float,
           rules: dict | None = None) -> dict:
    rules = rules or load_config("rules/actions")
    level = risk_level(score, thresholds)
    unsure = (conformal_state == "unsure" and level != "low") or bool(ood)
    if unsure:
        state = "unsure"
    elif level == "high":
        state = "confident_high_large_amount" if amount >= rules["large_amount_bdt"] else "confident_high"
    elif level == "medium":
        state = "elevated"
    else:
        state = "confident_low"
    rule = rules["states"][state]
    review = rule["human_review"]
    if state == "unsure" and amount >= rules["large_amount_bdt"]:
        review = "required"
    return {"risk_level": level, "uncertainty_state": "unsure" if unsure else "confident", "state": state,
            "recommendation": rule["recommendation"], "human_review": review,
            "reasons_for_unsure": [r for r, on in (("conformal_set_has_both_labels", conformal_state == "unsure"),
                                                   ("input_unlike_training_data", bool(ood))) if on]}
