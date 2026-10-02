"""Leakage-safe splits: time windows + entity-disjoint test groups (configs/assumptions.yaml)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from uvera_ml.common import load_config

WARMUP_DAYS = 14  # features need history; the first two weeks are never used for training or testing


def day_bounds(n_days: int) -> dict:
    s = load_config("assumptions")["splits"]
    train_end = int(round(s["train"] * n_days))
    cal_end = train_end + int(round(s["calibration"] * n_days))
    val_end = cal_end + int(round(s["validation"] * n_days))
    return {"warmup_end": WARMUP_DAYS, "train_end": train_end, "cal_end": cal_end, "val_end": val_end, "end": n_days}


def is_test_entity(ids: pd.Series, share: float = 0.3) -> np.ndarray:
    """Deterministic entity split: ids whose number ends in 0, 1 or 2 form the unseen test group (30%)."""
    num = ids.astype(str).str.extract(r"(\d+)$")[0].astype(int).to_numpy()
    return (num % 10) < int(round(share * 10))


def assign_split(day: pd.Series, entity_ids: pd.Series, n_days: int) -> pd.Series:
    """train / cal / val use the 70% training group; test uses the unseen 30% group in the last window."""
    b = day_bounds(n_days)
    d = day.to_numpy()
    unseen = is_test_entity(entity_ids)
    out = np.full(len(d), "warmup", dtype=object)
    out[(d >= b["warmup_end"]) & (d < b["train_end"]) & ~unseen] = "train"
    out[(d >= b["train_end"]) & (d < b["cal_end"]) & ~unseen] = "cal"
    out[(d >= b["cal_end"]) & (d < b["val_end"]) & ~unseen] = "val"
    out[(d >= b["val_end"]) & unseen] = "test"
    out[(d >= b["val_end"]) & ~unseen] = "test_seen"
    out[(d >= b["warmup_end"]) & (d < b["val_end"]) & unseen] = "unused_unseen"  # never touched before the test
    return pd.Series(out, index=day.index, name="split")
