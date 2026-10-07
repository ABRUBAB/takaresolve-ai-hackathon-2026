"""Training-serving parity test: streaming (online) features vs build_ai1_features() (batch) for the same events.

Inputs (made by the replay, see README):
  _outputs/scale/batch_features_window.parquet    offline features, test window (offline/build_reference.py)
  _outputs/scale/online_features_window.npy       point-in-time features written by the feature-worker while the
                                                  whole event log was replayed through Redis Streams
Output: reports/scalability/parity.json

  .venv\\Scripts\\python deploy/scale/parity_test.py
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
FEATURES = json.loads((ROOT / "artifacts/ai1/features.json").read_text())["features"]


def agreement(b: np.ndarray, o: np.ndarray) -> dict:
    both_nan = np.isnan(b) & np.isnan(o)
    diff = np.abs(b - o)
    scale = np.maximum(np.abs(b), 1e-9)
    exact = both_nan | (diff <= 1e-6 + 1e-9 * scale)
    r1 = both_nan | (diff <= 0.01 * scale) | (diff <= 1e-6)
    r5 = both_nan | (diff <= 0.05 * scale) | (diff <= 1e-6)
    return {"exact_pct": round(100 * exact.mean(), 3), "within_1pct": round(100 * r1.mean(), 3),
            "within_5pct": round(100 * r5.mean(), 3), "nan_mismatch": int((np.isnan(b) ^ np.isnan(o)).sum()),
            "max_abs_diff": None if np.all(np.isnan(diff)) else round(float(np.nanmax(diff)), 6),
            "mean_abs_diff": None if np.all(np.isnan(diff)) else round(float(np.nanmean(diff)), 6)}


def main() -> None:
    batch = pd.read_parquet(ROOT / "_outputs/scale/batch_features_window.parquet")
    arr = np.load(ROOT / "_outputs/scale/online_features_window.npy")
    online = pd.DataFrame(arr[:, 1:], columns=FEATURES)
    online.insert(0, "event_id", arr[:, 0].astype(np.int64))
    m = batch.merge(online, on="event_id", suffixes=("_b", "_o"))
    print(f"batch rows {len(batch)}, online rows {len(online)}, joined {len(m)}")
    per = {f: agreement(m[f + "_b"].to_numpy(float), m[f + "_o"].to_numpy(float)) for f in FEATURES}
    booster = lgb.Booster(model_file=str(ROOT / "artifacts/ai1/model.txt"))
    Xb = m[[f + "_b" for f in FEATURES]].to_numpy(float)
    Xo = m[[f + "_o" for f in FEATURES]].to_numpy(float)
    sb, so = booster.predict(Xb), booster.predict(Xo)
    thr = json.loads((ROOT / "artifacts/ai1/thresholds.json").read_text())
    lvl = lambda s: np.where(s > thr["red_score"], 2, np.where(s > thr["amber_score"], 1, 0))  # noqa: E731
    y = m["label_scam"].to_numpy()

    def metrics(s, mask):
        return {"n": int(mask.sum()), "positives": int(y[mask].sum()),
                "roc_auc": round(float(roc_auc_score(y[mask], s[mask])), 4),
                "pr_auc": round(float(average_precision_score(y[mask], s[mask])), 4),
                "recall_at_red": round(float((s[mask][y[mask] == 1] > thr["red_score"]).mean()), 4),
                "red_rate": round(float((s[mask] > thr["red_score"]).mean()), 5)}

    all_rows = np.ones(len(m), bool)
    unseen = (m["split"] == "test").to_numpy()
    exact_feats = [f for f, v in per.items() if v["exact_pct"] >= 99.99]
    approx = {f: v for f, v in per.items() if v["exact_pct"] < 99.99}
    out = {
        "what": "Point-in-time features computed by the streaming feature-worker (Redis Streams + Lua online store, "
                "whole event log replayed in order) vs the batch training builder build_ai1_features() on the same "
                "transfers of the test window (days 100-119).",
        "rows": {"batch": int(len(batch)), "online": int(len(online)), "joined": int(len(m))},
        "per_feature": per,
        "features_exact": exact_feats, "features_approximate": list(approx),
        "model_on_batch_features": {"window": metrics(sb, all_rows), "unseen_customers_test_split": metrics(sb, unseen)},
        "model_on_online_features": {"window": metrics(so, all_rows), "unseen_customers_test_split": metrics(so, unseen)},
        "score_agreement": {"max_abs_raw_score_diff": round(float(np.abs(sb - so).max()), 6),
                            "mean_abs_raw_score_diff": round(float(np.abs(sb - so).mean()), 8),
                            "same_risk_level_pct": round(100 * float((lvl(sb) == lvl(so)).mean()), 3),
                            "risk_level_changes": int((lvl(sb) != lvl(so)).sum())},
    }
    (ROOT / "reports/scalability/parity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_feature"}, indent=1))
    for f, v in per.items():
        print(f"{f:28s} exact {v['exact_pct']:7.3f}%  within1% {v['within_1pct']:7.3f}%  max|d| {v['max_abs_diff']}")


if __name__ == "__main__":
    main()
