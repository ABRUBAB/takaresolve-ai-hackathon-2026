"""Isotonic calibration, exported as plain JSON (no pickles) so the API can load it anywhere."""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


class IsotonicCalibrator:
    def __init__(self, x: np.ndarray | None = None, y: np.ndarray | None = None):
        self.x = None if x is None else np.asarray(x, float)
        self.y = None if y is None else np.asarray(y, float)

    def fit(self, scores, labels) -> "IsotonicCalibrator":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(np.asarray(scores, float), np.asarray(labels, float))
        self.x, self.y = iso.X_thresholds_, iso.y_thresholds_
        return self

    def predict(self, scores) -> np.ndarray:
        return np.interp(np.asarray(scores, float), self.x, self.y)

    def to_json(self) -> dict:
        return {"method": "isotonic", "x": self.x.tolist(), "y": self.y.tolist()}

    @classmethod
    def from_json(cls, d: dict) -> "IsotonicCalibrator":
        return cls(np.array(d["x"]), np.array(d["y"]))
