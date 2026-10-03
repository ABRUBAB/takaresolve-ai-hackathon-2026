"""NB99: gather every AI's measured results into one summary for the Trust Center, README and report.

Rule: a number is shown only if a notebook measured it. Missing results are reported as "not measured yet".
Also writes one model card per AI and a fairness report, generated from the same result files.
"""
from __future__ import annotations

import json
from pathlib import Path

from uvera_ml.common import write_json
from uvera_ml.eval import plots

AIS = {"ai1": "AI-1 Pause Check", "ai2": "AI-2 Scam Text Sentinel", "ai3": "AI-3 Cash-Flow Guardian",
       "ai4": "AI-4 Agent Liquidity Copilot", "ai5": "AI-5 QR Shield", "ai6": "AI-6 Case Linker", "ai7": "AI-7 Grounded Brief"}
NOTEBOOK = {"ai1": "NB01", "ai2": "NB02", "ai3": "NB03", "ai4": "NB04", "ai5": "NB05", "ai6": "NB06", "ai7": "NB07"}
NM = "not measured yet"
SERVED_TEXT_MODEL = "tfidf_lr"  # the API serves the character TF-IDF model: it runs on a CPU-only server


def _get(d, *path, default=NM):
    for p in path:
        if not isinstance(d, dict) or p not in d or d[p] is None:
            return default
        d = d[p]
    return d


def _row(rows, model):
    return next((r for r in rows or [] if isinstance(r, dict) and r.get("model") == model), {})


def _test_backtest(a: dict, model: str) -> dict:
    return next((r for r in a.get("backtest", []) if r.get("split") == "test" and r.get("model") == model), {})


def headline(m: dict) -> dict:
    a1, a2, a3, a4, a5, a6, a7 = (m.get(k, {}) for k in AIS)
    a2_served = _row(a2.get("test_heldout_style_B"), SERVED_TEXT_MODEL) if a2 else {}
    w3, w4 = _get(a3, "winner_on_validation", default=None), _get(a4, "winner_on_validation", default=None)
    return {
        "ai1": {"pr_auc": _get(a1, "test_unseen_customers", "model", "pr_auc"),
                "pr_auc_rule_baseline": _get(a1, "test_unseen_customers", "rule_baseline", "pr_auc"),
                "recall_at_5pct_alert_rate": _get(a1, "test_unseen_customers", "model", "at_5pct_alert_rate", "recall"),
                "recall_at_5pct_rule_baseline": _get(a1, "test_unseen_customers", "rule_baseline", "at_5pct_alert_rate", "recall"),
                "false_alerts_per_1000": _get(a1, "test_unseen_customers", "model", "false_alerts_per_1000_at_red"),
                "false_alerts_per_1000_rule_baseline": _get(a1, "test_unseen_customers", "rule_baseline", "false_alerts_per_1000"),
                "recall_at_pause": _get(a1, "test_unseen_customers", "model", "recall_at_red"),
                "precision_at_pause": _get(a1, "test_unseen_customers", "model", "precision_at_red"),
                "ece": _get(a1, "test_unseen_customers", "model", "ece_calibrated"),
                "conformal_coverage": _get(a1, "test_unseen_customers", "conformal"),
                "unsure_rate": _get(a1, "test_unseen_customers", "unsure_rate"),
                "error_at_80pct_coverage": _get(a1, "test_unseen_customers", "selective", "error_at_80pct_coverage"),
                "error_at_100pct_coverage": _get(a1, "test_unseen_customers", "selective", "error_at_100pct_coverage"),
                "loss_prevented_bdt": _get(a1, "test_unseen_customers", "loss_prevented_bdt")},
        "ai2": {"served_model": SERVED_TEXT_MODEL if a2 else NM, "best_on_cv": _get(a2, "served_model_chosen_on_cv"),
                "embedder": _get(a2, "embedder"),
                "heldout_style_verdict_pr_auc": a2_served.get("verdict_pr_auc", NM), "heldout_macro_f1": a2_served.get("macro_f1", NM),
                "served_by_language": _get(a2, "served_by_language"), "external_uci": _get(a2, "external_uci_sms_spam")},
        "ai3": {"winner": w3 or NM, "winner_test": _test_backtest(a3, w3) or NM, "naive_test": _test_backtest(a3, "seasonal_naive") or NM,
                "shortfall": _get(a3, "shortfall_probability_test")},
        "ai4": {"winner": w4 or NM, "winner_test": _test_backtest(a4, w4) or NM, "naive_test": _test_backtest(a4, "seasonal_naive") or NM,
                "cash_to_hold": _get(a4, "cash_to_hold_test"), "stockout": _get(a4, "stockout_probability_test"),
                "noise_floor": _get(a4, "noise_floor_perfect_knowledge")},
        "ai5": {"pr_auc_seen": _get(a5, "test", "pr_auc_seen_families"), "precision_at_k": _get(a5, "test", "weekly_precision_at_k"),
                "unseen_family_D": _get(a5, "test", "unseen_family_D"),
                "recall_family_D": _get(a5, "test", "recall_by_family", "D_rotating_ring"),
                "fpr_honest_round_price": _get(a5, "test", "fpr_honest_round_price_shops"),
                "fpr_honest_all": _get(a5, "test", "fpr_honest_all")},
        "ai6": _get(a6, "linking"),
        "ai7": {k: _get(a7, k) for k in ("validator_pass_rate_llm", "fallback_rate", "shown_text_valid_rate",
                                          "injection_raw_success_rate", "injection_shown_success_rate", "llm")},
    }


