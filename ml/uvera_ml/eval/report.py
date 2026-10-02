"""NB99: gather every AI's measured results into one summary for the Trust Center, README and report.

Rule: a number is shown only if a notebook measured it. Missing results are reported as "not measured yet".
"""
from __future__ import annotations

import json
from pathlib import Path

from uvera_ml.common import write_json
from uvera_ml.eval import plots

AIS = {"ai1": "AI-1 Pause Check", "ai2": "AI-2 Scam Text Sentinel", "ai3": "AI-3 Cash-Flow Guardian",
       "ai4": "AI-4 Agent Liquidity Copilot", "ai5": "AI-5 QR Shield", "ai6": "AI-6 Case Linker", "ai7": "AI-7 Grounded Brief"}
NM = "not measured yet"


def _get(d, *path, default=NM):
    for p in path:
        if not isinstance(d, dict) or p not in d or d[p] is None:
            return default
        d = d[p]
    return d


def headline(m: dict) -> dict:
    a1, a2, a3, a4, a5, a6, a7 = (m.get(k, {}) for k in AIS)
    a2_served = {}
    if a2:
        served = a2.get("served_model_chosen_on_cv")
        a2_served = next((r for r in a2.get("test_heldout_style_B", []) if r["model"] == served), {})
    return {
        "ai1": {"pr_auc": _get(a1, "test_unseen_customers", "model", "pr_auc"),
                "pr_auc_rule_baseline": _get(a1, "test_unseen_customers", "rule_baseline", "pr_auc"),
                "recall_at_5pct_alert_rate": _get(a1, "test_unseen_customers", "model", "at_5pct_alert_rate", "recall"),
                "recall_at_5pct_rule_baseline": _get(a1, "test_unseen_customers", "rule_baseline", "at_5pct_alert_rate", "recall"),
                "false_alerts_per_1000": _get(a1, "test_unseen_customers", "model", "false_alerts_per_1000_at_red"),
                "ece": _get(a1, "test_unseen_customers", "model", "ece_calibrated"),
                "conformal_coverage": _get(a1, "test_unseen_customers", "conformal"),
                "unsure_rate": _get(a1, "test_unseen_customers", "unsure_rate"),
                "error_at_80pct_coverage": _get(a1, "test_unseen_customers", "selective", "error_at_80pct_coverage"),
                "error_at_100pct_coverage": _get(a1, "test_unseen_customers", "selective", "error_at_100pct_coverage"),
                "loss_prevented_bdt": _get(a1, "test_unseen_customers", "loss_prevented_bdt")},
        "ai2": {"served_model": _get(a2, "served_model_chosen_on_cv"), "embedder": _get(a2, "embedder"),
                "heldout_style_verdict_pr_auc": a2_served.get("verdict_pr_auc", NM), "heldout_macro_f1": a2_served.get("macro_f1", NM),
                "external_uci": _get(a2, "external_uci_sms_spam")},
        "ai3": {"winner": _get(a3, "winner_on_validation"), "shortfall": _get(a3, "shortfall_probability_test")},
        "ai4": {"winner": _get(a4, "winner_on_validation"), "stockout": _get(a4, "stockout_probability_test")},
        "ai5": {"pr_auc_seen": _get(a5, "test", "pr_auc_seen_families"), "precision_at_k": _get(a5, "test", "weekly_precision_at_k"),
                "unseen_family_D": _get(a5, "test", "unseen_family_D"),
                "fpr_honest_round_price": _get(a5, "test", "fpr_honest_round_price_shops"),
                "fpr_honest_all": _get(a5, "test", "fpr_honest_all")},
        "ai6": _get(a6, "linking"),
        "ai7": {k: _get(a7, k) for k in ("validator_pass_rate_llm", "fallback_rate", "shown_text_valid_rate",
                                          "injection_raw_success_rate", "injection_shown_success_rate")},
    }


