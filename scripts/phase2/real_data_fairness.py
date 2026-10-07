"""Phase-2: fairness of AI-2 on REAL messages (BTTC, Mendeley Data, CC BY 4.0, 2026).

The judges asked for "real-data fairness validation". BTTC has no customer attributes, but it has two groups that matter
for a Bangladeshi scam-text check: the writing (pure Bangla script vs Bangla mixed with English/Latin text) and the channel
(SMS vs Telegram). We check that the check catches scams equally well in each group and flags normal messages equally
rarely, before and after per-group (equal-opportunity) thresholds, with the same protocol as the tenure study:
  - 5 seeds; half of the real messages held out for testing (exact duplicates removed first, as in real_data_validation.py)
  - a pilot model (same AI-2 architecture: character TF-IDF + logistic regression) trained on n real labelled messages
  - the global threshold is set on a separate validation part of the training pool to catch 90% of scams
  - equal opportunity: one threshold per group, each set on validation to catch 90% of that group's scams
  - zero-shot: the served AI-2 model (synthetic training only), per group, as the honest starting point
Writes reports/phase2/real_data_fairness.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT.parent / "external_data"
sys.path.insert(0, str(ROOT / "ml"))

from uvera_ml import common  # noqa: E402
from uvera_ml.models.ai2 import tfidf_lr  # noqa: E402
from uvera_ml.serving.store import ArtifactStore  # noqa: E402
from uvera_ml.serving.text import TextEngine  # noqa: E402

TARGET = 0.90
SEEDS = range(5)


def script_group(t: str) -> str:
    bn = sum("ঀ" <= c <= "৿" for c in t)
    la = sum(c.isascii() and c.isalpha() for c in t)
    return "Bangla script only" if bn + la and bn / (bn + la) > 0.8 else "Bangla mixed with English"


def thr_for_recall(p, y, target=TARGET):
    s = np.sort(p[y == 1])[::-1]
    if not len(s):
        return 0.5
    return float(s[min(len(s) - 1, int(np.ceil(target * len(s))) - 1)])


def rates(p, y, ham, thr):
    flag = p >= thr
    return {"recall": float(flag[y == 1].mean()) if (y == 1).any() else None,
            "fnr": float((~flag)[y == 1].mean()) if (y == 1).any() else None,
            "ham_flagged": float(flag[ham].mean()) if ham.any() else None,
            "n": int(len(y)), "scams": int(y.sum()), "ham": int(ham.sum())}


def group_eval(p, y, ham, groups, thr_of):
    return {g: rates(p[groups == g], y[groups == g], ham[groups == g], thr_of(g)) for g in sorted(set(groups))}


def mean_sd(runs, g, k):
    v = [r[g][k] for r in runs if r[g][k] is not None]
    return {"mean": float(np.mean(v)), "sd": float(np.std(v))} if v else None


def summarise(runs, groups_order):
    out = {}
    for g in groups_order:
        out[g] = {k: mean_sd(runs, g, k) for k in ("recall", "fnr", "ham_flagged")}
        out[g]["n"], out[g]["scams"], out[g]["ham"] = runs[0][g]["n"], runs[0][g]["scams"], runs[0][g]["ham"]
    gaps = [abs(r[groups_order[0]]["fnr"] - r[groups_order[1]]["fnr"]) for r in runs]
    out["fnr_gap_points"] = {"mean": float(100 * np.mean(gaps)), "sd": float(100 * np.std(gaps))}
    return out


def main():
    d = pd.read_parquet(EXT / "BTTC_complete_rows.parquet")
    d["text"] = d["Text_Clean"].fillna(d["Text"]).astype(str).str.strip()
    d = d[d["text"].str.len() > 3].drop_duplicates("text").reset_index(drop=True)
    y = (d["Label"] == "SPAM").to_numpy().astype(int)
    ham = (d["Label"] == "HAM").to_numpy()
    attrs = {"writing": d["Text"].astype(str).map(script_group).to_numpy(), "channel": d["Source"].astype(str).to_numpy()}
    eng = TextEngine(ArtifactStore([ROOT]))
    p0 = np.asarray(eng.scam_prob(d["text"].tolist()))

    result = {"dataset": "BTTC - Bangla Telegram and Text Communications (Mendeley Data, CC BY 4.0, 2026)",
              "protocol": __doc__.split("rarely, before")[1].strip() if "rarely, before" in __doc__ else "",
              "target_recall": TARGET, "messages": int(len(d)), "attributes": {}}
    for attr, groups in attrs.items():
        order = sorted(set(groups))
        res = {"groups": {g: {"messages": int((groups == g).sum()), "scams": int(y[groups == g].sum()), "ham": int(ham[groups == g].sum())} for g in order}}
        # zero-shot served model: one threshold for 90% recall on all real messages (an oracle-favourable choice), per group
        t0 = thr_for_recall(p0, y)
        res["zero_shot_served_model"] = group_eval(p0, y, ham, groups, lambda g: t0)
        for n in (300, 3000):
            before, after, rew, rew_eo = [], [], [], []
            for seed in SEEDS:
                idx = np.random.default_rng(seed).permutation(len(d))
                test, pool = idx[: len(d) // 2], idx[len(d) // 2:]
                tr, va = pool[:n], pool[n:n + 2000] if n < 3000 else pool[n:]
                for weighted, one, eo in ((False, before, after), (True, rew, rew_eo)):
                    m = common_fit(d["text"].iloc[tr], y[tr], cell_weights(groups[tr], y[tr]) if weighted else None)
                    pv, pt = m.predict_proba(d["text"].iloc[va])[:, 1], m.predict_proba(d["text"].iloc[test])[:, 1]
                    tg = thr_for_recall(pv, y[va])
                    tgrp = {g: thr_for_recall(pv[groups[va] == g], y[va][groups[va] == g]) for g in order}
                    one.append(group_eval(pt, y[test], ham[test], groups[test], lambda g: tg))
                    eo.append(group_eval(pt, y[test], ham[test], groups[test], lambda g: tgrp[g]))
            res[f"pilot_{n}_real_labels"] = {"one_threshold": summarise(before, order), "equal_opportunity": summarise(after, order),
                                             "group_balanced_training": summarise(rew, order),
                                             "group_balanced_training_plus_equal_opportunity": summarise(rew_eo, order)}
            print(attr, n, {k: round(v["fnr_gap_points"]["mean"], 1) for k, v in res[f"pilot_{n}_real_labels"].items()}, flush=True)
        result["attributes"][attr] = res
    common.write_json(ROOT / "reports" / "phase2" / "real_data_fairness.json", result)


def cell_weights(g, y):
    """Group-balanced training: every (group, scam/not scam) cell gets the same total weight, so the model cannot learn
    'this channel/writing style means scam' from how the training data happens to be composed."""
    cells = pd.Series(list(zip(g, y)))
    counts = cells.map(cells.value_counts())
    return (len(cells) / (cells.nunique() * counts)).to_numpy(dtype=float)


def common_fit(X, Y, w=None):
    m = tfidf_lr()
    return m.fit(X, Y) if w is None else m.fit(X, Y, logisticregression__sample_weight=w)


if __name__ == "__main__":
    main()