def fairness_summary(m: dict) -> list[dict]:
    rows = []
    for r in m.get("ai1", {}).get("fairness_slices_test_window", []):
        rows.append({"ai": "AI-1", **r})
    a5 = m.get("ai5", {}).get("test", {})
    for size, v in (a5.get("fpr_by_size") or {}).items():
        rows.append({"ai": "AI-5", "slice": "merchant_size", "group": size, "fpr": v})
    a2 = m.get("ai2", {})
    for lang, v in (a2.get("served_by_language") or a2.get("test_by_language_served") or {}).items():
        rows.append({"ai": "AI-2", "slice": "language", "group": lang, **v})
    return rows


def served_text_by_language(repo: str | Path) -> dict | None:
    """Score the held-out writing style (family B) by language with the exact text model the API serves.

    NB02 reports per-language results for its cross-validation winner; this adds them for the served model.
    Returns None (never raises) when the artifacts are missing.
    """
    try:
        import numpy as np
        import pandas as pd
        from sklearn.metrics import f1_score

        from uvera_ml.eval import metrics as M
        from uvera_ml.serving.store import ArtifactStore
        from uvera_ml.serving.text import TextEngine

        repo = Path(repo)
        corpus = repo / "artifacts" / "ai2" / "corpus.parquet"
        if not corpus.exists():
            return None
        eng = TextEngine(ArtifactStore([repo]))
        if getattr(eng, "source", "") != "official":
            return None
        c = pd.read_parquet(corpus)
        t = c[c["family"] == "B"].reset_index(drop=True)
        p = np.asarray(eng.scam_prob(t["text"].tolist()), float)
        y = (t["label"] != "legit").astype(int).to_numpy()
        out = {"model": SERVED_TEXT_MODEL, "overall": {"n": int(len(t)), "verdict_pr_auc": M.pr_auc(y, p)}}
        for lang, idx in t.groupby("language").indices.items():
            out[lang] = {"n": int(len(idx)), "verdict_pr_auc": M.pr_auc(y[idx], p[idx]),
                         "verdict_f1_at_0.5": float(f1_score(y[idx], (p[idx] >= 0.5).astype(int)))}
        return out
    except Exception as e:  # noqa: BLE001 - an optional extra; the summary must still be written
        print("served_text_by_language skipped:", repr(e)[:200])
        return None


def _load(reports_dir: Path) -> tuple[dict, dict]:
    m, versions = {}, {}
    for k in AIS:
        p = reports_dir / f"metrics_{k}.json"
        if p.exists():
            m[k] = json.loads(p.read_text(encoding="utf-8"))
        v = reports_dir / f"versions_{NOTEBOOK[k].lower()}.json"
        if v.exists():
            versions[k] = json.loads(v.read_text(encoding="utf-8"))
    return m, versions


