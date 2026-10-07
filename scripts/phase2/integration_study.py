"""Phase-2 integration study on the official world (seed 42), using the DEPLOYED phase-1 models unchanged.

Answers the judges:
  Innovation:  "Run ablations such as Pause Check only -> Pause + QR Shield -> Pause + QR + Case Linker, and quantify whether
                linking and evidence generation actually improve analyst decisions beyond simple alert aggregation."
  AI/ML depth: unseen scam families (leave-one-family-out) for AI-1.
  Responsible AI: subgroup FNR gaps (tenure 19.2%-29.0%) -> a validation-chosen, group-aware threshold fix, before/after.
Parts (run all by default, or name them):  linking  loop  lofo  fairness
Everything is causal: the closed loop only uses events that happened before the decision time.
Writes reports/phase2/integration/*.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.eval import metrics as M  # noqa: E402
from uvera_ml.features.ai1 import FEATURES, rule_baseline_score  # noqa: E402
from uvera_ml.graph import linker as L  # noqa: E402
from uvera_ml.models import ai1  # noqa: E402
from uvera_ml.sim.world import World  # noqa: E402
from uvera_ml.uncertainty.calibration import IsotonicCalibrator  # noqa: E402
from uvera_ml.uncertainty.conformal import MondrianConformal  # noqa: E402

OUT = ROOT / "reports" / "phase2" / "integration"
OUT.mkdir(parents=True, exist_ok=True)
ART = ROOT / "artifacts"
LABEL = "label_scam"
DAY = 86400


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load():
    world = World.load(ROOT / "_outputs" / "world_full")
    df = ai1.prepare(world)
    booster = lgb.Booster(model_file=str(ART / "ai1" / "model.txt"))
    calib = IsotonicCalibrator.from_json(json.loads((ART / "ai1" / "calibrator.json").read_text()))
    conf = MondrianConformal.from_json(json.loads((ART / "ai1" / "conformal.json").read_text()))
    thr = json.loads((ART / "ai1" / "thresholds.json").read_text())
    df["raw"] = booster.predict(df[FEATURES])
    df["p"] = calib.predict(df["raw"].to_numpy())
    level = np.where(df["raw"] > thr["red_score"], "high", np.where(df["raw"] > thr["amber_score"], "medium", "low"))
    df["risk_level"] = level
    df["unsure"] = (conf.state(df["p"].to_numpy()) == "unsure") & (level != "low")
    df["p_calibrated"] = df["p"]
    return world, df, thr


# ------------------------------------------------------------------ 1. Case Linker vs simple alert aggregation
def linking_vs_naive(world, df):
    # the exact phase-1 scored test table (same 377 alerts as NB06)
    te = pd.read_parquet(ART / "ai1" / "test_scores.parquet")
    ms = pd.read_parquet(ART / "ai5" / "merchant_scores.parquet")
    cases, meta = L.link_cases(world, te, ms)
    cases_noqr, _ = L.link_cases(world, te, None)
    alerts = te[(te["risk_level"] == "high") | (te["unsure"] & (te["risk_level"] != "low"))].copy()
    truth_mule = world.truth_cases.set_index("case_id")["mule"].to_dict()
    is_mule = set(world.truth_customers.loc[world.truth_customers["is_mule"], "customer_id"])
    n_true = int(alerts["is_scam"].sum())
    cash = world.events[(world.events["mule_flow"] == 1) & world.events["etype"].isin(["cash_out", "qr_pay"])]
    cash = cash[cash["t"] >= alerts["t"].min()]

    def summarise(name, groups, rank_key, finds_downstream: bool, edges_by_group=None):
        groups = sorted(groups, key=rank_key, reverse=True)
        items = len(groups)
        def top(k):
            return float(sum(sum(int(a.is_scam) for a in g["alerts"]) for g in groups[:k]) / max(1, n_true))
        # mule wallets and cash-out points identified (only path tracing sees beyond the first receiver)
        mules_found, cash_found = set(), set()
        for g in groups:
            mules_found |= {w for w in g["wallets"] if w in is_mule}
            cash_found |= set(g.get("cash_event_ids", []))
        cash_case = cash[cash["case_id"].isin({int(a.case_id) for g in groups for a in g["alerts"] if int(a.case_id) >= 0})]
        return {"method": name, "analyst_items": items, "items_reduction_vs_alerts": 1 - items / max(1, len(alerts)),
                "real_scam_alerts_in_top_5": top(5), "real_scam_alerts_in_top_10": top(10), "real_scam_alerts_in_top_20": top(20),
                "mule_wallets_identified": len(mules_found),
                "scam_cashouts_identified": float(cash_case["event_id"].isin(cash_found).mean()) if len(cash_case) else 0.0,
                "sees_downstream_cash_out": finds_downstream}

    # A. no aggregation: one item per alert, ranked by AI-1 probability
    a_items = [{"alerts": [a], "wallets": {a.dst}} for a in alerts.itertuples(index=False)]
    res = [summarise("A. one item per alert (ranked by AI-1)", a_items, lambda g: max(x.p_calibrated for x in g["alerts"]), False)]
    # B. simple aggregation: group alerts by the receiving wallet, ranked by alert count then max probability
    by_dst = defaultdict(list)
    for a in alerts.itertuples(index=False):
        by_dst[a.dst].append(a)
    b_items = [{"alerts": v, "wallets": {k}} for k, v in by_dst.items()]
    res.append(summarise("B. simple aggregation: same receiving wallet", b_items,
                         lambda g: (len(g["alerts"]), max(x.p_calibrated for x in g["alerts"])), False))
    # C/D. UVERA Case Linker (time-respecting money paths + union-find + chain score), without and with QR Shield
    by_eid = {int(a.event_id): a for a in alerts.itertuples(index=False)}
    for name, cs in (("C. UVERA Case Linker without QR Shield", cases_noqr), ("D. UVERA Case Linker + QR Shield", cases)):
        items = [{"alerts": [by_eid[e] for e in c["alert_event_ids"]], "wallets": set(c["wallets"]) | {by_eid[e].dst for e in c["alert_event_ids"]},
                  "cash_event_ids": [x["event_id"] for x in c["edges"] if x["etype"] in ("cash_out", "qr_pay")], "score": c["score"]} for c in cs]
        res.append(summarise(name, items, lambda g: g["score"], True))
    out = {"alerts": int(len(alerts)), "real_scam_alerts": n_true, "methods": res, "linker_meta": meta}
    common.write_json(OUT / "linking_vs_naive.json", out)
    log("linking", json.dumps(res)[:1500])
    return out


# ------------------------------------------------------------------ 2. ablation ladder + closed loop
def closed_loop(world, df, thr):
    """Day-by-day over the test window (all customers). Pause Check alone vs Pause Check + watchlist fed back by the Case
    Linker (wallets in high-score cases found so far are watched; a transfer to a watched wallet is paused)."""
    win = df[df["split"].isin(["test", "test_seen"])].sort_values("t").reset_index(drop=True)
    y, amount = win[LABEL].to_numpy(), win["amount"].to_numpy(float)
    truly = win["is_scam"].to_numpy().astype(bool)  # ground truth (incl. unreported scams)
    rule = np.asarray(rule_baseline_score(win)) >= 2
    ai1_pause = win["risk_level"].to_numpy() == "high"
    days = sorted(win["day"].unique())
    ev_all = world.events
    ms = pd.read_parquet(ART / "ai5" / "merchant_scores.parquet")
    watch = set()
    watch_pause = np.zeros(len(win), bool)
    added_by_day = {}
    victims_all = set(win["src"])
    for d in days:
        idx = np.where(win["day"].to_numpy() == d)[0]
        dst = win["dst"].to_numpy()[idx]
        watch_pause[idx] = np.isin(dst, list(watch)) if watch else False
        # end of day d: link all alerts so far using only events that already happened
        now = (int(d) + 1) * DAY
        seen = win.iloc[: idx[-1] + 1] if len(idx) else win.iloc[:0]
        alerts_so_far = seen[(seen["risk_level"] == "high") | (seen["unsure"] & (seen["risk_level"] != "low"))]
        if len(alerts_so_far):
            wv = SimpleNamespace(events=ev_all[ev_all["t"] < now])
            cases, _ = L.link_cases(wv, alerts_so_far, ms)
            new = set()
            for c in cases:
                if c["score"] >= 0.95 and c["n_alerts"] >= 2:  # only strong, multi-victim cases feed the watchlist
                    new |= set(c["wallets"]) | {e["dst"] for e in c["edges"][:1]}
            new -= victims_all & set(alerts_so_far["src"])
            added_by_day[int(d)] = len(new - watch)
            watch |= new
        log("loop day", d, "watchlist", len(watch))
    loop_pause = ai1_pause | watch_pause

    def stats(name, flag):
        tp, fp = (flag & truly), (flag & ~truly)
        return {"configuration": name, "scams_paused": int(tp.sum()), "scams_total": int(truly.sum()),
                "recall": float(tp.sum() / max(1, truly.sum())),
                "scam_money_paused_bdt": float(amount[tp].sum()), "scam_money_total_bdt": float(amount[truly].sum()),
                "false_pauses": int(fp.sum()), "false_pauses_per_1000_normal": float(1000 * fp.sum() / max(1, (~truly).sum())),
                "precision": float(tp.sum() / max(1, flag.sum()))}

    ladder = [stats("0. Rule only (Tk 5,000+ to a new receiver)", rule),
              stats("1. Pause Check (AI-1) alone", ai1_pause),
              stats("2. Pause Check + Case Linker watchlist (closed loop)", loop_pause)]
    extra = loop_pause & ~ai1_pause
    out = {"window": "test window, all customers (days 100-119)", "transfers": int(len(win)), "ladder": ladder,
           "closed_loop_extra": {"extra_scams_paused": int((extra & truly).sum()), "extra_false_pauses": int((extra & ~truly).sum()),
                                 "extra_scam_money_bdt": float(amount[extra & truly].sum())},
           "watchlist_size_end": len(watch), "watchlist_added_by_day": added_by_day,
           "rule": "watchlist = wallets in linked cases with chain score >= 0.95 and >= 2 alerts, built only from events before the decision day"}
    common.write_json(OUT / "closed_loop.json", out)
    log("loop", json.dumps(out)[:1200])
    return out


# ------------------------------------------------------------------ 3. AI-1 leave-one-scam-family-out
def lofo(world, df):
    tr, ca, va, te = (df[df["split"] == s].reset_index(drop=True) for s in ("train", "cal", "val", "test"))
    te_all = df[df["split"].isin(["test", "test_seen"])].reset_index(drop=True)
    fams = [f for f in sorted(df["scam_family"].dropna().unique()) if str(f) not in ("", "-1", "none", "nan")]
    rows = []
    for fam in fams:
        for held_out in (False, True):
            keep = ~((tr["scam_family"] == fam) & (tr["is_scam"] == 1)) if held_out else np.ones(len(tr), bool)
            t2 = tr[keep]
            b, _ = ai1._fit_lgb(t2, t2[LABEL].to_numpy(), 42, 482)
            neg = b.predict(va[FEATURES])[va[LABEL].to_numpy() == 0]
            red = float(np.quantile(neg, 0.99))
            s = b.predict(te_all[FEATURES])
            m = (te_all["scam_family"] == fam) & (te_all["is_scam"] == 1)
            other = (te_all["is_scam"] == 1) & ~m
            rows.append({"family": str(fam), "held_out_from_training": held_out, "test_scams_of_family": int(m.sum()),
                         "recall_on_family_at_pause": float((s[m.to_numpy()] > red).mean()) if m.any() else None,
                         "recall_on_other_families": float((s[other.to_numpy()] > red).mean()),
                         "train_positives": int(t2[LABEL].sum())})
            log("lofo", rows[-1])
    out = {"protocol": "train without one scam family (its scam transfers removed from training), thresholds frozen on validation "
                       "(1% of normal validation transfers), measured on the whole test window", "rows": rows}
    common.write_json(OUT / "lofo_scam_families.json", out)
    return out


# ------------------------------------------------------------------ 4. fairness: group-aware thresholds (equal opportunity)
def fairness(world, df, thr):
    va = df[df["split"] == "val"].reset_index(drop=True)
    win = df[df["split"].isin(["test", "test_seen"])].reset_index(drop=True)
    g_col = "tenure_bucket"
    global_red = thr["red_score"]
    # target: the validation recall the global threshold achieves overall
    yv = va[LABEL].to_numpy()
    target = float((va["raw"].to_numpy()[yv == 1] > global_red).mean())
    group_thr = {}
    for g, gv in va.groupby(g_col):
        s_pos = gv.loc[gv[LABEL] == 1, "raw"].to_numpy()
        s_neg = gv.loc[gv[LABEL] == 0, "raw"].to_numpy()
        if len(s_pos) < 10:
            group_thr[g] = global_red
            continue
        # highest threshold whose validation recall reaches the target, but never flag more than 2% of the group's normal transfers
        cand = np.quantile(s_pos, 1 - target)
        floor = np.quantile(s_neg, 0.98)
        group_thr[g] = float(max(min(cand, global_red), floor))
    def slice_stats(thr_for):
        rows = []
        for g, gw in win.groupby(g_col):
            t = thr_for(g)
            yy, ff = gw[LABEL].to_numpy() == 1, gw["raw"].to_numpy() > t
            rows.append({"group": g, "n": int(len(gw)), "scams": int(yy.sum()), "threshold": t,
                         "fnr": float(1 - ff[yy].mean()) if yy.any() else None, "fpr": float(ff[~yy].mean())})
        yy, ff = win[LABEL].to_numpy() == 1, np.array([r > thr_for(g) for r, g in zip(win["raw"], win[g_col])])
        overall = {"recall": float(ff[yy].mean()), "false_pauses_per_1000_normal": float(1000 * ff[~yy].mean())}
        return rows, overall
    before, ob = slice_stats(lambda g: global_red)
    after, oa = slice_stats(lambda g: group_thr[g])
    gap = lambda rows: max(r["fnr"] for r in rows if r["fnr"] is not None) - min(r["fnr"] for r in rows if r["fnr"] is not None)  # noqa: E731
    out = {"slice": g_col, "method": "post-processing for equal opportunity: one pause threshold per tenure group, chosen on the "
                                     "VALIDATION window so each group reaches the overall validation recall, capped at 2% of the group's "
                                     "normal transfers; evaluated once on the test window with the same reported labels as the phase-1 fairness report",
           "validation_target_recall": target, "group_thresholds": group_thr, "global_threshold": global_red,
           "before": {"slices": before, "overall": ob, "fnr_gap": gap(before)},
           "after": {"slices": after, "overall": oa, "fnr_gap": gap(after)}}
    common.write_json(OUT / "fairness_tenure.json", out)
    log("fairness", json.dumps(out)[:1500])
    return out


def fairness_budget(world, df, thr):
    """Equal opportunity WITHOUT spending more false pauses: per-tenure thresholds (each a quantile of that group's normal
    validation transfers) chosen on VALIDATION to minimise the FNR gap, subject to: overall validation false-pause rate no
    higher than the global threshold's, and overall validation recall not lower. One test pass afterwards."""
    import itertools
    g_col = "tenure_bucket"
    va = df[df["split"] == "val"].reset_index(drop=True)
    win = df[df["split"].isin(["test", "test_seen"])].reset_index(drop=True)
    groups = sorted(va[g_col].unique())
    levels = [0.004, 0.006, 0.008, 0.01, 0.012, 0.014, 0.016, 0.02]
    qthr = {g: {lv: float(np.quantile(va.loc[(va[g_col] == g) & (va[LABEL] == 0), "raw"], 1 - lv)) for lv in levels} for g in groups}

    def measure(frame, tmap):
        t = frame[g_col].map(tmap).to_numpy()
        ff, yy = frame["raw"].to_numpy() > t, frame[LABEL].to_numpy() == 1
        fnr = {g: float(1 - ff[(frame[g_col] == g).to_numpy() & yy].mean()) for g in groups}
        return {"fnr": fnr, "gap": max(fnr.values()) - min(fnr.values()), "recall": float(ff[yy].mean()),
                "fpr": float(ff[~yy].mean())}

    base = measure(va, {g: thr["red_score"] for g in groups})
    best = None
    for combo in itertools.product(levels, repeat=len(groups)):
        tmap = {g: qthr[g][lv] for g, lv in zip(groups, combo)}
        m = measure(va, tmap)
        if m["fpr"] <= base["fpr"] + 1e-9 and m["recall"] >= base["recall"] - 1e-9 and (best is None or m["gap"] < best[1]["gap"]):
            best = (tmap, m, dict(zip(groups, combo)))
    tmap, val_m, combo = best
    before = measure(win, {g: thr["red_score"] for g in groups})
    after = measure(win, tmap)
    out = {"slice": g_col, "method": fairness_budget.__doc__.strip().replace("\n", " "),
           "validation": {"before": base, "after": val_m, "chosen_false_pause_level_per_group": combo},
           "test_window": {"before": before, "after": after,
                           "false_pauses_per_1000_normal": {"before": 1000 * before["fpr"], "after": 1000 * after["fpr"]}},
           "group_thresholds": tmap, "global_threshold": thr["red_score"]}
    common.write_json(OUT / "fairness_tenure_budget.json", out)
    log("fairness_budget", json.dumps(out["test_window"]))
    return out


