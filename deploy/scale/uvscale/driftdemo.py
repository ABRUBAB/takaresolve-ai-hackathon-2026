"""Drift demonstration on the live stream: normal test-window traffic, then two shifted streams.

Precondition: fresh online store warmed with days 0-99 (see README). Each phase replays a fresh slice of days
(no event is applied twice), waits for the stream to drain, then reads GET /drift. The window holds ~7 days of p2p
transfers so day-of-week does not alias.
"""
from __future__ import annotations

import argparse
import json
import time

import redis

from uvscale.producer import REDIS_URL, Events, group_lag, produce
from uvscale.streambench import call, workers

PHASES = [("normal: days 100-106 as recorded", 100, 107, "none", 0.0),
          ("shifted: days 107-113, p2p amounts x3", 107, 114, "amount_x3", 0.0),
          ("shifted: days 114-119, 30% of p2p to brand-new receivers", 114, 120, "new_receivers", 0.3)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/repo/reports/scalability/drift_demo.json")
    a = ap.parse_args()
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    out = {"what": "PSI per AI-1 feature: reference bins (build_ai1_features, days 70-99: the 30 days before go-live) vs the "
                   "feature-worker's sliding window of the last N p2p transfers on the stream",
           "thresholds": {"warn": 0.1, "alert": 0.2}, "phases": []}
    for ip in workers():  # one reset at the start; the window then slides (about 7 days of transfers)
        call(ip, "/drift/reset", "POST")
    for name, d0, d1, shift, share in PHASES:
        ev = Events(d0, d1)
        if shift != "none":
            ev.shift(shift, share)
        prod = produce(r, ev, 0)
        t0 = time.time()
        while group_lag(r) > 0 and time.time() - t0 < 300:
            time.sleep(0.2)
        time.sleep(2)
        drift = call(workers()[0], "/drift")
        print(f"{name}: status={drift['status']} max_psi={drift['max_psi']:.3f} top={drift['top_drifted'][:3]}", flush=True)
        out["phases"].append({"name": name, "shift": shift, "producer": prod, "drift": drift})
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