def build_summary(reports_dir: str | Path, out: str | Path, repo: str | Path | None = None) -> dict:
    reports_dir, out = Path(reports_dir), Path(out)
    m, versions = _load(reports_dir)
    if "ai2" in m:
        by_lang = served_text_by_language(repo or reports_dir.parent)
        if by_lang:
            m["ai2"]["served_by_language"] = {k: v for k, v in by_lang.items() if k not in ("model", "overall")}
    head = headline(m)
    summary = {"available": {AIS[k]: k in m for k in AIS}, "headline": head, "fairness": fairness_summary(m),
               "ablation_ai1": m.get("ai1", {}).get("ablation_validation", NM),
               "cv_ai1": m.get("ai1", {}).get("cv_summary", NM), "cv_ai5": m.get("ai5", {}).get("cv_summary_train", NM),
               "backtest_ai3": m.get("ai3", {}).get("backtest", NM), "backtest_ai4": m.get("ai4", {}).get("backtest", NM),
               "world": m.get("ai1", {}).get("world", NM),
               "run_commits": {AIS[k]: v.get("uvera_commit") for k, v in versions.items()},
               "note": "All results are on synthetic data: they show that the pipeline works, not real-world accuracy."}
    (out / "reports" / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "reports" / "metrics.json", summary)
    a1 = head["ai1"]
    if isinstance(a1["recall_at_5pct_alert_rate"], float):
        plots.bars(["UVERA AI-1", "rule baseline"], [a1["recall_at_5pct_alert_rate"], a1["recall_at_5pct_rule_baseline"]],
                   out / "reports" / "figures" / "summary_recall_vs_rule.png", "Scams caught at the same 5% alert rate", "recall")
    (out / "reports" / "summary.md").write_text(to_markdown(summary), encoding="utf-8")
    cards = out / "reports" / "model_cards"
    cards.mkdir(parents=True, exist_ok=True)
    for name, text in model_cards(m, versions).items():
        (cards / name).write_text(text, encoding="utf-8")
    (out / "reports" / "fairness.md").write_text(fairness_markdown(summary["fairness"]), encoding="utf-8")
    return summary


# ------------------------------------------------------------------ formatting
def _fmt(v, kind: str = "num") -> str:
    if isinstance(v, bool) or v is None or v == NM or (isinstance(v, str) and not v):
        return "—"
    if isinstance(v, (int, float)):
        if kind == "pct":
            return f"{v * 100:.1f}%"
        if kind == "int":
            return f"{int(round(v)):,}"
        if kind == "tk":
            return f"Tk {v:,.0f}"
        if kind == "d1":
            return f"{v:.1f}"
        return f"{v:.3f}" if isinstance(v, float) else f"{v:,}"
    return str(v)


def to_markdown(s: dict) -> str:
    h = s["headline"]
    a3w, a3n, a4w, a4n = h["ai3"]["winner_test"], h["ai3"]["naive_test"], h["ai4"]["winner_test"], h["ai4"]["naive_test"]
    c4 = h["ai4"]["cash_to_hold"] if isinstance(h["ai4"]["cash_to_hold"], dict) else {}
    nf4 = h["ai4"]["noise_floor"] if isinstance(h["ai4"]["noise_floor"], dict) else {}
    sh = h["ai3"]["shortfall"] if isinstance(h["ai3"]["shortfall"], dict) else {}
    a6 = h["ai6"] if isinstance(h["ai6"], dict) else {}
    top5 = _get(a6, "real_scam_alerts_in_top_cases", "5")
    rows = [
        ("AI-1 Pause Check", "Scams caught when 5% of transfers are flagged", h["ai1"]["recall_at_5pct_alert_rate"], h["ai1"]["recall_at_5pct_rule_baseline"], "pct"),
        ("AI-1 Pause Check", "PR-AUC on customers never seen in training", h["ai1"]["pr_auc"], h["ai1"]["pr_auc_rule_baseline"], "num"),
        ("AI-1 Pause Check", "False pauses per 1,000 normal transfers", h["ai1"]["false_alerts_per_1000"], h["ai1"]["false_alerts_per_1000_rule_baseline"], "d1"),
        ("AI-1 Pause Check", "Calibration error (ECE)", h["ai1"]["ece"], None, "num"),
        ("AI-2 Scam Text", f"Verdict PR-AUC, unseen writing style (served model: {h['ai2']['served_model']})", h["ai2"]["heldout_style_verdict_pr_auc"], None, "num"),
        ("AI-2 Scam Text", "Scam-family macro F1, unseen writing style", h["ai2"]["heldout_macro_f1"], None, "num"),
        ("AI-3 Cash-Flow", f"Forecast error, MASE ({h['ai3']['winner']})", _get(a3w, "mase"), _get(a3n, "mase"), "num"),
        ("AI-3 Cash-Flow", "80% range holds the truth (target 0.80)", _get(a3w, "coverage_80"), _get(a3n, "coverage_80"), "num"),
        ("AI-3 Cash-Flow", "Shortfall warning PR-AUC (vs history)", _get(sh, "pr_auc"), _get(sh, "pr_auc_baseline"), "num"),
        ("AI-4 Liquidity", f"Forecast error, MASE ({h['ai4']['winner']})", _get(a4w, "mase"), _get(a4n, "mase"), "num"),
        ("AI-4 Liquidity", "Days short of cash: hold the 90% forecast (vs usual cash)",
         _get(c4, "forecast_q90", "days_short_of_cash"), _get(c4, "usual_cash", "days_short_of_cash"), "pct"),
        ("AI-4 Liquidity", "Share of the best possible gain over naive reached (perfect-knowledge limit = 100%)",
         _get(nf4, "share_of_possible_gain_test", "pinball_mean"), None, "pct"),
        ("AI-5 QR Shield", "Real cash-out shops among the 20 reviewed each week", h["ai5"]["precision_at_k"], None, "pct"),
        ("AI-5 QR Shield", "Honest round-price shops wrongly flagged", h["ai5"]["fpr_honest_round_price"], None, "pct"),
        ("AI-5 QR Shield", "Recall on a disguise type never seen in training", h["ai5"]["recall_family_D"], None, "pct"),
        ("AI-6 Case Linker", "Fewer items for analysts (alerts → cases)", _get(a6, "analyst_items_reduction"), None, "pct"),
        ("AI-6 Case Linker", "Real scam alerts inside the top 5 cases", top5, None, "pct"),
        ("AI-7 Grounded Brief", "Prompt-injection attacks shown to users", h["ai7"]["injection_shown_success_rate"], None, "pct"),
    ]
    lines = ["# UVERA — measured results (synthetic data)", "", s["note"], "",
             "| AI | What is measured (test data the model never saw) | UVERA | Baseline |", "|---|---|---|---|"]
    lines += [f"| {a} | {k} | {_fmt(v, kind)} | {_fmt(b, kind) if b is not None else '—'} |" for a, k, v, b, kind in rows]
    lines += ["", "Baselines: AI-1 a simple rule (large amount to a new receiver) flagging the same number of transfers; AI-3/AI-4 "
              "seasonal-naive forecasts and historical frequencies; AI-4 'usual cash' = the agent's normal cash on hand.",
              "Each AI's details are in [`model_cards/`](model_cards) and fairness slices in [`fairness.md`](fairness.md)."]
    return "\n".join(lines) + "\n"


