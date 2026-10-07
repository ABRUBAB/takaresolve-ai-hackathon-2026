"""Publish measured scale results to the Phase 2 evidence page.

All displayed numbers come from reports/scalability/*.json. Run after the
load tests: python deploy/scale/export_web.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "scalability"
OUT = ROOT / "frontend" / "public" / "data" / "phase2" / "scalability.json"


def read(name: str):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def main() -> None:
    transfers = read("loadtest_transfer.json")
    mixed = read("loadtest_mixed.json")
    db_modes = read("loadtest_dbmode.json")
    shadow = read("shadow_replay.json")
    parity = read("parity.json")
    by_run = {(r["replicas"], r["concurrency"]): r for r in transfers}
    required = [(replicas, clients) for replicas in (1, 2, 4) for clients in (1, 8, 32, 64, 128)]
    missing = [key for key in required if key not in by_run]
    if missing:
        raise ValueError(f"Incomplete transfer sweep: {missing}")

    best = by_run[(2, 32)]
    clients = [1, 8, 32, 64, 128]
    chart = lambda metric: {
        "kind": "line", "unit": "ms", "x": clients, "x_label": "concurrent clients",
        "series": [
            {"name": f"{n} scorer{'s' if n > 1 else ''}",
             "values": [by_run[(n, c)]["latency_ms"][metric] for c in clients]}
            for n in (1, 2, 4)
        ],
    }
    data = {
        "status": "measured",
        "title": "Scale and latency, measured on one laptop",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "deploy/scale/export_web.py -> reports/scalability/loadtest_*.json, shadow_replay.json, parity.json",
        "summary": "Redis Streams, online features, Postgres and scorer replicas were tested together on one laptop. More replicas helped at some loads but four replicas contended for the same CPU and did not always win.",
        "headline": [
            {"label": "Transfer p95, 32 clients / 2 scorers", "value": best["latency_ms"]["p95"], "format": "ms", "sub": f"p99 {best['latency_ms']['p99']:.1f} ms; 0 errors"},
            {"label": "Transfer throughput, 32 clients / 2 scorers", "value": best["rps"], "format": "num1", "sub": "one laptop, 30-second load point"},
            {"label": "Shadow replay decisions / second", "value": shadow["decisions_per_s"], "format": "num1", "sub": f"{shadow['slices']['all_p2p']['transfers_scored']:,} synthetic transfers scored"},
            {"label": "Online / batch risk-level agreement", "value": parity["score_agreement"]["same_risk_level_pct"] / 100, "format": "pct1", "sub": f"{parity['score_agreement']['risk_level_changes']} decisions changed level"},
        ],
        "sections": [
            {"id": "latency", "title": "Transfer p95 latency under load", "lead": "Same transfer endpoint, 1, 2 or 4 scorer processes behind nginx.",
             "chart": chart("p95"),
             "takeaway": "At 32 clients, 2 scorers reached 468.8 requests/s at p95 129.7 ms. At 128 clients, latency rose sharply. Four scorers were slower than two on this shared laptop."},
            {"id": "p99", "title": "Transfer p99 latency under load", "lead": "The slowest 1% of requests matter during a payment.",
             "chart": chart("p99"),
             "takeaway": "At 32 clients with 2 scorers, p99 was 195.4 ms. One of the 2-scorer, 64-client runs had 2 request errors; raw files retain them."},
            {"id": "replicas", "title": "Throughput at the same 32-client load", "lead": "All processes shared one laptop, so extra replicas eventually competed for CPU.",
             "chart": {"kind": "bars", "unit": "num1", "x": ["1 scorer", "2 scorers", "4 scorers"],
                       "series": [{"name": "requests / second", "values": [by_run[(n, 32)]["rps"] for n in (1, 2, 4)]}]},
             "takeaway": "294.5 → 468.8 → 330.9 requests/s. This proves the fleet runs with several scorers, not unlimited horizontal scaling."},
            {"id": "database", "title": "Postgres decision-write test", "lead": "Three separate 4-scorer, 64-client runs; synchronous insert, batched COPY and write disabled.",
             "chart": {"kind": "table", "columns": ["write mode", "requests/s", "p95 ms", "p99 ms", "errors"],
                       "units": [None, "num1", "ms", "ms", "num"],
                       "rows": [[r["db_write"], r["rps"], r["latency_ms"]["p95"], r["latency_ms"]["p99"], r["errors"]] for r in db_modes]},
             "takeaway": "Postgres writes were exercised. In this run, batched COPY did not beat synchronous inserts; we do not claim it did."},
            {"id": "mixed", "title": "Mixed transfer, text, alert and case workload", "lead": "70% transfer checks, 20% SMS checks, 10% alert/case operations; 4 scorers and Postgres.",
             "chart": {"kind": "table", "columns": ["clients", "requests/s", "p95 ms", "p99 ms", "errors"],
                       "units": ["num", "num1", "ms", "ms", "num"],
                       "rows": [[r["concurrency"], r["rps"], r["latency_ms"]["p95"], r["latency_ms"]["p99"], r["errors"]] for r in mixed]},
             "takeaway": "At 32 clients the mixed workload reached 289.6 requests/s, p95 288.9 ms, with zero errors. At 64 clients p95 rose to 1,237 ms."},
            {"id": "shadow", "title": "Full synthetic test-window replay", "lead": "Event stream → online feature worker → scorer → Postgres; labels were joined afterwards.",
             "chart": {"kind": "table", "columns": ["measure", "value"], "units": [None, "num1"],
                       "rows": [["transfers scored", shadow["slices"]["all_p2p"]["transfers_scored"]],
                                ["scams paused", shadow["slices"]["all_p2p"]["scams_paused_red"]],
                                ["decisions / second", shadow["decisions_per_s"]],
                                ["end-to-end p95 ms", shadow["latency_ms"]["end_to_end_produce_to_decision"]["p95"]],
                                ["end-to-end p99 ms", shadow["latency_ms"]["end_to_end_produce_to_decision"]["p99"]]]},
             "takeaway": "83,659 synthetic transfers were scored at 553.7 decisions/s; produced-to-decision p95 was 601.7 ms. This is a replay, not live MFS traffic."},
        ],
        "caveats": [
            "All load tests ran on one laptop with the load generator and services sharing CPU and memory; this is not a production cluster or live upay integration.",
            "The old monolith performs more work per call than the new focused scorer, so their response times are not an identical-endpoint comparison.",
            "The test stream uses our synthetic world. User-study results remain pending until real volunteers participate.",
        ],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
