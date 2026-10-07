"""Population Stability Index per feature: training reference bins vs a sliding live window."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np

from uvscale.online_features import FEATURES

EPS = 1e-4


def psi(expected: np.ndarray, actual: np.ndarray) -> float:
    e = np.clip(expected, EPS, None)
    a = np.clip(actual, EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


class DriftMonitor:
    def __init__(self, ref_path: str | Path, window: int = 20_000, min_n: int = 500):
        ref = json.loads(Path(ref_path).read_text(encoding="utf-8"))
        self.warn, self.alert = ref.get("psi_warn", 0.1), ref.get("psi_alert", 0.2)
        self.edges = [np.asarray(ref["features"][f]["edges"], float) for f in FEATURES]
        self.ref = [np.asarray(ref["features"][f]["props"] + [ref["features"][f]["nan_prop"]], float) for f in FEATURES]
        self.window, self.min_n = window, min_n
        self.buf = np.full((window, len(FEATURES)), np.nan)
        self.n, self.pos, self.seen = 0, 0, 0
        self.lock = threading.Lock()

    def add(self, x: np.ndarray) -> None:
        with self.lock:
            self.buf[self.pos] = x
            self.pos = (self.pos + 1) % self.window
            self.n = min(self.n + 1, self.window)
            self.seen += 1

    def reset(self) -> None:
        with self.lock:
            self.n, self.pos = 0, 0

    def compute(self) -> dict:
        with self.lock:
            data = self.buf[: self.n].copy()
        out = {}
        for j, f in enumerate(FEATURES):
            v = data[:, j]
            fin = v[~np.isnan(v)]
            counts = np.bincount(np.searchsorted(self.edges[j], fin, side="left"), minlength=len(self.edges[j]) + 1)
            live = np.append(counts / max(1, len(v)), np.isnan(v).mean() if len(v) else 0.0)
            out[f] = round(psi(self.ref[j], live), 4) if len(v) >= self.min_n else None
        vals = [v for v in out.values() if v is not None]
        worst = max(vals) if vals else 0.0
        status = "insufficient_data" if not vals else "alert" if worst >= self.alert else "warn" if worst >= self.warn else "ok"
        top = sorted(((f, v) for f, v in out.items() if v is not None), key=lambda kv: -kv[1])[:5]
        return {"status": status, "max_psi": worst, "window_n": int(len(data)), "window_size": self.window,
                "events_seen": self.seen, "thresholds": {"warn": self.warn, "alert": self.alert},
                "top_drifted": [{"feature": f, "psi": v} for f, v in top], "psi": out,
                "features_alert": [f for f, v in out.items() if v is not None and v >= self.alert],
                "features_warn": [f for f, v in out.items() if v is not None and self.warn <= v < self.alert]}