def fairness_markdown(rows: list[dict]) -> str:
    out = ["# Fairness slices (synthetic data)", "",
           "Error rates by group on the test data. Large gaps would be flagged here; they are reported even when they look bad. "
           "No sensitive attributes are used or invented.", ""]
    a1 = [r for r in rows if r["ai"] == "AI-1"]
    if a1:
        out += ["## AI-1 Pause Check (test window, pause threshold)", "",
                "| Slice | Group | Transfers | Scams | False-positive rate | Missed scams (FNR) | Calibration error | 'Not sure' rate |",
                "|---|---|---|---|---|---|---|---|"]
        out += [f"| {r.get('slice')} | {r.get('group')} | {_fmt(r.get('n'), 'int')} | {_fmt(r.get('positives'), 'int')} | "
                f"{_fmt(r.get('fpr_at_red'), 'pct')} | {_fmt(r.get('fnr_at_red'), 'pct')} | {_fmt(r.get('ece'))} | {_fmt(r.get('unsure_rate'), 'pct')} |"
                for r in a1]
        out.append("")
    a2 = [r for r in rows if r["ai"] == "AI-2"]
    if a2:
        out += ["## AI-2 Scam Text (held-out writing style, served model)", "", "| Language | Messages | Verdict PR-AUC | F1 at 0.5 |", "|---|---|---|---|"]
        out += [f"| {r.get('group')} | {_fmt(r.get('n'), 'int')} | {_fmt(r.get('verdict_pr_auc'))} | {_fmt(r.get('verdict_f1_at_0.5'))} |" for r in a2]
        out.append("")
    a5 = [r for r in rows if r["ai"] == "AI-5"]
    if a5:
        out += ["## AI-5 QR Shield (honest shops wrongly flagged, by size)", "", "| Shop size | False-positive rate |", "|---|---|"]
        out += [f"| {r.get('group')} | {_fmt(r.get('fpr'), 'pct')} |" for r in a5]
        out.append("")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ model cards
