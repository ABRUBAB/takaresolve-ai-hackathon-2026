"""Shared forecasting module for AI-3 (customer cash-flow) and AI-4 (agent cash liquidity).

Three forecasters, compared fairly with a rolling-origin backtest (no shuffling of time):
  seasonal-naive (weekly)  ->  LightGBM quantile (global, lag >= 7 so no recursion)  ->  Chronos-2 (zero-shot, covariates)
The winner per task is chosen on the validation origins and then reported on the test origins.
"""
from __future__ import annotations

from math import erf, sqrt

import lightgbm as lgb
import numpy as np
import pandas as pd

from uvera_ml.common import load_config
from uvera_ml.eval import metrics as M

QUANTILES = [0.1, 0.5, 0.9]
HORIZON = 7
LAGS = [7, 14, 21, 28]
COVARIATES = ["dow", "dom", "salary_week", "month_end", "festival"]


def add_calendar(df: pd.DataFrame, festival_days: list[int]) -> pd.DataFrame:
    df = df.copy()
    df["dow"] = df["date"].dt.dayofweek
    df["dom"] = df["date"].dt.day
    df["salary_week"] = (df["dom"] <= 5).astype(int)
    df["month_end"] = (df["dom"] >= 25).astype(int)
    df["festival"] = df["day"].between(festival_days[0], festival_days[1]).astype(int)
    return df


