"""Stream ingestion benchmark: producer at increasing rates -> feature-worker throughput and end-to-end lag.

Runs inside the compose network:  python -m uvscale.streambench --rates 1000 2000 5000 10000 20000 0 --seconds 30
Lag = time from XADD by the producer to the event being applied in the online feature store (feature freshness).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import time
import urllib.request

import redis

from uvscale.producer import GROUP, REDIS_URL, STREAM, Events, group_lag, produce


def workers() -> list[str]:
    return sorted({ai[4][0] for ai in socket.getaddrinfo("feature-worker", 9100, proto=socket.IPPROTO_TCP)})


def call(ip: str, path: str, method: str = "GET") -> dict:
    req = urllib.request.Request(f"http://{ip}:9100{path}", method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rates", type=float, nargs="+", default=[1000, 2000, 5000, 10000, 20000, 0])
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--from-day", type=int, default=100)
    ap.add_argument("--to-day", type=int, default=120)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="/repo/reports/scalability/stream_ingest.json")
    ap.add_argument("--finish", action="store_true", help="after the steps, replay the rest of the range at max rate (warm-up)")
    a = ap.parse_args()
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    ev = Events(a.from_day, a.to_day)
    print(f"{len(ev)} events loaded; workers: {workers()}", flush=True)
    results, pos = [], 0
    for rate in a.rates:
        ips = workers()
        for ip in ips:
            call(ip, "/stats/reset", "POST")
        n_need = int((rate if rate > 0 else 80_000) * a.seconds)
        if pos + n_need > len(ev):
            pos = 0
        prod = produce(r, ev, rate, max_seconds=a.seconds, start=pos, stop=pos + n_need, max_lag=150_000)
        pos = prod["next"]
        t0 = time.time()
        while group_lag(r) > 0 and time.time() - t0 < 120:
            time.sleep(0.2)
        time.sleep(1.5)
        stats = [call(ip, "/stats") for ip in ips]
        total = sum(s["events"] for s in stats)
        span = max((s["active_seconds"] for s in stats), default=0) or 1
        row = {"label": a.label, "target_rate": rate if rate > 0 else "max", "producer": prod, "n_workers": len(ips),
               "events_processed": total, "worker_events_per_s": round(total / span, 1),
               "lag_ms_p50_max_over_workers": max(s["lag_ms"]["p50"] for s in stats),
               "lag_ms_p95_max_over_workers": max(s["lag_ms"]["p95"] for s in stats),
               "lag_ms_p99_max_over_workers": max(s["lag_ms"]["p99"] for s in stats),
               "lag_ms_max": max(s["lag_ms"]["max"] for s in stats), "drain_s": round(time.time() - t0, 2), "workers": stats}
        print(json.dumps({k: v for k, v in row.items() if k != "workers"}), flush=True)
        results.append(row)
    if a.finish and pos < len(ev):
        ips = workers()
        for ip in ips:
            call(ip, "/stats/reset", "POST")
        prod = produce(r, ev, 0, start=pos, max_lag=150_000)
        t0 = time.time()
        while group_lag(r) > 0 and time.time() - t0 < 600:
            time.sleep(0.2)
        time.sleep(1.5)
        stats = [call(ip, "/stats") for ip in ips]
        total = sum(s["events"] for s in stats)
        span = max((s["active_seconds"] for s in stats), default=0) or 1
        row = {"label": a.label, "target_rate": "max", "producer": prod, "n_workers": len(ips), "events_processed": total,
               "worker_events_per_s": round(total / span, 1),
               "lag_ms_p50_max_over_workers": max(s["lag_ms"]["p50"] for s in stats),
               "lag_ms_p95_max_over_workers": max(s["lag_ms"]["p95"] for s in stats),
               "lag_ms_p99_max_over_workers": max(s["lag_ms"]["p99"] for s in stats),
               "lag_ms_max": max(s["lag_ms"]["max"] for s in stats), "drain_s": round(time.time() - t0, 2), "workers": stats,
               "note": "rest of the range at max producer speed; backpressure holds the stream at <=150k unread events"}
        print(json.dumps({k: v for k, v in row.items() if k != "workers"}), flush=True)
        results.append(row)
    prev = json.load(open(a.out)) if os.path.exists(a.out) else []
    json.dump(prev + results, open(a.out, "w"), indent=1)
    _ = (GROUP, STREAM)


if __name__ == "__main__":
    main()