CARD_FACTS = {
    "ai1": {
        "task": "Scam risk of a draft person-to-person transfer, before the customer confirms it.",
        "inputs": "19 features known before the transfer: sender (9), receiver (6), moment (4). Leakage-guarded: no single feature separates scams with AUC above 0.80.",
        "model": "LightGBM, chosen over logistic regression, XGBoost and CatBoost by StratifiedGroupKFold (5 folds × 5 seeds, grouped by sender).",
        "baseline": "Rule: amount of Tk 5,000 or more to a receiver never paid before, at the same alert rate.",
        "uncertainty": "Isotonic calibration; Mondrian conformal sets (90%); robust novelty flag. Both labels in the set (on a non-low score) or an unusual input → \"not sure\" → a person checks.",
        "explanation": "Exact TreeSHAP contributions → top-3 reasons in Bangla and English (risk-raising, or what looked normal for a low-risk draft); counterfactual amount.",
        "use": "Decision support inside the send-money flow. The customer is never blocked; a hold on a large high-risk transfer needs staff approval.",
        "not_for": "Automatic blocking, credit or account decisions; real customers without retraining on governed data.",
        "limits": "Synthetic data: scam families were designed by the team. 10% label noise and honest look-alikes reduce, but do not remove, the risk that real scams are harder.",
    },
    "ai2": {
        "task": "Is a received message a scam, which of six scam families, and which phrases moved the verdict.",
        "inputs": "Message text in Bangla, Banglish or English (synthetic: templates + Gemini-generated, never real messages).",
        "model": f"Served live: character TF-IDF (2–5-grams) + logistic regression ({SERVED_TEXT_MODEL}), because it runs on a CPU-only server. Compared with BGE-M3 embeddings + logistic regression and BGE-M3 + an evidential (Dirichlet) head.",
        "baseline": "The three models compared with each other; external sanity test on the UCI SMS Spam Collection (English advertising spam, a different task).",
        "uncertainty": "Isotonic-calibrated scam probability: likely scam ≥ 0.7, likely safe ≤ 0.3, otherwise \"not sure\".",
        "explanation": "Phrase occlusion: remove a phrase and measure how much the scam probability drops.",
        "use": "Customers check a suspicious message before acting on it.",
        "not_for": "Filtering or deleting messages; any decision without the person reading the result.",
        "limits": "Trained and tested on synthetic text. On real English spam (UCI) the scores drop sharply, so real-world performance is not proven.",
    },
    "ai3": {
        "task": "7-day forecast of a customer's net cash flow and the chance the balance ends the week below a safety floor.",
        "inputs": "Daily money in and out per customer + calendar covariates (weekday, day of month, salary week, month end, festival).",
        "model": "Chronos-2 (zero-shot foundation model), LightGBM-quantile (lags 7–28 days plus the same calendar day 1 and 2 months back, because pay day and bill day repeat monthly) and seasonal-naive, compared by rolling-origin backtest; the winner is chosen on validation pinball loss. The live API serves LightGBM-quantile (CPU-only server).",
        "baseline": "Seasonal-naive forecast; historical low-balance frequency for the warning.",
        "uncertainty": "10/50/90% quantile bands; the shortfall probability comes from the empirical distribution of validation residuals.",
        "explanation": "Heaviest spending weeks; the forecast band itself.",
        "use": "A weekly heads-up and savings plans that leave room for a bad month. Nothing moves automatically.",
        "not_for": "Lending or credit scoring.",
        "limits": "Synthetic cash flows. The warning has modest skill over history; the forecast itself clearly beats seasonal-naive.",
    },
    "ai4": {
        "task": "How much cash an agent should hold each day for a 90%-safe day.",
        "inputs": "Daily cash-out demand per agent + the same calendar covariates as AI-3.",
        "model": "Same three forecasters as AI-3; the winner on validation pinball loss is used. Cash to hold = the 90% forecast.",
        "baseline": "Seasonal-naive forecast; the agent's usual cash on hand (1.5 × average daily cash-out, an assumption); the same extra cash spread evenly.",
        "uncertainty": "10/50/90% quantile bands; day-level stock-out probability from validation residuals (shown for transparency only).",
        "explanation": "The forecast band and the extra cash above the usual amount.",
        "use": "Planning cash top-ups. No yes/no alarm is shown.",
        "not_for": "Automatic cash movements or limits on agents.",
        "limits": "Which day of an agent's week runs short could not be predicted better than chance, so no day is flagged; a flat top-up with the same total cash performs about as well as the forecast amount in this synthetic world.",
    },
    "ai5": {
        "task": "Find shops whose Bangla QR payments look like disguised cash-out.",
        "inputs": "16 merchant-week features, most relative to shops of the same type, area and size (round amounts, bursts, payments right after a cash-in, wallet drain, one-time payers, …).",
        "model": "Rank fusion: 70% LightGBM + 30% Isolation Forest. Disguise family D (rotating ring) is held out of training entirely.",
        "baseline": "Peer z-score alone.",
        "uncertainty": "Isotonic calibration; Mondrian conformal → grey \"not sure, a person checks\".",
        "explanation": "Top reasons per shop and a peer comparison.",
        "use": "Weekly review list for analysts (top 20 shop-weeks); agents see only zone-level totals.",
        "not_for": "Automatic merchant caps or closures; naming shops to agents.",
        "limits": "The never-seen disguise type is caught far less often; fee leakage uses an assumed 1.5% cash-out fee inside the public 2026 range.",
    },
    "ai6": {
        "task": "Join many alerts into a few evidence-backed cases.",
        "inputs": "High-risk transfers from AI-1, flagged shops from AI-5 and the money paths between wallets, shops and agents.",
        "model": "Time-respecting path tracing (≤ 3 hops, ≤ 48 hours) + union-find linking + a transparent chain score; Louvain communities for ring discovery.",
        "baseline": "One alert = one item for the analyst.",
        "uncertainty": "Weak links are shown as weak; the chain score formula is shown to the analyst.",
        "explanation": "The evidence subgraph is the explanation; evidence lines E1–E5.",
        "use": "Operations case queue with a dispute-deadline clock (business rules).",
        "not_for": "Automatic holds; every action needs an analyst with a written reason (audit log).",
        "limits": "Linking quality depends on AI-1 and AI-5 alerts; synthetic money paths.",
    },
    "ai7": {
        "task": "Short Bangla and English explanation that only restates the evidence the other AIs produced.",
        "inputs": "Structured evidence (reasons, rules, case facts) + retrieved policy cards.",
        "model": "Gemini API (structured JSON output) with a deterministic validator and a template fallback; policy cards retrieved by embedding similarity.",
        "baseline": "Template text built directly from the evidence.",
        "uncertainty": "Inherits the upstream state; must say \"not sure\" when the case is not sure.",
        "explanation": "Cites evidence ids and policy-card ids.",
        "use": "Customer, agent and analyst screens.",
        "not_for": "Any decision; the language model never decides anything.",
        "limits": "Measured on synthetic evidence only; the validator rejects new numbers, links, phone numbers, certainty claims and contradictions.",
    },
}


