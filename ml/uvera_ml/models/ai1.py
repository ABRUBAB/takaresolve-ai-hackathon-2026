"""AI-1 Pause Check.

rule baseline -> logistic regression -> LightGBM (StratifiedGroupKFold x seeds) -> isotonic calibration
-> Mondrian conformal ("not sure") -> novelty flag -> thresholds frozen on validation -> ONE test pass
-> fairness slices, ablation, exact TreeSHAP reasons, JSON export (no pickles).
"""
from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from uvera_ml.common import load_config, write_json
from uvera_ml.eval import metrics as M
from uvera_ml.eval import plots
from uvera_ml.features.ai1 import FEATURES, GROUPS, SLICE_COLS, build_ai1_features, rule_baseline_score
from uvera_ml.features.splits import assign_split, day_bounds
from uvera_ml.uncertainty.calibration import IsotonicCalibrator
from uvera_ml.uncertainty.conformal import MondrianConformal
from uvera_ml.uncertainty.novelty import RobustNovelty
from uvera_ml.xai.reasons import top_reasons

LGB_PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_child_samples=40,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1)
LABEL = "label_scam"


def prepare(world) -> pd.DataFrame:
    df = build_ai1_features(world)
    df["split"] = assign_split(df["day"], df["src"], world.n_days)
    return df


def single_feature_auc(train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in FEATURES:
        a = M.roc_auc(train[LABEL], train[c].fillna(-999))
        rows.append({"feature": c, "auc": round(max(a, 1 - a), 4)})
    return pd.DataFrame(rows).sort_values("auc", ascending=False).reset_index(drop=True)


def _fit_lgb(X, y, seed, n_rounds=2000, Xv=None, yv=None, features=FEATURES):
    pos = max(1, int(np.sum(y)))
    params = {**LGB_PARAMS, "seed": seed, "scale_pos_weight": float(np.sqrt((len(y) - pos) / pos))}
    ds = lgb.Dataset(X[features], y, free_raw_data=False)
    if Xv is not None:
        dv = lgb.Dataset(Xv[features], yv, reference=ds)
        b = lgb.train({**params, "metric": "average_precision"}, ds, n_rounds, valid_sets=[dv],
                      callbacks=[lgb.early_stopping(100, verbose=False)])
        return b, b.best_iteration
    return lgb.train(params, ds, n_rounds), n_rounds


def _logreg(features=FEATURES):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=1.0, class_weight="balanced", max_iter=3000))


def cross_validate(train: pd.DataFrame, seeds=(42,), n_splits=5, compare=True) -> tuple[pd.DataFrame, int]:
    """StratifiedGroupKFold grouped by sender: no customer is in both the fit and the evaluation fold."""
    X, y, g = train, train[LABEL].to_numpy(), train["src"].to_numpy()
    rows, iters = [], []
    for seed in seeds:
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        for fold, (a, b) in enumerate(cv.split(X, y, g)):
            Xa, Xb, ya, yb = X.iloc[a], X.iloc[b], y[a], y[b]
            booster, it = _fit_lgb(Xa, ya, seed, Xv=Xb, yv=yb)
            iters.append(it)
            s = booster.predict(Xb[FEATURES], num_iteration=it)
            rows.append({"model": "lightgbm", "seed": seed, "fold": fold, "pr_auc": M.pr_auc(yb, s), "roc_auc": M.roc_auc(yb, s)})
            if seed != seeds[0] or not compare:
                continue
            rows.append({"model": "rule_baseline", "seed": seed, "fold": fold,
                         "pr_auc": M.pr_auc(yb, rule_baseline_score(Xb)), "roc_auc": M.roc_auc(yb, rule_baseline_score(Xb))})
            lr = _logreg().fit(Xa[FEATURES], ya)
            s = lr.predict_proba(Xb[FEATURES])[:, 1]
            rows.append({"model": "logistic_regression", "seed": seed, "fold": fold, "pr_auc": M.pr_auc(yb, s), "roc_auc": M.roc_auc(yb, s)})
            try:
                import xgboost as xgb

                pos = max(1, ya.sum())
                m = xgb.XGBClassifier(n_estimators=400, learning_rate=0.05, max_depth=6, subsample=0.8,
                                      colsample_bytree=0.8, scale_pos_weight=np.sqrt((len(ya) - pos) / pos),
                                      eval_metric="aucpr", random_state=seed, n_jobs=4)
                m.fit(Xa[FEATURES], ya)
                s = m.predict_proba(Xb[FEATURES])[:, 1]
                rows.append({"model": "xgboost", "seed": seed, "fold": fold, "pr_auc": M.pr_auc(yb, s), "roc_auc": M.roc_auc(yb, s)})
            except ImportError:
                pass
            try:
                from catboost import CatBoostClassifier

                m = CatBoostClassifier(iterations=400, learning_rate=0.05, depth=6, auto_class_weights="SqrtBalanced",
                                       random_seed=seed, verbose=False)
                m.fit(Xa[FEATURES], ya)
                s = m.predict_proba(Xb[FEATURES])[:, 1]
                rows.append({"model": "catboost", "seed": seed, "fold": fold, "pr_auc": M.pr_auc(yb, s), "roc_auc": M.roc_auc(yb, s)})
            except ImportError:
                pass
    folds = pd.DataFrame(rows)
    return folds, int(np.median(iters)) if iters else 300