def fairness_summary(m: dict) -> list[dict]:
    rows = []
    for r in m.get("ai1", {}).get("fairness_slices_test_window", []):
        rows.append({"ai": "AI-1", **r})
    a5 = m.get("ai5", {}).get("test", {})
    for size, v in (a5.get("fpr_by_size") or {}).items():
        rows.append({"ai": "AI-5", "slice": "merchant_size", "group": size, "fpr": v})
    for lang, v in (m.get("ai2", {}).get("test_by_language_served") or {}).items():
        rows.append({"ai": "AI-2", "slice": "language", "group": lang, **v})
    return rows


def build_summary(reports_dir: str | Path, out: str | Path) -> dict:
    reports_dir, out = Path(reports_dir), Path(out)
    m = {}
    for k in AIS:
        p = reports_dir / f"metrics_{k}.json"
        if p.exists():
            m[k] = json.loads(p.read_text(encoding="utf-8"))
    head = headline(m)
    summary = {"available": {AIS[k]: k in m for k in AIS}, "headline": head, "fairness": fairness_summary(m),
               "ablation_ai1": m.get("ai1", {}).get("ablation_validation", NM),
               "cv_ai1": m.get("ai1", {}).get("cv_summary", NM), "cv_ai5": m.get("ai5", {}).get("cv_summary_train", NM),
               "backtest_ai3": m.get("ai3", {}).get("backtest", NM), "backtest_ai4": m.get("ai4", {}).get("backtest", NM),
               "world": m.get("ai1", {}).get("world", NM),
               "note": "All results are on synthetic data: they show that the pipeline works, not real-world accuracy."}
    (out / "reports" / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "reports" / "metrics.json", summary)
    a1 = head["ai1"]
    if isinstance(a1["recall_at_5pct_alert_rate"], float):
        plots.bars(["UVERA AI-1", "rule baseline"], [a1["recall_at_5pct_alert_rate"], a1["recall_at_5pct_rule_baseline"]],
                   out / "reports" / "figures" / "summary_recall_vs_rule.png", "Scams caught at the same 5% alert rate", "recall")
    (out / "reports" / "summary.md").write_text(to_markdown(summary), encoding="utf-8")
    return summary


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    return "—" if v == NM else str(v)


def to_markdown(s: dict) -> str:
    h = s["headline"]
    lines = ["# UVERA — measured results (synthetic data)", "", s["note"], "", "| AI | Metric | Value |", "|---|---|---|"]
    rows = [("AI-1", "PR-AUC (unseen customers)", h["ai1"]["pr_auc"]), ("AI-1", "PR-AUC rule baseline", h["ai1"]["pr_auc_rule_baseline"]),
            ("AI-1", "Recall at 5% alert rate", h["ai1"]["recall_at_5pct_alert_rate"]),
            ("AI-1", "Recall at 5% (rule baseline)", h["ai1"]["recall_at_5pct_rule_baseline"]),
            ("AI-1", "False alerts per 1,000 normal transfers", h["ai1"]["false_alerts_per_1000"]),
            ("AI-1", "Calibration error (ECE)", h["ai1"]["ece"]), ("AI-1", "'Not sure' rate", h["ai1"]["unsure_rate"]),
            ("AI-2", "Verdict PR-AUC (held-out writing style)", h["ai2"]["heldout_style_verdict_pr_auc"]),
            ("AI-3", "Best forecaster (validation)", h["ai3"]["winner"]), ("AI-4", "Best forecaster (validation)", h["ai4"]["winner"]),
            ("AI-5", "PR-AUC (seen families)", h["ai5"]["pr_auc_seen"]), ("AI-5", "Precision@k per week", h["ai5"]["precision_at_k"]),
            ("AI-5", "False-positive rate, honest round-price shops", h["ai5"]["fpr_honest_round_price"]),
            ("AI-6", "Analyst items reduction", _get(h, "ai6", "analyst_items_reduction")),
            ("AI-7", "Injection success shown to users", h["ai7"]["injection_shown_success_rate"])]
    lines += [f"| {a} | {k} | {_fmt(v)} |" for a, k, v in rows]
    return "\n".join(lines) + "\n"