def _metrics_lines(k: str, a: dict) -> list[str]:
    g = lambda *p, kind="num": _fmt(_get(a, *p), kind)  # noqa: E731
    if k == "ai1":
        t = "test_unseen_customers"
        return [f"- Test: {g(t, 'n', kind='int')} transfers from customers never seen in training, {g(t, 'positives', kind='int')} scams.",
                f"- Scams caught at a 5% alert rate: **{g(t, 'model', 'at_5pct_alert_rate', 'recall', kind='pct')}** (rule: {g(t, 'rule_baseline', 'at_5pct_alert_rate', 'recall', kind='pct')}).",
                f"- PR-AUC {g(t, 'model', 'pr_auc')} (rule {g(t, 'rule_baseline', 'pr_auc')}); ROC-AUC {g(t, 'model', 'roc_auc')}.",
                f"- At the pause threshold: recall {g(t, 'model', 'recall_at_red', kind='pct')}, precision {g(t, 'model', 'precision_at_red', kind='pct')}, "
                f"{g(t, 'model', 'false_alerts_per_1000_at_red', kind='d1')} false pauses per 1,000 normal transfers (rule {g(t, 'rule_baseline', 'false_alerts_per_1000', kind='d1')}).",
                f"- Calibration error (ECE) {g(t, 'model', 'ece_calibrated')}; Brier {g(t, 'model', 'brier')}.",
                f"- Conformal coverage {g(t, 'conformal', 'overall', kind='pct')} (target 90%); shown as \"not sure\" to customers: {g(t, 'unsure_rate', kind='pct')}."]
    if k == "ai2":
        served = _row(a.get("test_heldout_style_B"), SERVED_TEXT_MODEL)
        lines = [f"- Corpus: {g('corpus', 'total', kind='int')} synthetic messages; best on cross-validation: {g('served_model_chosen_on_cv')}.",
                 "- Held-out writing style (never seen in training):"]
        for r in a.get("test_heldout_style_B", []):
            lines.append(f"  - {r['model']}{' (served)' if r['model'] == SERVED_TEXT_MODEL else ''}: verdict PR-AUC {_fmt(r.get('verdict_pr_auc'))}, "
                         f"scam-family macro F1 {_fmt(r.get('macro_f1'))}, ECE {_fmt(r.get('verdict_ece'))}")
        for lang, v in (a.get("served_by_language") or {}).items():
            lines.append(f"  - served model, {lang}: PR-AUC {_fmt(v.get('verdict_pr_auc'))}, F1 {_fmt(v.get('verdict_f1_at_0.5'))}")
        uci = a.get("external_uci_sms_spam") or {}
        if uci:
            lines.append("- External real English SMS spam (UCI, a different task): " + ", ".join(
                f"{m} PR-AUC {_fmt(v.get('verdict_pr_auc'))}" for m, v in uci.items()) + f" (spam share {_fmt(next(iter(uci.values())).get('spam_share'), 'pct')}).")
        if not served:
            lines.append("- The served model's held-out result is not available.")
        return lines
    if k in ("ai3", "ai4"):
        w = _get(a, "winner_on_validation", default=None)
        lines = [f"- Winner on validation: **{w or '—'}**. Test backtest:"]
        for r in [r for r in a.get("backtest", []) if r.get("split") == "test"]:
            lines.append(f"  - {r['model']}: MASE {_fmt(r.get('mase'))}, pinball {_fmt(r.get('pinball_mean'), 'int')}, 80% coverage {_fmt(r.get('coverage_80'))}")
        lines.append("- Validation backtest (chooses the winner; " + ("its weeks include pay days" if k == "ai3" else "busier weeks") + "):")
        for r in [r for r in a.get("backtest", []) if r.get("split") == "val"]:
            lines.append(f"  - {r['model']}: MASE {_fmt(r.get('mase'))}, pinball {_fmt(r.get('pinball_mean'), 'int')}, 80% coverage {_fmt(r.get('coverage_80'))}")
        if k == "ai3":
            lines.append(f"- Shortfall probability (test): PR-AUC {g('shortfall_probability_test', 'pr_auc')} vs history {g('shortfall_probability_test', 'pr_auc_baseline')}; "
                         f"Brier {g('shortfall_probability_test', 'brier')} vs {g('shortfall_probability_test', 'brier_baseline')}; ECE {g('shortfall_probability_test', 'ece')}.")
            sv = a.get("served_live_model")
            if sv and sv != w and a.get("shortfall_probability_test_served"):
                lines.append(f"- Served live ({sv}): shortfall PR-AUC {g('shortfall_probability_test_served', 'pr_auc')}; "
                             f"ECE {g('shortfall_probability_test_served', 'ece')}.")
        else:
            c = a.get("cash_to_hold_test") or {}
            for key, label in (("usual_cash", "usual cash on hand"), ("forecast_q90", "hold the 90% forecast (served)"),
                               ("same_extra_cash_spread_flat", "same extra cash spread evenly"), ("seasonal_naive_q90", "seasonal-naive 90% level")):
                if key in c:
                    lines.append(f"- Days short of cash, {label}: **{_fmt(c[key].get('days_short_of_cash'), 'pct')}** (mean cash {_fmt(c[key].get('mean_cash_bdt'), 'tk')}).")
            if a.get("day_ranking_test"):
                lines.append(f"- Picking the two riskiest days of an agent's week: precision {g('day_ranking_test', 'model', 'precision', kind='pct')} vs chance "
                             f"{g('day_ranking_test', 'chance_precision', kind='pct')} → no day is flagged.")
            if a.get("agent_ranking_test"):
                lines.append(f"- Ranking agents most at risk each week (top 20%): precision {g('agent_ranking_test', 'model', 'precision', kind='pct')} vs history "
                             f"{g('agent_ranking_test', 'history_baseline', 'precision', kind='pct')}.")
            nf = a.get("noise_floor_perfect_knowledge") or {}
            if isinstance(nf.get("test"), dict):
                lines.append(f"- Best possible forecast (a simulated forecaster that knows every balance and mule cash-out on the day): test MASE "
                             f"{_fmt(nf['test'].get('mase'))}, pinball {_fmt(nf['test'].get('pinball_mean'), 'int')}. UVERA reaches "
                             f"**{g('noise_floor_perfect_knowledge', 'share_of_possible_gain_test', 'pinball_mean', kind='pct')}** of the possible "
                             "improvement over seasonal-naive; the rest is chance that no model can predict.")
        return lines
    if k == "ai5":
        lines = [f"- Test: {g('test', 'n_merchant_weeks', kind='int')} merchant-weeks, {g('test', 'disguised_weeks', kind='int')} disguised.",
                 f"- Real cash-out shops among the 20 reviewed each week: **{g('test', 'weekly_precision_at_k', kind='pct')}**.",
                 f"- PR-AUC {g('test', 'pr_auc_seen_families')} on seen disguise types, {g('test', 'pr_auc_all')} overall (peer z-score baseline {g('test', 'peer_z_baseline_pr_auc')}).",
                 f"- Honest round-price shops wrongly flagged: {g('test', 'fpr_honest_round_price_shops', kind='pct')}; all honest shops: {g('test', 'fpr_honest_all', kind='pct')}.",
                 f"- Calibration error {g('test', 'ece')}; conformal coverage {g('test', 'conformal', 'overall', kind='pct')}."]
        for fam, v in (_get(a, "test", "recall_by_family", default={}) or {}).items():
            lines.append(f"  - recall, {fam}{' (never seen in training)' if fam.startswith('D') else ''}: {_fmt(v, 'pct')}")
        return lines
    if k == "ai6":
        lk = a.get("linking") or {}
        return [f"- {g('linking', 'n_alerts', kind='int')} alerts → {g('linking', 'n_cases', kind='int')} cases: **{g('linking', 'analyst_items_reduction', kind='pct')} fewer items** to open.",
                f"- Alert pairs paid to the same mule that were linked: {g('linking', 'same_mule_pairs_linked', kind='pct')}; mean case purity {g('linking', 'case_purity_mean', kind='pct')}.",
                f"- Real scam alerts inside the top 5 / 10 / 20 cases: {_fmt(_get(lk, 'real_scam_alerts_in_top_cases', '5'), 'pct')} / "
                f"{_fmt(_get(lk, 'real_scam_alerts_in_top_cases', '10'), 'pct')} / {_fmt(_get(lk, 'real_scam_alerts_in_top_cases', '20'), 'pct')}.",
                f"- Cash-outs found for detected cases: {g('linking', 'cashouts_found_for_detected_cases', kind='pct')}."]
    if k == "ai7":
        return [f"- Language model: {g('llm')}; retrieval: {g('retrieval')}; {g('n_items', kind='int')} briefs and {g('n_injection_tests', kind='int')} prompt-injection tests.",
                f"- Validator pass rate of Gemini output: {g('validator_pass_rate_llm', kind='pct')}; template fallback rate: {g('fallback_rate', kind='pct')}.",
                f"- Shown text valid: {g('shown_text_valid_rate', kind='pct')}; injection attacks that reached a user: **{g('injection_shown_success_rate', kind='pct')}** "
                f"(raw model output before the validator: {g('injection_raw_success_rate', kind='pct')})."]
    return []