def customer_series(w, n: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Daily NET flow (inflow - outflow) per customer; only customers with full history and no mule role."""
    dc = w.daily_customer
    full = dc.groupby("customer_id")["day"].min() == 0
    ok = set(full[full].index) - set(w.truth_customers.loc[w.truth_customers["is_mule"], "customer_id"])
    ids = np.random.default_rng(seed).choice(sorted(ok), min(n, len(ok)), replace=False)
    s = dc[dc["customer_id"].isin(ids)].rename(columns={"customer_id": "id"}).copy()
    s["target"] = s["inflow"] - s["outflow"]
    return add_calendar(s[["id", "day", "date", "target", "balance_sod", "balance_eod"]], w.meta["festival_days"])


def agent_series(w) -> pd.DataFrame:
    s = w.daily_agent.rename(columns={"agent_id": "id", "cash_out": "target"})[["id", "day", "date", "target", "cash_in"]].copy()
    return add_calendar(s, w.meta["festival_days"])


# ------------------------------------------------------------------ forecasters
def seasonal_naive(ctx: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
    """y_hat(t) = y(t-7); quantiles from each series' own seasonal-naive residuals."""
    out = []
    for sid, g in ctx.groupby("id", sort=False):
        y = g["target"].to_numpy()
        res = y[7:] - y[:-7] if len(y) > 14 else np.zeros(1)
        lo, hi = np.quantile(res, 0.1), np.quantile(res, 0.9)
        f = future[future["id"] == sid].sort_values("day")
        base = np.resize(y[-7:], len(f))
        out.append(pd.DataFrame({"id": sid, "day": f["day"].to_numpy(), "q0.1": base + lo, "q0.5": base, "q0.9": base + hi}))
    return pd.concat(out, ignore_index=True)


def _lag_frame(s: pd.DataFrame) -> pd.DataFrame:
    s = s.sort_values(["id", "day"]).copy()
    g = s.groupby("id")["target"]
    for L in LAGS:
        s[f"lag{L}"] = g.shift(L)
    s["lag_mean"] = s[[f"lag{L}" for L in LAGS]].mean(axis=1)
    s["lag_std"] = s[[f"lag{L}" for L in LAGS]].std(axis=1)
    return s


LGB_FEATS = [f"lag{L}" for L in LAGS] + ["lag_mean", "lag_std"] + COVARIATES


class LGBQuantile:
    """Global LightGBM, one model per quantile. All lags >= 7 days, so a 7-day horizon needs no recursion."""

    def fit(self, hist: pd.DataFrame, seed: int = 42) -> "LGBQuantile":
        X = _lag_frame(hist).dropna(subset=[f"lag{L}" for L in LAGS])
        self.models = {q: lgb.train({"objective": "quantile", "alpha": q, "learning_rate": 0.05, "num_leaves": 31,
                                     "min_child_samples": 30, "verbose": -1, "seed": seed},
                                    lgb.Dataset(X[LGB_FEATS], X["target"]), 300) for q in QUANTILES}
        return self

    def predict(self, ctx: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
        both = pd.concat([ctx, future.assign(target=np.nan)], ignore_index=True)
        X = _lag_frame(both)
        X = X[X["day"].isin(future["day"].unique()) & X.set_index(["id", "day"]).index.isin(future.set_index(["id", "day"]).index)]
        out = X[["id", "day"]].copy()
        for q, m in self.models.items():
            out[f"q{q}"] = m.predict(X[LGB_FEATS])
        out[["q0.1", "q0.5", "q0.9"]] = np.sort(out[["q0.1", "q0.5", "q0.9"]].to_numpy(), axis=1)  # no quantile crossing
        return out.reset_index(drop=True)


class Chronos2:
    """Zero-shot Chronos-2 (amazon/chronos-2, Apache-2.0) with known future covariates."""

    def __init__(self, device: str | None = None):
        import torch
        from chronos import Chronos2Pipeline

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map=device)

    def predict(self, ctx: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
        cdf = ctx[["id", "date", "target", *COVARIATES]].rename(columns={"date": "timestamp"})
        fdf = future[["id", "date", *COVARIATES]].rename(columns={"date": "timestamp"})
        pred = self.pipe.predict_df(cdf, future_df=fdf, prediction_length=future.groupby("id").size().max(),
                                    quantile_levels=QUANTILES, id_column="id", timestamp_column="timestamp", target="target")
        qcols = {c: f"q{float(c)}" for c in pred.columns if _is_quantile_col(c)}
        pred = pred.rename(columns=qcols)
        pred["day"] = (pd.to_datetime(pred["timestamp"]) - pd.Timestamp(ctx["date"].min())).dt.days + int(ctx["day"].min())
        return pred[["id", "day", "q0.1", "q0.5", "q0.9"]]


def _is_quantile_col(c) -> bool:
    try:
        return 0 < float(c) < 1
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------ evaluation
def evaluate(series: pd.DataFrame, pred: pd.DataFrame, origin: int) -> dict:
    m = series.merge(pred, on=["id", "day"])
    ctx = series[series["day"] < origin]
    scale = ctx.groupby("id")["target"].apply(lambda y: np.mean(np.abs(np.diff(y.to_numpy(), n=1)[6:])) if len(y) > 8 else 1.0)
    scale = float(np.nanmean(scale.replace(0, np.nan))) or 1.0
    # naive seasonal scale (lag 7) for MASE
    s7 = ctx.groupby("id")["target"].apply(lambda y: np.mean(np.abs(y.to_numpy()[7:] - y.to_numpy()[:-7])) if len(y) > 14 else np.nan)
    scale7 = float(np.nanmean(s7.replace(0, np.nan))) or scale
    return {"origin": origin, "n_points": int(len(m)),
            "mase": M.mase(m["target"], m["q0.5"], scale7),
            "pinball_mean": float(np.mean([M.pinball(m["target"], m[f"q{q}"], q) for q in QUANTILES])),
            "coverage_80": M.interval_coverage(m["target"], m["q0.1"], m["q0.9"]),
            "mean_width_80": float((m["q0.9"] - m["q0.1"]).mean())}


def normal_prob_above(threshold, q10, q50, q90):
    """P(X > threshold) from three quantiles via a normal approximation (sigma from the 80% band)."""
    sigma = np.maximum((np.asarray(q90) - np.asarray(q10)) / 2.563, 1e-6)
    z = (np.asarray(threshold, float) - np.asarray(q50)) / sigma
    return 0.5 * (1 - np.vectorize(lambda v: erf(v / sqrt(2)))(z))


def origins(n_days: int) -> dict:
    from uvera_ml.features.splits import day_bounds

    b = day_bounds(n_days)
    val = [o for o in range(b["cal_end"], b["val_end"] - HORIZON + 1, HORIZON)] or [b["cal_end"]]
    test = [o for o in range(b["val_end"], n_days - HORIZON + 1, HORIZON)] or [n_days - HORIZON]
    return {"val": val, "test": test, "train_end": b["train_end"]}


def backtest(series: pd.DataFrame, n_days: int, use_chronos: bool = True, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    """Rolling-origin backtest for every available model; returns per-origin metrics and test predictions."""
    org = origins(n_days)
    models = {"seasonal_naive": None, "lightgbm_quantile": None}
    chronos = None
    if use_chronos:
        try:
            chronos = Chronos2()
            models["chronos2"] = None
        except Exception as e:  # noqa: BLE001 - optional dependency
            print("Chronos-2 unavailable, skipping:", repr(e)[:200])
    rows, preds = [], {}
    for split, origin_list in (("val", org["val"]), ("test", org["test"])):
        for o in origin_list:
            ctx = series[series["day"] < o]
            fut = series[(series["day"] >= o) & (series["day"] < o + HORIZON)]
            lgbq = LGBQuantile().fit(ctx, seed)
            for name in models:
                if name == "seasonal_naive":
                    p = seasonal_naive(ctx, fut)
                elif name == "lightgbm_quantile":
                    p = lgbq.predict(ctx, fut)
                else:
                    p = chronos.predict(ctx, fut)
                r = evaluate(series, p, o)
                rows.append({"split": split, "model": name, **r})
                preds.setdefault(name, []).append(p.assign(origin=o, split=split))
    res = pd.DataFrame(rows)
    return res, {k: pd.concat(v, ignore_index=True) for k, v in preds.items()}


def pick_winner(res: pd.DataFrame) -> str:
    """Lowest validation pinball loss wins (MASE as tie-breaker)."""
    v = res[res["split"] == "val"].groupby("model")[["pinball_mean", "mase"]].mean()
    return str(v.sort_values(["pinball_mean", "mase"]).index[0])


def capacity(series: pd.DataFrame, train_end: int, factor: float | None = None) -> pd.Series:
    """Agent cash capacity = factor x mean daily cash-out demand in the TRAINING window only."""
    factor = factor or load_config("assumptions").get("agent_capacity_factor", 1.25)
    return series[series["day"] < train_end].groupby("id")["target"].mean() * factor