def summarise_cv(folds: pd.DataFrame) -> pd.DataFrame:
    return (folds.groupby("model").agg(pr_auc_mean=("pr_auc", "mean"), pr_auc_std=("pr_auc", "std"),
                                       roc_auc_mean=("roc_auc", "mean"), n_fits=("pr_auc", "size"))
            .sort_values("pr_auc_mean", ascending=False).round(4).reset_index())


def _states(score, conf_state, ood, thr):
    level = np.where(score > thr["red_score"], "high", np.where(score > thr["amber_score"], "medium", "low"))
    # "not sure" = the conformal set holds both labels while the score is in the alert zone, or the input is novel.
    # Low-score transfers with an ambiguous set proceed normally (the model cannot rule a scam out, but the risk is
    # below the alert budget) - this keeps "not sure" rare enough to be useful for a human reviewer.
    unsure = ((conf_state == "unsure") & (level != "low")) | ood
    return level, unsure


def evaluate(df: pd.DataFrame, p: np.ndarray, raw: np.ndarray, conf: MondrianConformal, ood: np.ndarray,
             thr: dict, follow_rates: dict) -> dict:
    y, amount = df[LABEL].to_numpy(), df["amount"].to_numpy(float)
    rule = rule_baseline_score(df)
    rule_tb = rule + amount / 1e7  # rule points, ties broken by amount (as a basic system would)
    level, unsure = _states(raw, conf.state(p), ood, thr)
    flagged_red = level == "high"
    at5 = M.at_alert_rate(y, p, 0.05, amount)
    rule5 = M.at_alert_rate(y, rule_tb, 0.05, amount)
    conf_cov = conf.coverage(p, y)
    correct = (flagged_red == (y == 1)).astype(float)
    logit = lambda v: np.log(np.clip(v, 1e-6, 1 - 1e-6) / (1 - np.clip(v, 1e-6, 1 - 1e-6)))  # noqa: E731
    confidence = np.abs(logit(raw) - logit(np.array(thr["red_score"])))  # far from the decision threshold = confident
    rc = M.risk_coverage(correct, confidence)
    out = {
        "n": int(len(y)), "positives": int(y.sum()),
        "model": {"pr_auc": M.pr_auc(y, p), "pr_auc_ci95": M.bootstrap_ci(M.pr_auc, y, p), "roc_auc": M.roc_auc(y, p),
                  "brier": M.brier(y, p), "ece_calibrated": M.ece(y, p),
                  "ece_uncalibrated": M.ece(y, 1 / (1 + np.exp(-raw))) if raw.min() < 0 or raw.max() > 1 else M.ece(y, raw),
                  "at_5pct_alert_rate": at5, "false_alerts_per_1000_at_red": M.false_alerts_per_1000(y, flagged_red),
                  "recall_at_red": float(flagged_red[y == 1].mean()) if y.sum() else float("nan"),
                  "precision_at_red": float(y[flagged_red].mean()) if flagged_red.any() else float("nan")},
        "rule_baseline": {"pr_auc": M.pr_auc(y, rule_tb), "roc_auc": M.roc_auc(y, rule_tb), "at_5pct_alert_rate": rule5,
                          "false_alerts_per_1000": M.false_alerts_per_1000(y, rule >= 2)},
        "conformal": conf_cov, "ood_rate": float(ood.mean()), "unsure_rate": float(unsure.mean()),
        "error_rate_confident_vs_unsure": {
            "confident": float(1 - correct[~unsure].mean()) if (~unsure).any() else None,
            "unsure": float(1 - correct[unsure].mean()) if unsure.any() else None},
        "risk_levels": {k: int(v) for k, v in pd.Series(level).value_counts().items()},
        "selective": {"error_at_100pct_coverage": float(rc["risk"].iloc[-1]),
                      "error_at_80pct_coverage": float(rc.loc[(rc["coverage"] - 0.8).abs().idxmin(), "risk"])},
        "loss_prevented_bdt": {name: {"model": at5["amount_caught"] * fr, "rule_baseline": rule5["amount_caught"] * fr,
                                      "follow_rate": fr} for name, fr in follow_rates.items()},
    }
    return out, rc


