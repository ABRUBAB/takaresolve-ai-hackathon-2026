"""Shadow-mode replay report, computed from Postgres.

1. Load confirmed outcomes for the replayed window into fraud_labels (in production: fraud reports / chargebacks;
   here: the synthetic ground truth, which the stream itself never carried).
2. Join with decisions (source='shadow') and report volume, catches, false pauses and end-to-end decision latency.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import asyncpg
import numpy as np

PG_DSN = os.environ.get("PG_DSN", "postgresql://uvera:uvera@postgres:5432/uvera")
DATA = os.environ.get("SCALE_DATA", "/repo/_outputs/scale")

SUMMARY_SQL = """
WITH d AS (
  SELECT DISTINCT ON (event_id) * FROM decisions WHERE source = 'shadow' ORDER BY event_id, decided_at
), j AS (
  SELECT d.*, l.label_scam, l.mule_flow, l.unseen_customer FROM d LEFT JOIN fraud_labels l USING (event_id)
)
SELECT {where_label} AS slice,
  count(*) AS transfers_scored,
  count(*) FILTER (WHERE label_scam IS NOT NULL) AS with_outcome,
  coalesce(sum(label_scam), 0) AS scams_in_window,
  count(*) FILTER (WHERE risk_level = 'high') AS paused_red,
  count(*) FILTER (WHERE risk_level = 'high' AND label_scam = 1) AS scams_paused_red,
  count(*) FILTER (WHERE risk_level = 'high' AND label_scam = 0) AS false_pauses_red,
  count(*) FILTER (WHERE risk_level <> 'low' OR unsure) AS warned_any,
  count(*) FILTER (WHERE (risk_level <> 'low' OR unsure) AND label_scam = 1) AS scams_warned_any,
  count(*) FILTER (WHERE (risk_level <> 'low' OR unsure) AND label_scam = 0) AS false_warnings_any,
  count(*) FILTER (WHERE unsure) AS unsure,
  sum(amount) FILTER (WHERE risk_level = 'high' AND label_scam = 1) AS scam_amount_paused_bdt,
  sum(amount) FILTER (WHERE label_scam = 1) AS scam_amount_total_bdt
FROM j {where}
"""

LAT_SQL = """
WITH d AS (SELECT DISTINCT ON (event_id) * FROM decisions WHERE source = 'shadow' ORDER BY event_id, decided_at)
SELECT
  percentile_cont(ARRAY[0.5, 0.95, 0.99]) WITHIN GROUP (ORDER BY extract(epoch FROM decided_at - produced_at) * 1000) AS e2e,
  max(extract(epoch FROM decided_at - produced_at) * 1000) AS e2e_max,
  percentile_cont(ARRAY[0.5, 0.95, 0.99]) WITHIN GROUP (ORDER BY latency_ms) AS scorer,
  max(latency_ms) AS scorer_max,
  extract(epoch FROM max(decided_at) - min(decided_at)) AS span_s,
  count(DISTINCT replica) AS replicas,
  count(DISTINCT model_version) AS model_versions,
  min(model_version) AS model_version
FROM d
"""


async def main(out: str, from_day: int, to_day: int, notes: dict) -> None:
    z = np.load(f"{DATA}/window_labels.npz")
    recs = list(zip(z["event_id"].tolist(), z["label"].tolist(), [None] * len(z["label"]), z["mule"].tolist(), z["unseen"].tolist()))
    con = await asyncpg.connect(PG_DSN)
    await con.execute("TRUNCATE fraud_labels")
    await con.copy_records_to_table("fraud_labels", records=recs,
                                    columns=["event_id", "label_scam", "scam_family", "mule_flow", "unseen_customer"])
    rows = {}
    for name, where in [("all_p2p", ""), ("excluding_mule_flows", "WHERE mule_flow = 0"),
                        ("unseen_customers_only", "WHERE unseen_customer AND mule_flow = 0")]:
        r = dict(await con.fetchrow(SUMMARY_SQL.format(where=where, where_label=f"'{name}'")))
        r = {k: (float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, int) else v) for k, v in r.items()}
        n, s = r["transfers_scored"], r["scams_in_window"] or 0
        r["recall_red"] = round(r["scams_paused_red"] / s, 4) if s else None
        r["precision_red"] = round(r["scams_paused_red"] / r["paused_red"], 4) if r["paused_red"] else None
        r["false_pauses_per_1000_transfers"] = round(1000 * r["false_pauses_red"] / n, 2) if n else None
        r["recall_any_warning"] = round(r["scams_warned_any"] / s, 4) if s else None
        r["pause_rate"] = round(r["paused_red"] / n, 4) if n else None
        rows[name] = r
    lat = dict(await con.fetchrow(LAT_SQL))
    await con.close()
    q = lambda arr: {"p50": round(arr[0], 2), "p95": round(arr[1], 2), "p99": round(arr[2], 2)} if arr else None  # noqa: E731
    report = {"window": f"days {from_day}-{to_day - 1} (test window), every customer-to-customer p2p transfer",
              "pipeline": "producer (events.parquet, labels stripped) -> Redis Stream -> feature-worker (point-in-time "
                          "features, Lua) -> nginx -> scorer replicas -> Postgres decisions; outcomes joined afterwards",
              "definitions": {"paused_red": "risk_level = high (red: 'wait 10 minutes' pause)",
                              "warned_any": "risk_level medium/high or unsure (any on-screen warning)",
                              "false_pause": "paused_red on a transfer that was not a scam"},
              "slices": rows,
              "latency_ms": {"end_to_end_produce_to_decision": {**q(lat["e2e"]), "max": round(lat["e2e_max"], 2)},
                             "scorer_internal": {**q(lat["scorer"]), "max": round(lat["scorer_max"], 2)}},
              "replay_span_s": round(float(lat["span_s"]), 1), "scorer_replicas_used": lat["replicas"],
              "model_versions_seen": lat["model_versions"], "model_version": lat["model_version"], **notes}
    report["decisions_per_s"] = round(rows["all_p2p"]["transfers_scored"] / report["replay_span_s"], 1) if report["replay_span_s"] else None
    json.dump(report, open(out, "w"), indent=1, default=str)
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/repo/reports/scalability/shadow_replay.json")
    ap.add_argument("--from-day", type=int, default=100)
    ap.add_argument("--to-day", type=int, default=120)
    ap.add_argument("--notes", default="{}")
    a = ap.parse_args()
    asyncio.run(main(a.out, a.from_day, a.to_day, json.loads(a.notes)))
