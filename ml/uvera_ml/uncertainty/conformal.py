"""Class-conditional (Mondrian) split conformal prediction for binary risk scores.

For each class c we compute a quantile q_c of the non-conformity scores 1 - p_c on the calibration set.
A label c is in the prediction set when 1 - p_c <= q_c. Coverage per class is >= 1 - alpha under
exchangeability. A set with both labels (or no label) means "not sure".
"""
from __future__ import annotations

import math

import numpy as np


class MondrianConformal:
    def __init__(self, alpha: float = 0.10, q0: float | None = None, q1: float | None = None):
        self.alpha, self.q0, self.q1 = alpha, q0, q1

    @staticmethod
    def _quantile(scores: np.ndarray, alpha: float) -> float:
        n = len(scores)
        if n == 0:
            return 1.0
        level = min(1.0, math.ceil((n + 1) * (1 - alpha)) / n)
        return float(np.quantile(scores, level, method="higher"))

    def fit(self, p_cal, y_cal) -> "MondrianConformal":
        p, y = np.asarray(p_cal, float), np.asarray(y_cal)
        self.q1 = self._quantile(1 - p[y == 1], self.alpha)
        self.q0 = self._quantile(p[y == 0], self.alpha)  # 1 - p_0 = p
        return self

    def predict_set(self, p) -> tuple[np.ndarray, np.ndarray]:
        p = np.asarray(p, float)
        in1 = (1 - p) <= self.q1
        in0 = p <= self.q0
        return in0, in1

    def state(self, p) -> np.ndarray:
        """'confident_low' (only 0), 'confident_high' (only 1), or 'unsure' (both / none)."""
        in0, in1 = self.predict_set(p)
        return np.where(in0 & ~in1, "confident_low", np.where(in1 & ~in0, "confident_high", "unsure"))

    def coverage(self, p, y) -> dict:
        in0, in1 = self.predict_set(p)
        y = np.asarray(y)
        cov = np.where(y == 1, in1, in0)
        return {"overall": float(cov.mean()),
                "class_1": float(cov[y == 1].mean()) if (y == 1).any() else float("nan"),
                "class_0": float(cov[y == 0].mean()) if (y == 0).any() else float("nan"),
                "unsure_rate": float(np.mean(in0 == in1)), "target": 1 - self.alpha}

    def to_json(self) -> dict:
        return {"method": "mondrian_split_conformal", "alpha": self.alpha, "q0": self.q0, "q1": self.q1}

    @classmethod
    def from_json(cls, d: dict) -> "MondrianConformal":
        return cls(d["alpha"], d["q0"], d["q1"])
