"""AI-5 QR Shield: detect Bangla QR used as a disguised cash-out, per merchant per week.

Hybrid: peer-benchmark z-scores (transparent baseline) + IsolationForest (unsupervised, catches new styles)
+ LightGBM (supervised on families A, B, C). Family D is NEVER seen in training: it is the honest test of
whether the system generalises. Calibration + Mondrian conformal give a grey "needs review" state.
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import StratifiedGroupKFold

from uvera_ml.common import load_config, write_json
from uvera_ml.eval import metrics as M
from uvera_ml.eval import plots
from uvera_ml.features.qr import FEATURES, REASON_TEXT, build_qr_features
from uvera_ml.features.splits import day_bounds, is_test_entity
from uvera_ml.uncertainty.calibration import IsotonicCalibrator
from uvera_ml.uncertainty.conformal import MondrianConformal

HELD_OUT = "D_rotating_ring"
W_SUPERVISED = 0.7  # design choice: keep 30% weight on the unsupervised detector so new disguise styles still surface
LGB_PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=15, min_child_samples=20, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1)


def assign_qr_split(f: pd.DataFrame, n_days: int) -> pd.Series:
    b = day_bounds(n_days)
    mid = f["week"] * 7 + 3  # a week belongs to the window that contains its middle day
    test_m = is_test_entity(f["merchant_id"])
    out = np.full(len(f), "unused", dtype=object)
    out[(mid >= b["warmup_end"]) & (mid < b["train_end"]) & ~test_m] = "train"
    out[(mid >= b["train_end"]) & (mid < b["cal_end"]) & ~test_m] = "cal"
    out[(mid >= b["cal_end"]) & (mid < b["val_end"]) & ~test_m] = "val"
    out[(mid >= b["val_end"]) & test_m] = "test"
    split = pd.Series(out, index=f.index)
    split[(f["family"] == HELD_OUT) & split.isin(["train", "cal", "val"])] = "unused"  # family D never seen before test
    return split


def _rank(x: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Percentile of x within a reference distribution (the training scores)."""
    ref = np.sort(ref)
    return np.searchsorted(ref, x, side="right") / max(1, len(ref))


class QRShield:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def fit(self, train: pd.DataFrame, n_rounds: int = 300) -> "QRShield":
        y = train["is_disguised"].to_numpy()
        pos = max(1, y.sum())
        self.booster = lgb.train({**LGB_PARAMS, "seed": self.seed, "scale_pos_weight": float(np.sqrt((len(y) - pos) / pos))},
                                 lgb.Dataset(train[FEATURES], y), n_rounds)
        self.iforest = IsolationForest(n_estimators=300, random_state=self.seed).fit(train[FEATURES].fillna(0))
        self.ref_sup = self.booster.predict(train[FEATURES])
        self.ref_iso = -self.iforest.score_samples(train[FEATURES].fillna(0))
        self.ref_peer = train["peer_z_baseline"].to_numpy()
        return self

    def components(self, df: pd.DataFrame) -> dict:
        sup = self.booster.predict(df[FEATURES])
        iso = -self.iforest.score_samples(df[FEATURES].fillna(0))
        return {"supervised": _rank(sup, self.ref_sup), "isolation_forest": _rank(iso, self.ref_iso),
                "peer_z": _rank(df["peer_z_baseline"].to_numpy(), self.ref_peer)}

    def score(self, df: pd.DataFrame) -> np.ndarray:
        c = self.components(df)
        return W_SUPERVISED * c["supervised"] + (1 - W_SUPERVISED) * c["isolation_forest"]


def _weekly_precision_at_k(df: pd.DataFrame, s: np.ndarray, k: int) -> float:
    vals = [M.precision_at_k(g["is_disguised"].to_numpy(), s[g.index], k) for _, g in df.groupby("week")]
    return float(np.mean(vals)) if vals else float("nan")