def model_cards(m: dict, versions: dict | None = None) -> dict[str, str]:
    versions = versions or {}
    cards = {}
    index = ["# Model cards", "", "One card per AI, generated by NB99 from the result files in `reports/`. Synthetic data only.", "",
             "| AI | Card | Measured by |", "|---|---|---|"]
    for k, name in AIS.items():
        f, a = CARD_FACTS[k], m.get(k)
        fname = f"{name.split()[0]}.md"
        commit = (versions.get(k) or {}).get("uvera_commit")
        lines = [f"# Model card — {name}", "",
                 f"*Notebook `{NOTEBOOK[k]}` · code commit `{commit[:10] if commit else '—'}` · results `reports/metrics_{k}.json` · synthetic data only.*", "",
                 "| | |", "|---|---|",
                 f"| Task | {f['task']} |", f"| Inputs | {f['inputs']} |", f"| Model | {f['model']} |", f"| Baseline | {f['baseline']} |",
                 f"| Uncertainty | {f['uncertainty']} |", f"| Explanation | {f['explanation']} |", f"| Intended use | {f['use']} |",
                 f"| Out of scope | {f['not_for']} |", "", "## Measured results (test data the model never saw)", ""]
        lines += _metrics_lines(k, a) if a else [f"- Not measured yet: run `{NOTEBOOK[k]}`."]
        lines += ["", "## Limitations", "", f["limits"], ""]
        cards[fname] = "\n".join(lines)
        index.append(f"| {name} | [{fname}]({fname}) | {NOTEBOOK[k]}{' ✔' if a else ' (not run yet)'} |")
    cards["README.md"] = "\n".join(index) + "\n"
    return cards
