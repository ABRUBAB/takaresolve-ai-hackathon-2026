"""Offline (batch) side of the scale stack. Run once with the project venv:

    .venv\\Scripts\\python deploy/scale/offline/build_reference.py

Writes
  deploy/scale/reference_bins.json              PSI reference: quantile bins of the 19 AI-1 features, days 70-99
  deploy/scale/reference_bins_train.json        same on the train split (days 14-69), kept for comparison
  _outputs/scale/batch_features_window.parquet  build_ai1_features() values for the test window (days >= val_end),
                                                the "offline" side of the training-serving parity test
  _outputs/scale/loadgen_transfers.parquet      a sample of real test-window p2p transfers used as load-test payloads
  _outputs/scale/loadgen_texts.parquet          a sample of SMS texts for the AI-2 text-check load
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml.features.ai1 import FEATURES  # noqa: E402
from uvera_ml.features.splits import day_bounds  # noqa: E402
from uvera_ml.models.ai1 import prepare  # noqa: E402
from uvera_ml.sim.world import World  # noqa: E402

OUT = ROOT / "_outputs" / "scale"
N_BINS = 10


def ref_bins(v: np.ndarray) -> dict:
    """Quantile edges on non-missing values; NaN gets its own bin. Bin i = values in (edge[i-1], edge[i]]."""
    finite = v[~np.isnan(v)]
    edges = np.unique(np.quantile(finite, np.linspace(0, 1, N_BINS + 1)[1:-1])) if len(finite) else np.array([])
    idx = np.searchsorted(edges, finite, side="left")  # value == edge falls in the lower bin
    counts = np.bincount(idx, minlength=len(edges) + 1).astype(float)
    nan_share = float(np.isnan(v).mean())
    props = (counts / max(1, len(finite))) * (1 - nan_share)
    return {"edges": edges.tolist(), "props": props.tolist(), "nan_prop": nan_share, "n": int(len(v))}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    w = World.load(ROOT / "_outputs" / "world_full")
    df = prepare(w)
    b = day_bounds(w.n_days)
    print(f"features built in {time.time() - t0:.0f}s, rows={len(df)}, bounds={b}")

    # Deployed reference: the 30 days right before go-live (calibration + validation windows, days 70-99), i.e. the
    # data the calibrator, conformal sets and alert thresholds were fitted on. The train split (days 14-69) is kept as
    # an alternative: against it, calendar/history-dependent features (tenure, wallet age, first-time pair) drift on
    # perfectly normal traffic, see reports/scalability/README.md section 9.
    for name, part, label in [("reference_bins.json", df[df["split"].isin(["cal", "val"])],
                               f"split in (cal, val): days {b['train_end']}-{b['val_end'] - 1}, 70% customer group (last 30 days before go-live)"),
                              ("reference_bins_train.json", df[df["split"] == "train"],
                               f"split == train: days {b['warmup_end']}-{b['train_end'] - 1}, 70% customer group")]:
        bins = {f: ref_bins(part[f].to_numpy(float)) for f in FEATURES}
        ref = {"source": "build_ai1_features(_outputs/world_full), " + label, "data_version": w.meta["hashes"]["events"][:12],
               "n_rows": int(len(part)), "n_bins": N_BINS, "psi_warn": 0.1, "psi_alert": 0.2, "features": bins}
        (ROOT / "deploy" / "scale" / name).write_text(json.dumps(ref, indent=1), encoding="utf-8")

    window = df[df["day"] >= b["val_end"]]
    cols = ["event_id", "t", "day", "src", "dst", "amount", "channel", "label_scam", "is_scam", "split"] + FEATURES
    window[cols].to_parquet(OUT / "batch_features_window.parquet", index=False)
    print("window rows", len(window), "scams", int(window["label_scam"].sum()))

    rng = np.random.default_rng(7)
    ev = w.events
    p2p = ev[(ev["etype"] == "p2p") & (ev["src_kind"] == 0) & (ev["dst_kind"] == 0) & (ev["day"] >= b["val_end"])]
    s = p2p.iloc[rng.choice(len(p2p), size=min(20000, len(p2p)), replace=False)]
    s[["event_id", "t", "src", "dst", "amount", "channel"]].to_parquet(OUT / "loadgen_transfers.parquet", index=False)
    corpus = pd.read_parquet(ROOT / "artifacts" / "ai2" / "corpus.parquet")
    corpus.sample(n=min(3000, len(corpus)), random_state=7)[["text", "label"]].to_parquet(OUT / "loadgen_texts.parquet", index=False)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
