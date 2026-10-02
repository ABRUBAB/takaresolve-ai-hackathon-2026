"""AI-7 Grounded Brief: Gemini rewrites structured evidence into Bangla + English, checked by a validator.

Measures: validator pass rate, fallback rate, prompt-injection success (raw model output vs what users would see).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from uvera_ml.brief import grounding as G
from uvera_ml.common import load_config, write_json
from uvera_ml.policy import decide

FAMILY_TAG = {"recipient_age_days": "mule_signals", "recipient_sender_days_7d": "mule_signals",
              "recipient_in_count_7d": "mule_signals", "device_change_72h": "fake_customer_care", "pin_reset_72h": "fake_customer_care"}


def _decision(row, thr, rules):
    return decide(float(row["raw_score"]), "unsure" if row["unsure"] else row["conformal_state"], bool(row["ood"]), thr,
                  float(row["amount"]), rules)


def run_ai7(out: str | Path, scored: pd.DataFrame, thresholds: dict, cases: list[dict] | None, gemini=None,
            n_eval: int = 200, n_injection: int = 30, embedder=None, seed: int = 42) -> dict:
    out = Path(out)
    art, rep = out / "artifacts" / "ai7", out / "reports"
    art.mkdir(parents=True, exist_ok=True)
    rep.mkdir(parents=True, exist_ok=True)
    rules = load_config("rules/actions")
    retriever = G.CardRetriever(G.load_cards(), embedder)

    # stratified sample of test transfers across risk states
    scored = scored.copy()
    scored["bucket"] = np.where(scored["unsure"], "unsure", scored["risk_level"])
    per = max(1, n_eval // 4)
    sample = pd.concat([g.sample(min(per, len(g)), random_state=seed) for _, g in scored.groupby("bucket")])

    def build(row, note=None):
        d = _decision(row, thresholds, rules)
        reasons = json.loads(row["reasons"]) if isinstance(row["reasons"], str) else []
        tags = [FAMILY_TAG.get(r["feature"], "") for r in reasons]  # model evidence only, never the true label
        query = " ".join(r["text_en"] for r in reasons) or "transfer risk"
        return G.transfer_evidence(row, d, retriever.retrieve(query, tags), note)

    items = [("transfer", build(r)) for _, r in sample.iterrows()]
    if cases:
        for c in cases[:20]:
            tags = ["qr_misuse"] if c["merchants"] else ["mule_signals"]
            items.append(("case", G.case_evidence(c, retriever.retrieve(" ".join(e["text"] for e in c["evidence"]), tags))))
    high = scored[scored["risk_level"] == "high"]
    inj_rows = high.sample(min(n_injection, len(high)), random_state=seed, replace=len(high) < n_injection) if len(high) else high
    injections = [("injection", build(r, G.INJECTIONS[i % len(G.INJECTIONS)])) for i, (_, r) in enumerate(inj_rows.iterrows())]

    results, cache = [], {}
    for kind, ev in items + injections:
        t0 = time.time()
        raw, problems, source = None, [], "template"
        if gemini is not None:
            try:
                raw = gemini.json(G.prompt_for(ev), G.Brief, temperature=0.3, system=G.SYSTEM)
                ok, problems = G.validate(raw, ev)
                source = "gemini" if ok else "template_after_validator"
            except Exception as e:  # noqa: BLE001
                problems, source = [f"gemini error: {str(e)[:80]}"], "template_after_error"
        shown = {**raw, "source": "gemini"} if source == "gemini" else G.template_brief(ev)
        shown_ok, shown_problems = G.validate(shown, ev)
        raw_unsafe = bool(raw) and any("contradicts high risk" in p or "banned" in p or "link" in p for p in problems)
        key = __import__("hashlib").sha256(json.dumps(ev, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
        cache[key] = {"evidence": ev, "brief": shown}
        results.append({"kind": kind, "source": source, "raw_valid": not problems if raw else None, "problems": problems,
                        "shown_valid": shown_ok, "shown_problems": shown_problems, "raw_unsafe": raw_unsafe,
                        "latency_s": round(time.time() - t0, 2), "key": key})
    res = pd.DataFrame(results)
    inj = res[res["kind"] == "injection"]
    normal = res[res["kind"] != "injection"]
    summary = {
        "ai": "AI-7 Grounded Brief", "llm": gemini.stats() if gemini is not None else "unavailable (template only)",
        "retrieval": retriever.mode, "n_items": int(len(normal)), "n_injection_tests": int(len(inj)),
        "validator_pass_rate_llm": float(normal["raw_valid"].mean()) if gemini is not None and normal["raw_valid"].notna().any() else None,
        "fallback_rate": float((normal["source"] != "gemini").mean()),
        "shown_text_valid_rate": float(res["shown_valid"].mean()),
        "injection_raw_success_rate": float(inj["raw_unsafe"].mean()) if gemini is not None and len(inj) else None,
        "injection_shown_success_rate": float((~inj["shown_valid"]).mean()) if len(inj) else None,
        "top_validator_problems": res["problems"].explode().dropna().value_counts().head(8).to_dict(),
        "median_latency_s": float(res["latency_s"].median()),
    }
    (art / "briefs_cache.json").write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    res.to_csv(rep / "ai7_results.csv", index=False)
    write_json(rep / "metrics_ai7.json", summary)
    return summary
