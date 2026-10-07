"""Pull the on-site user study results from the live API, drop practice runs (facilitator code TEST), and write
  reports/phase2/user_study.json   (used by business_case.py: stated stop rate, measured analyst triage time)
  frontend/public/data/phase2/study.json   (the /trust/phase2 page)
Usage:  STUDY_PIN=<pin> python scripts/phase2/study_results.py [api_base]
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.api.v1.study import aggregate  # noqa: E402  (the same aggregation the results page uses)

API = (sys.argv[1] if len(sys.argv) > 1 else "https://desktop-ir0t2s7.tail5106c5.ts.net").rstrip("/")


def main():
    req = urllib.request.Request(API + "/v1/study/results", headers={"X-Study-Pin": os.environ["STUDY_PIN"]})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    rows = [r for r in data["rows"] if str(r.get("facilitator") or "").upper() != "TEST"]
    s = aggregate(rows)
    t1, t2, t3 = s.get("task1", {}), s.get("task2", {}), s.get("task3", {})
    A, B = t3.get("A", {}), t3.get("B", {})
    out = {"n": s["n"], "stated_stop_rate": (t1.get("stated_stop") or {}).get("rate"), "stated_stop_ci95": (t1.get("stated_stop") or {}).get("ci95"),
           "comprehension": (t1.get("comprehension") or {}).get("rate"), "not_sure_understood": (t2.get("understood") or {}).get("rate"),
           "clarity": (t1.get("clarity") or {}).get("mean"), "trust": (t1.get("trust") or {}).get("mean"), "annoyance": (t1.get("annoyance") or {}).get("mean"),
           "triage": {"A_alert_list": A, "B_linked_cases": B},
           "analyst_triage": ({"minutes_per_alert_item_measured": A["median_time_s"] / 60 / 12, "minutes_per_linked_case_measured": B["median_time_s"] / 60 / 4}
                              if A.get("median_time_s") and B.get("median_time_s") else {}),
           "summary": s, "caveat": s.get("caveat")}
    (ROOT / "reports" / "phase2" / "user_study.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    def r(x):
        return None if x is None else round(float(x), 4)
    web = {"status": "measured" if s["n"] else "pending", "title": "On-site user study (anonymous, participants' own phones)",
           "updated_at": data.get("generated_at"), "source": "GET /v1/study/results -> scripts/phase2/study_results.py",
           "summary": f"{s['n']} volunteers at the venue saw the real Pause and 'not sure' screens (Bangla or English, randomised) and did an analyst triage task (alert list A vs linked cases B).",
           "headline": [{"label": "Understood the Pause screen", "value": r(out["comprehension"]), "format": "pct", "sub": f"n = {s['n']}"},
                        {"label": "Would NOT send after the Pause (stated)", "value": r(out["stated_stop_rate"]), "format": "pct",
                         "sub": f"95% CI {out['stated_stop_ci95'][0]:.0%}-{out['stated_stop_ci95'][1]:.0%}" if out.get("stated_stop_ci95") else ""},
                        {"label": "Understood 'not sure' = a person checks", "value": r(out["not_sure_understood"]), "format": "pct", "sub": ""}],
           "sections": [{"id": "triage", "title": "Analyst triage: plain alert list (A) vs UVERA linked cases (B)",
                         "lead": "Same 12 alerts, 3 hidden rings. Between-subject; each participant saw one version.",
                         "chart": {"kind": "bars", "unit": "pct", "x": ["found the 3 rings", "picked the right wallet (W-77)", "both correct"],
                                   "series": [{"name": f"A: alert list (n = {A.get('n', 0)})", "values": [r((A.get(k) or {}).get('rate')) for k in ('rings_correct', 'wallet_correct', 'both_correct')]},
                                              {"name": f"B: linked cases (n = {B.get('n', 0)})", "values": [r((B.get(k) or {}).get('rate')) for k in ('rings_correct', 'wallet_correct', 'both_correct')]}]},
                         "takeaway": f"Median time: A {A.get('median_time_s')} s vs B {B.get('median_time_s')} s."},
                        {"id": "ratings", "title": "How the Pause felt (1-5)", "lead": "Clarity and trust: higher is better. Annoyance if the transfer were safe: lower is better.",
                         "chart": {"kind": "bars", "unit": "num1", "x": ["clarity", "trust", "annoyance if safe"],
                                   "series": [{"name": "mean rating", "values": [r(out["clarity"]), r(out["trust"]), r(out["annoyance"])]}]},
                         "takeaway": "Stated intentions in a short session, not observed behaviour."}],
           "caveats": [s.get("caveat") or "Small n."]}
    (ROOT / "frontend" / "public" / "data" / "phase2" / "study.json").write_text(json.dumps(web, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n", "stated_stop_rate", "comprehension", "not_sure_understood", "analyst_triage")}, indent=1))


if __name__ == "__main__":
    main()
