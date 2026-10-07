"""Phase-2 robustness study for AI-1 (Pause Check).

Answers the judges' request: "Add repeated independently generated worlds, distribution-shift tests".
  1. independent worlds: regenerate the full synthetic world with new seeds and re-run the AI-1 protocol
     (LightGBM, isotonic on cal, Mondrian conformal on val, thresholds frozen on val, one test pass on unseen customers);
  2. distribution shift WITHOUT retraining: the deployed phase-1 model (artifacts/ai1) is applied unchanged to worlds whose
     scam process changed (more/fewer scams, smaller scam amounts, older "bought" mule accounts, noisier labels);
  3. the same shifted worlds WITH retraining (does the method recover?).
Usage:  python scripts/phase2/robustness_ai1.py [job ...]   (jobs: seed1..seed5, seed42, shift_<name>)
Writes reports/phase2/robustness/<job>.json; summarise with scripts/phase2/summarise_robustness.py
"""
from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.eval import metrics as M  # noqa: E402
from uvera_ml.features.ai1 import FEATURES, rule_baseline_score  # noqa: E402
from uvera_ml.models import ai1  # noqa: E402
from uvera_ml.sim import world as W  # noqa: E402
from uvera_ml.uncertainty.calibration import IsotonicCalibrator  # noqa: E402
from uvera_ml.uncertainty.conformal import MondrianConformal  # noqa: E402

OUT = ROOT / "reports" / "phase2" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)
N_ROUNDS = 482  # the phase-1 CV-selected number of boosting rounds (reports/metrics_ai1.json)
LABEL = "label_scam"

SHIFTS = {
    "prevalence_x2": {"assumptions": {"rates": {"scam_share_of_p2p": 0.012}}},
    "prevalence_half": {"assumptions": {"rates": {"scam_share_of_p2p": 0.003}}},
    "smaller_amounts": {"patterns_amount_scale": 0.5},
    "older_mules": {"assumptions": {"mule_fresh_share": 0.10}},
    "noisier_labels": {"assumptions": {"rates": {"label_noise": 0.20}}},
    "adaptive_scammers": {"assumptions": {"mule_fresh_share": 0.10}, "patterns_amount_scale": 0.5},
}


def _deep_update(d: dict, u: dict) -> dict:
    for k, v in u.items():
        d[k] = _deep_update(d.get(k, {}), v) if isinstance(v, dict) else v
    return d


def make_world(seed: int, shift: dict | None = None):
    orig = common.load_config

    def patched(name):
        cfg = copy.deepcopy(orig(name))
        if shift and name == "assumptions" and "assumptions" in shift:
            _deep_update(cfg, shift["assumptions"])
        if shift and name == "patterns" and "patterns_amount_scale" in shift:
            s = shift["patterns_amount_scale"]
            for f in cfg["scam_families"].values():
                f["amount_bdt"] = [max(100, int(a * s)) for a in f["amount_bdt"]]
        return cfg

    W.load_config = patched
    try:
        return W.generate_world("full", seed)
    finally:
        W.load_config = orig


def evaluate(te, p, raw, thr, conf):
    y, amount = te[LABEL].to_numpy(), te["amount"].to_numpy(float)
    rule_tb = rule_baseline_score(te) + amount / 1e7
    red = raw > thr["red_score"]
    at5, rule5 = M.at_alert_rate(y, p, 0.05, amount), M.at_alert_rate(y, rule_tb, 0.05, amount)
    cov = conf.coverage(p, y)
    return {
        "n": int(len(y)), "positives": int(y.sum()), "prevalence": float(y.mean()),
        "pr_auc": M.pr_auc(y, p), "roc_auc": M.roc_auc(y, p), "ece": M.ece(y, p),
        "recall_at_5pct": at5["recall"], "precision_at_5pct": at5["precision"],
        "recall_at_red": float(red[y == 1].mean()) if y.sum() else None,
        "false_alerts_per_1000_at_red": M.false_alerts_per_1000(y, red),
        "conformal_coverage_scams": cov.get("class_1"), "conformal_coverage_all": cov.get("overall"),
        "rule_pr_auc": M.pr_auc(y, rule_tb), "rule_recall_at_5pct": rule5["recall"],
    }


def protocol(world, tag: str) -> dict:
    """Retrain on this world with the phase-1 protocol (no CV; fixed rounds), one test pass."""
    t0 = time.time()
    df = ai1.prepare(world)
    tr, ca, va, te = (df[df["split"] == s].reset_index(drop=True) for s in ("train", "cal", "val", "test"))
    leak = ai1.single_feature_auc(tr)["auc"].max()
    booster, _ = ai1._fit_lgb(tr, tr[LABEL].to_numpy(), 42, N_ROUNDS)
    raw = {k: booster.predict(v[FEATURES]) for k, v in dict(cal=ca, val=va, test=te).items()}
    calib = IsotonicCalibrator().fit(raw["cal"], ca[LABEL])
    p = {k: calib.predict(v) for k, v in raw.items()}
    conf = MondrianConformal(0.10).fit(p["val"], va[LABEL])
    neg_val = raw["val"][va[LABEL].to_numpy() == 0]
    thr = {"red_score": float(np.quantile(neg_val, 0.99))}
    res = evaluate(te, p["test"], raw["test"], thr, conf)
    res.update({"max_single_feature_auc": float(leak), "train_rows": int(len(tr)), "train_positives": int(tr[LABEL].sum()),
                "seconds": round(time.time() - t0, 1)})
    return res, df


def deployed(df) -> dict:
    """The phase-1 deployed model, unchanged, on another world's unseen-customer test window."""
    art = ROOT / "artifacts" / "ai1"
    booster = lgb.Booster(model_file=str(art / "model.txt"))
    calib = IsotonicCalibrator.from_json(json.loads((art / "calibrator.json").read_text()))
    conf = MondrianConformal.from_json(json.loads((art / "conformal.json").read_text()))
    thr = json.loads((art / "thresholds.json").read_text())
    te = df[df["split"] == "test"].reset_index(drop=True)
    raw = booster.predict(te[FEATURES])
    return evaluate(te, calib.predict(raw), raw, thr, conf)


def run(job: str):
    t0 = time.time()
    if job.startswith("seed"):
        seed = int(job[4:])
        world = make_world(seed)
        res, df = protocol(world, job)
        out = {"job": job, "kind": "independent_world", "seed": seed, "world_events": int(world.meta["n_events"]),
               "world_scams": int(world.meta["n_scam_transfers"]), "retrained": res, "deployed_model": deployed(df)}
    else:
        name = job.removeprefix("shift_")
        world = make_world(42, SHIFTS[name])
        res, df = protocol(world, job)
        out = {"job": job, "kind": "distribution_shift", "shift": name, "spec": SHIFTS[name],
               "world_events": int(world.meta["n_events"]), "world_scams": int(world.meta["n_scam_transfers"]),
               "deployed_model": deployed(df), "retrained": res}
    out["seconds_total"] = round(time.time() - t0, 1)
    common.write_json(OUT / f"{job}.json", out)
    print(job, json.dumps({k: (v if not isinstance(v, dict) else {kk: round(vv, 4) if isinstance(vv, float) else vv
                                                                  for kk, vv in v.items()}) for k, v in out.items()
                           if k in ("deployed_model", "retrained", "seconds_total")})[:900], flush=True)


if __name__ == "__main__":
    for j in sys.argv[1:]:
        try:
            run(j)
        except Exception as e:  # keep going with the other jobs
            print("FAILED", j, repr(e), flush=True)