def slices(df: pd.DataFrame, p: np.ndarray, raw: np.ndarray, unsure: np.ndarray, thr: dict) -> list[dict]:
    y, flagged = df[LABEL].to_numpy(), raw > thr["red_score"]
    rows = []
    for col in SLICE_COLS:
        for val, idx in df.groupby(col).indices.items():
            yy, ff = y[idx], flagged[idx]
            rows.append({"slice": col, "group": str(val), "n": int(len(idx)), "positives": int(yy.sum()),
                         "fpr_at_red": float(ff[yy == 0].mean()) if (yy == 0).any() else None,
                         "fnr_at_red": float(1 - ff[yy == 1].mean()) if (yy == 1).any() else None,
                         "ece": M.ece(yy, p[idx]) if len(idx) > 50 else None,
                         "unsure_rate": float(unsure[idx].mean())})
    return rows


def ablation(train: pd.DataFrame, val: pd.DataFrame, n_rounds: int, seed: int = 42) -> list[dict]:
    """Validation-only ablation (the test set is never used here)."""
    sets = {"sender only": GROUPS["sender"], "recipient only": GROUPS["recipient"],
            "sender + recipient": GROUPS["sender"] + GROUPS["recipient"], "full": FEATURES}
    rows = []
    for name, feats in sets.items():
        b, _ = _fit_lgb(train, train[LABEL].to_numpy(), seed, n_rounds, features=feats)
        s = b.predict(val[feats])
        rows.append({"features": name, "n_features": len(feats), "val_pr_auc": M.pr_auc(val[LABEL], s)})
    rows.append({"features": "rule baseline", "n_features": 2, "val_pr_auc": M.pr_auc(val[LABEL], rule_baseline_score(val))})
    return rows


