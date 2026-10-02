"""Metrics used across UVERA. Never report accuracy alone on imbalanced data."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def pr_auc(y, s) -> float:
    y = np.asarray(y)
    return float(average_precision_score(y, s)) if 0 < y.sum() < len(y) else float("nan")


def roc_auc(y, s) -> float:
    y = np.asarray(y)
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else float("nan")


def brier(y, p) -> float:
    return float(brier_score_loss(y, np.clip(p, 0, 1)))


def ece(y, p, n_bins: int = 15) -> float:
    """Expected calibration error with equal-width bins."""
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 0, 1)
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def reliability_table(y, p, n_bins: int = 10) -> pd.DataFrame:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 0, 1)
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    df = pd.DataFrame({"bin": bins, "y": y, "p": p})
    return df.groupby("bin").agg(mean_pred=("p", "mean"), frac_pos=("y", "mean"), n=("y", "size")).reset_index()


def at_alert_rate(y, s, rate: float, amount=None) -> dict:
    """Flag the top `rate` share of scores; report recall, precision and (optionally) amount caught."""
    y, s = np.asarray(y), np.asarray(s, float)
    k = max(1, int(round(rate * len(s))))
    order = np.argsort(-s, kind="stable")[:k]
    flagged = np.zeros(len(s), bool)
    flagged[order] = True
    out = {"alert_rate": rate, "alerts": int(k), "recall": float(y[flagged].sum() / max(1, y.sum())),
           "precision": float(y[flagged].mean())}
    if amount is not None:
        amount = np.asarray(amount, float)
        out["amount_caught"] = float(amount[flagged & (y == 1)].sum())
        out["amount_total_scam"] = float(amount[y == 1].sum())
    return out


def false_alerts_per_1000(y, flagged) -> float:
    y, flagged = np.asarray(y), np.asarray(flagged, bool)
    neg = y == 0
    return float(1000 * flagged[neg].mean()) if neg.any() else float("nan")


def bootstrap_ci(fn, y, s, n: int = 200, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i):
            vals.append(fn(y[i], s[i]))
    if not vals:
        return float("nan"), float("nan")
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def risk_coverage(correct, confidence, points: int = 20) -> pd.DataFrame:
    """Selective prediction: keep the most confident predictions; error rate among kept ones."""
    correct, confidence = np.asarray(correct, float), np.asarray(confidence, float)
    order = np.argsort(-confidence, kind="stable")
    rows = []
    for cov in np.linspace(0.05, 1.0, points):
        k = max(1, int(round(cov * len(order))))
        rows.append({"coverage": float(cov), "risk": float(1 - correct[order[:k]].mean())})
    return pd.DataFrame(rows)


def precision_at_k(y, s, k: int) -> float:
    y, s = np.asarray(y), np.asarray(s, float)
    k = min(k, len(s))
    return float(y[np.argsort(-s, kind="stable")[:k]].mean()) if k else float("nan")


def mase(y_true, y_pred, scale: float) -> float:
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))) / max(scale, 1e-9))


def pinball(y_true, q_pred, q: float) -> float:
    diff = np.asarray(y_true, float) - np.asarray(q_pred, float)
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


def interval_coverage(y_true, lo, hi) -> float:
    y = np.asarray(y_true, float)
    return float(np.mean((y >= np.asarray(lo)) & (y <= np.asarray(hi))))


def mean_std(values) -> dict:
    v = np.asarray([x for x in values if x == x], float)
    return {"mean": float(v.mean()) if len(v) else float("nan"), "std": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
            "n": int(len(v))}