def fairness_dial(world, df, thr):
    """Policy dial: lower only the long-tenure (>365d) group's pause threshold step by step (chosen on validation as the
    share of that group's normal transfers paused) and measure, once on the test window, the FNR gap vs false pauses."""
    g_col, grp = "tenure_bucket", ">365d"
    va = df[df["split"] == "val"].reset_index(drop=True)
    win = df[df["split"].isin(["test", "test_seen"])].reset_index(drop=True)
    neg = va.loc[(va[g_col] == grp) & (va[LABEL] == 0), "raw"]
    rows = []
    for lv in [None, 0.008, 0.01, 0.012, 0.015, 0.02, 0.025]:
        t_grp = thr["red_score"] if lv is None else min(thr["red_score"], float(np.quantile(neg, 1 - lv)))
        t = np.where(win[g_col] == grp, t_grp, thr["red_score"])
        ff, yy = win["raw"].to_numpy() > t, win[LABEL].to_numpy() == 1
        fnr = {g: float(1 - ff[(win[g_col] == g).to_numpy() & yy].mean()) for g in sorted(win[g_col].unique())}
        rows.append({"long_tenure_pause_level": lv or "phase-1 global threshold", "fnr": fnr,
                     "fnr_gap": max(fnr.values()) - min(fnr.values()), "recall": float(ff[yy].mean()),
                     "false_pauses_per_1000_normal": float(1000 * ff[~yy].mean())})
        log("dial", rows[-1])
    common.write_json(OUT / "fairness_dial.json", {"method": fairness_dial.__doc__.strip().replace("\n", " "), "rows": rows})


if __name__ == "__main__":
    parts = sys.argv[1:] or ["linking", "loop", "fairness", "lofo"]
    t0 = time.time()
    world, df, thr = load()
    log("loaded", len(df), "transfers in", round(time.time() - t0), "s")
    for p in parts:
        try:
            {"linking": lambda: linking_vs_naive(world, df), "loop": lambda: closed_loop(world, df, thr),
             "lofo": lambda: lofo(world, df), "fairness": lambda: fairness(world, df, thr),
             "fairness2": lambda: fairness_budget(world, df, thr), "dial": lambda: fairness_dial(world, df, thr)}[p]()
        except Exception as e:
            import traceback
            traceback.print_exc()
            log("FAILED", p, repr(e))