def run_ai1(world, out: str | Path, seeds=(42, 7, 1337, 2026, 99), quick: bool = False) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai1", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    (rep / "figures").mkdir(parents=True, exist_ok=True)
    cfg = load_config("assumptions")
    follow = cfg.get("impact", {}).get("follow_rate", {"conservative": 0.3, "base": 0.5, "optimistic": 0.7})
    alpha = load_config("thresholds")["ai1_pause_check"]["conformal_alpha"]

    df = prepare(world)
    tr, ca, va = (df[df["split"] == s].reset_index(drop=True) for s in ("train", "cal", "val"))
    te, te_seen = (df[df["split"] == s].reset_index(drop=True) for s in ("test", "test_seen"))
    print({k: (len(v), int(v[LABEL].sum())) for k, v in dict(train=tr, cal=ca, val=va, test=te, test_seen=te_seen).items()})

    leak = single_feature_auc(tr)
    guard = cfg["leakage_guard"]["max_single_feature_auc"]
    if leak["auc"].max() > guard:
        print(f"WARNING: a single feature reaches AUC {leak['auc'].max():.3f} > {guard} (labels may be too easy)")

    seeds = seeds[:1] if quick else seeds
    folds, n_rounds = cross_validate(tr, seeds, n_splits=3 if quick else 5, compare=not quick)
    cv = summarise_cv(folds)
    print(cv.to_string(index=False))

    booster, _ = _fit_lgb(tr, tr[LABEL].to_numpy(), seeds[0], n_rounds)
    raw = {k: booster.predict(v[FEATURES]) for k, v in dict(cal=ca, val=va, test=te, test_seen=te_seen).items()}
    calib = IsotonicCalibrator().fit(raw["cal"], ca[LABEL])
    p = {k: calib.predict(v) for k, v in raw.items()}
    conf = MondrianConformal(alpha).fit(p["cal"], ca[LABEL])
    nov = RobustNovelty().fit(tr[FEATURES])
    neg_val = raw["val"][va[LABEL].to_numpy() == 0]  # thresholds on the continuous model score (no isotonic ties)
    thr = {"amber_score": float(np.quantile(neg_val, 0.95)), "red_score": float(np.quantile(neg_val, 0.99)),
           "rule": "chosen on the validation split: amber = 5% / red = 1% of normal transfers flagged", "frozen": True}
    thr["amber_p"], thr["red_p"] = (float(v) for v in calib.predict([thr["amber_score"], thr["red_score"]]))

    # ---- the ONE test pass (thresholds already frozen)
    ood_te = nov.flag(te[FEATURES])
    test_metrics, rc = evaluate(te, p["test"], raw["test"], conf, ood_te, thr, follow)
    seen_metrics, _ = evaluate(te_seen, p["test_seen"], raw["test_seen"], conf, nov.flag(te_seen[FEATURES]), thr, follow)
    window = pd.concat([te, te_seen], ignore_index=True)
    p_win = np.concatenate([p["test"], p["test_seen"]])
    raw_win = np.concatenate([raw["test"], raw["test_seen"]])
    _, uns_win = _states(raw_win, conf.state(p_win), nov.flag(window[FEATURES]), thr)
    fair = slices(window, p_win, raw_win, uns_win, thr)
    abl = [] if quick else ablation(tr, va, n_rounds)

    contrib = booster.predict(te[FEATURES], pred_contrib=True)
    imp = np.abs(contrib[:, :-1]).mean(axis=0)
    global_importance = sorted(zip(FEATURES, imp.round(5).tolist()), key=lambda x: -x[1])

    # ---- scored test table (used by AI-6 linker, AI-7 briefs, NB99, demo)
    level, unsure = _states(raw["test"], conf.state(p["test"]), ood_te, thr)
    scored = te[["event_id", "t", "day", "src", "dst", "amount", "channel", LABEL, "is_scam", "scam_family", "case_id",
                 "zone", "tenure_bucket"]].copy()
    scored["p_calibrated"], scored["raw_score"] = p["test"], raw["test"]
    scored["risk_level"], scored["unsure"], scored["ood"] = level, unsure, ood_te
    scored["conformal_state"] = conf.state(p["test"])
    reasons = [top_reasons(contrib[i], te.loc[i, FEATURES].to_dict(), FEATURES)
               for i in range(len(te))] if len(te) <= 200_000 else [[] for _ in range(len(te))]
    scored["reasons"] = [__import__("json").dumps(r, ensure_ascii=False) for r in reasons]

    # ---- figures
    plots.reliability({"calibrated (isotonic)": M.reliability_table(te[LABEL], p["test"]),
                       "raw model score": M.reliability_table(te[LABEL], raw["test"])}, rep / "figures" / "ai1_reliability.png")
    plots.pr_curves({"UVERA AI-1": p["test"], "rule baseline": rule_baseline_score(te) + te["amount"] / 1e7},
                    te[LABEL], rep / "figures" / "ai1_pr_curve.png")
    plots.risk_coverage({"AI-1 with abstention": rc}, rep / "figures" / "ai1_risk_coverage.png")
    plots.bars([f for f, _ in global_importance], [v for _, v in global_importance], rep / "figures" / "ai1_shap_global.png",
               "What drives AI-1 (mean |SHAP|, test)")

    # ---- export (portable JSON/text, no pickles)
    booster.save_model(str(art / "model.txt"))
    write_json(art / "calibrator.json", calib.to_json())
    write_json(art / "conformal.json", conf.to_json())
    write_json(art / "novelty.json", nov.to_json())
    write_json(art / "thresholds.json", thr)
    write_json(art / "features.json", {"features": FEATURES, "groups": GROUPS, "slices": SLICE_COLS})
    scored.to_parquet(art / "test_scores.parquet", index=False)

    summary = {"ai": "AI-1 Pause Check", "model": "LightGBM + isotonic + Mondrian conformal + robust novelty",
               "n_rounds": n_rounds, "splits": day_bounds(world.n_days), "world": world.meta,
               "leakage_single_feature_auc": leak.to_dict("records"), "cv_summary": cv.to_dict("records"),
               "thresholds": thr, "test_unseen_customers": test_metrics, "test_seen_customers": seen_metrics,
               "fairness_slices_test_window": fair, "ablation_validation": abl, "global_importance": global_importance}
    write_json(rep / "metrics_ai1.json", summary)
    folds.to_csv(rep / "ai1_cv_folds.csv", index=False)
    return summary