def run_ai5(world, out: str | Path, seeds=(42, 7, 1337, 2026, 99), quick: bool = False) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai5", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    th = load_config("thresholds")["ai5_qr_shield"]
    fee = load_config("qr_fee")
    k = int(th["review_capacity_per_day"])

    f = build_qr_features(world)
    f["split"] = assign_qr_split(f, world.n_days)
    tr, ca, va, te = (f[f["split"] == s].reset_index(drop=True) for s in ("train", "cal", "val", "test"))
    print({s: (len(d), int(d["is_disguised"].sum())) for s, d in dict(train=tr, cal=ca, val=va, test=te).items()})

    single = {}
    for fam in ["A_round_amount_atm", "B_split_under_limit", "C_cash_in_pass_through", HELD_OUT]:
        sub = f[(f["family"] == fam) | (f["is_disguised"] == 0)]
        single[fam] = sorted({c: round(max(M.roc_auc(sub["is_disguised"], sub[c]), 1 - M.roc_auc(sub["is_disguised"], sub[c])), 3)
                              for c in FEATURES}.items(), key=lambda x: -x[1])[:3]

    # ---- cross-validation on train (grouped by merchant), components compared
    rows = []
    for seed in (seeds[:1] if quick else seeds):
        cv = StratifiedGroupKFold(n_splits=3 if quick else 5, shuffle=True, random_state=seed)
        for fold, (a, b) in enumerate(cv.split(tr, tr["is_disguised"], tr["merchant_id"])):
            m = QRShield(seed).fit(tr.iloc[a])
            comp = m.components(tr.iloc[b])
            yb = tr.iloc[b]["is_disguised"].to_numpy()
            for name, s in {**comp, "fused": m.score(tr.iloc[b])}.items():
                rows.append({"model": name, "seed": seed, "fold": fold, "pr_auc": M.pr_auc(yb, s)})
    folds = pd.DataFrame(rows)
    cv_summary = folds.groupby("model")["pr_auc"].agg(["mean", "std"]).round(4).reset_index().to_dict("records")

    # ---- final model, calibration, conformal, thresholds (validation)
    model = QRShield(seeds[0]).fit(tr)
    s = {k_: (model.score(d) if len(d) else np.array([])) for k_, d in dict(cal=ca, val=va, test=te).items()}
    calib = IsotonicCalibrator().fit(s["cal"], ca["is_disguised"])
    p = {k_: calib.predict(v) for k_, v in s.items()}
    conf = MondrianConformal(th["conformal_alpha"]).fit(p["cal"], ca["is_disguised"])
    thr_src, thr_df = ("val", va) if len(va) else ("cal", ca)
    neg_val = s[thr_src][thr_df["is_disguised"].to_numpy() == 0]  # thresholds on the continuous score (no ties)
    thr = {"amber_score": float(np.quantile(neg_val, 0.90)), "red_score": float(np.quantile(neg_val, 0.98)), "frozen": True,
           "rule": "validation split: amber = 10%, red = 2% of honest merchant-weeks flagged"}
    thr["amber_p"], thr["red_p"] = (float(v) for v in calib.predict([thr["amber_score"], thr["red_score"]]))

    # ---- ONE test pass
    y = te["is_disguised"].to_numpy()
    comp = model.components(te)
    level = np.where(s["test"] > thr["red_score"], "red", np.where(s["test"] > thr["amber_score"], "amber", "green"))
    cstate = conf.state(p["test"])
    grey = (cstate == "unsure") & (level != "green")
    state = np.where(grey, "grey_review", level)
    seen = te["family"].fillna("legit") != HELD_OUT
    d_rows = te["family"] == HELD_OUT
    honest_round = (te["is_disguised"] == 0) & te["category"].isin(["fixed_price_service", "mobile_recharge"])
    flagged = level != "green"

    def recall_on(mask):
        return float(flagged[mask].mean()) if mask.any() else None

    test = {
        "n_merchant_weeks": int(len(te)), "disguised_weeks": int(y.sum()),
        "pr_auc_seen_families": M.pr_auc(y[seen], p["test"][seen]),
        "pr_auc_all": M.pr_auc(y, p["test"]),
        "weekly_precision_at_k": _weekly_precision_at_k(te, p["test"], k), "k": k,
        "recall_by_family": {fam: recall_on((te["family"] == fam).to_numpy()) for fam in
                             ["A_round_amount_atm", "B_split_under_limit", "C_cash_in_pass_through", HELD_OUT]},
        "unseen_family_D": {name: M.pr_auc(np.r_[np.ones(d_rows.sum()), np.zeros((y == 0).sum())],
                                           np.r_[sc[d_rows.to_numpy()], sc[y == 0]])
                            for name, sc in {**comp, "fused": model.score(te)}.items()} if d_rows.any() else None,
        "fpr_honest_round_price_shops": float(flagged[honest_round.to_numpy()].mean()) if honest_round.any() else None,
        "fpr_honest_all": float(flagged[y == 0].mean()),
        "fpr_by_size": {sz: float(flagged[((te["size"] == sz) & (te["is_disguised"] == 0)).to_numpy()].mean())
                        for sz in ["small", "medium", "large"] if ((te["size"] == sz) & (te["is_disguised"] == 0)).any()},
        "ece": M.ece(y, p["test"]), "brier": M.brier(y, p["test"]), "conformal": conf.coverage(p["test"], y),
        "states": {k_: int(v) for k_, v in pd.Series(state).value_counts().items()},
        "peer_z_baseline_pr_auc": M.pr_auc(y, comp["peer_z"]),
    }

    # ---- scored table + reasons + zone summary (agent portal)
    contrib = model.booster.predict(te[FEATURES], pred_contrib=True)
    te_out = te[["merchant_id", "week", "zone", "category", "size", "volume", "n_payments", "is_disguised", "family"]].copy()
    te_out["score"], te_out["p_calibrated"], te_out["state"] = s["test"], p["test"], state
    for name, v in comp.items():
        te_out[f"component_{name}"] = v
    reasons = []
    for i in range(len(te)):
        c = contrib[i, :-1]
        top = [j for j in np.argsort(-c) if c[j] > 0][:3]
        r = []
        for j in top:
            feat, v = FEATURES[j], float(te.loc[i, FEATURES[j]])
            en, bn = REASON_TEXT.get(feat, (feat, feat))
            try:
                en, bn = en.format(v=v), bn.format(v=v)
            except (ValueError, KeyError):
                pass
            r.append({"feature": feat, "value": v, "contribution": float(c[j]), "text_en": en, "text_bn": bn})
        reasons.append(json.dumps(r, ensure_ascii=False))
    te_out["reasons"] = reasons
    te_out["est_fee_leakage_bdt"] = np.where(level != "green", te_out["volume"] * fee["fee_rate"], 0.0)
    zone = (te_out.groupby(["zone", "week"]).agg(flagged_merchants=("state", lambda s_: int((s_ != "green").sum())),
                                                  est_fee_leakage_bdt=("est_fee_leakage_bdt", "sum"),
                                                  merchants=("merchant_id", "nunique")).reset_index())

    plots.bars(list(comp) + ["fused"], [test["unseen_family_D"][n] if test["unseen_family_D"] else 0 for n in list(comp) + ["fused"]],
               rep / "figures" / "ai5_unseen_family_D.png", "Unseen family D: PR-AUC by component")
    plots.reliability({"QR Shield (calibrated)": M.reliability_table(y, p["test"])}, rep / "figures" / "ai5_reliability.png")

    model.booster.save_model(str(art / "model.txt"))
    write_json(art / "calibrator.json", calib.to_json())
    write_json(art / "conformal.json", conf.to_json())
    write_json(art / "thresholds.json", thr)
    te_out.to_parquet(art / "merchant_scores.parquet", index=False)
    zone.to_parquet(art / "zone_summary.parquet", index=False)

    summary = {"ai": "AI-5 QR Shield", "model": f"{W_SUPERVISED:.0%} LightGBM + {1 - W_SUPERVISED:.0%} IsolationForest (rank fusion)",
               "held_out_family": HELD_OUT, "fee_rate_assumption": fee, "single_feature_auc_top3": single,
               "cv_summary_train": cv_summary, "thresholds": thr, "test": test}
    write_json(rep / "metrics_ai5.json", summary)
    folds.to_csv(rep / "ai5_cv_folds.csv", index=False)
    return summary
