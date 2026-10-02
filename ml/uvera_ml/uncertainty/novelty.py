"""Out-of-range / novelty flag from robust z-scores (JSON-exportable, no pickles)."""
from __future__ import annotations

import numpy as np
import pandas as pd


class RobustNovelty:
    def __init__(self, median: dict | None = None, scale: dict | None = None, threshold: float | None = None):
        self.median, self.scale, self.threshold = median or {}, scale or {}, threshold

    def _z(self, X: pd.DataFrame) -> np.ndarray:
        cols = list(self.median)
        Z = (X[cols].to_numpy(float) - np.array([self.median[c] for c in cols])) / np.array([self.scale[c] for c in cols])
        return np.nan_to_num(np.abs(Z), nan=0.0)

    def fit(self, X: pd.DataFrame, quantile: float = 0.995) -> "RobustNovelty":
        for c in X.columns:
            v = X[c].to_numpy(float)
            v = v[~np.isnan(v)]
            med = float(np.median(v)) if len(v) else 0.0
            iqr = float(np.subtract(*np.percentile(v, [75, 25]))) if len(v) else 1.0
            self.median[c], self.scale[c] = med, max(iqr / 1.349, 1e-6 + 0.05 * abs(med), 1e-3)
        self.threshold = float(np.quantile(self.score(X), quantile))
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Mean of the 3 largest |z| values: robust to a single odd feature."""
        Z = np.sort(self._z(X), axis=1)[:, -3:]
        return Z.mean(axis=1)

    def flag(self, X: pd.DataFrame) -> np.ndarray:
        return self.score(X) > self.threshold

    def to_json(self) -> dict:
        return {"method": "robust_z_top3", "median": self.median, "scale": self.scale, "threshold": self.threshold}

    @classmethod
    def from_json(cls, d: dict) -> "RobustNovelty":
        return cls(d["median"], d["scale"], d["threshold"])
