"""Feature worker: consumes the transfer event stream (Redis Streams consumer group), keeps the online feature store
up to date, snapshots point-in-time features of p2p transfers, feeds the drift monitor, and (shadow mode) sends
those transfers to the scorer fleet so every decision lands in Postgres.

HTTP on :9100  GET /metrics  GET /drift  POST /drift/reset  GET /stats  POST /stats/reset
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import random
import socket
import threading
import time
from array import array
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import redis.asyncio as aioredis
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from redis.exceptions import ResponseError

from uvscale.drift import DriftMonitor
from uvscale.online_features import APPLY_LUA, DAY, FEATURES, finalize

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
STREAM = os.environ.get("STREAM", "uvera:events")
GROUP = os.environ.get("GROUP", "features")
CONSUMER = socket.gethostname()
BATCH = int(os.environ.get("BATCH", "500"))
DRIFT_SAMPLE = float(os.environ.get("DRIFT_SAMPLE", "1.0"))  # share of p2p transfers snapshotted for drift
DRIFT_WINDOW = int(os.environ.get("DRIFT_WINDOW", "20000"))
REF_BINS = os.environ.get("REF_BINS", "/srv/reference_bins.json")
SHADOW_URL = os.environ.get("SHADOW_URL", "")  # e.g. http://nginx:8080/score/batch
SHADOW_CONC = int(os.environ.get("SHADOW_CONC", "8"))
SHADOW_CHUNK = int(os.environ.get("SHADOW_CHUNK", "32"))
PARITY_OUT = os.environ.get("PARITY_OUT", "")  # parquet path for point-in-time features of x=1 events

EVENTS = Counter("uvera_worker_events_total", "Events applied to the online feature store", ["etype"])
SNAPSHOTS = Counter("uvera_worker_feature_snapshots_total", "Point-in-time feature vectors computed")
LAG = Histogram("uvera_worker_lag_seconds", "Event produced -> applied to the feature store",
                buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60, 120))
BATCH_LAT = Histogram("uvera_worker_batch_seconds", "Time to apply one batch", buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5))
SHADOW = Counter("uvera_shadow_scored_total", "Shadow-mode transfers sent to the scorer fleet", ["outcome"])
PSI = Gauge("uvera_feature_psi", "Population stability index vs training reference", ["feature"])
DRIFT_STATUS = Gauge("uvera_drift_status", "0 ok, 1 warn (PSI>=0.1), 2 alert (PSI>=0.2)")
DRIFT_MAX = Gauge("uvera_drift_max_psi", "Largest per-feature PSI in the live window")


class Stats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.n, self.featured, self.shadow_ok, self.shadow_err = 0, 0, 0, 0
        self.t_first, self.t_last = None, None
        self.lags = array("d")
        self.batch_ms = array("d")

    def snapshot(self) -> dict:
        lags = np.frombuffer(self.lags, dtype=float) if len(self.lags) else np.array([0.0])
        bms = np.frombuffer(self.batch_ms, dtype=float) if len(self.batch_ms) else np.array([0.0])
        span = (self.t_last - self.t_first) if self.t_first and self.t_last else 0.0
        pct = lambda a, q: round(float(np.percentile(a, q)), 2)  # noqa: E731
        return {"consumer": CONSUMER, "events": self.n, "featured": self.featured, "shadow_scored": self.shadow_ok,
                "shadow_errors": self.shadow_err, "active_seconds": round(span, 3),
                "events_per_s": round(self.n / span, 1) if span > 0 else None,
                "lag_ms": {"p50": pct(lags, 50), "p95": pct(lags, 95), "p99": pct(lags, 99), "max": round(float(lags.max()), 2)},
                "batch_ms": {"p50": pct(bms, 50), "p95": pct(bms, 95), "n": len(self.batch_ms)}}


STATS = Stats()
DRIFT = DriftMonitor(REF_BINS, window=DRIFT_WINDOW)
PARITY_ROWS: list = []


def update_drift_gauges() -> dict:
    d = DRIFT.compute()
    for f, v in d["psi"].items():
        if v is not None:
            PSI.labels(f).set(v)
    DRIFT_MAX.set(d["max_psi"])
    DRIFT_STATUS.set({"ok": 0, "warn": 1, "alert": 2}.get(d["status"], 0))
    return d


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/metrics"):
            update_drift_gauges()
            self._send(200, generate_latest(), CONTENT_TYPE_LATEST)
        elif self.path.startswith("/drift"):
            self._send(200, json.dumps(update_drift_gauges()).encode())
        elif self.path.startswith("/stats"):
            self._send(200, json.dumps(STATS.snapshot()).encode())
        elif self.path.startswith("/health"):
            self._send(200, b'{"status":"ok"}')
        else:
            self._send(404, b"{}")

    def do_POST(self):
        if self.path.startswith("/stats/reset"):
            STATS.reset()
            self._send(200, b'{"reset":true}')
        elif self.path.startswith("/drift/reset"):
            DRIFT.reset()
            self._send(200, b'{"reset":true}')
        else:
            self._send(404, b"{}")


def dump_parity() -> None:
    """event_id + 19 point-in-time features of every x=1 transfer, as a float64 .npy (column 0 = event_id)."""
    if not PARITY_OUT or not PARITY_ROWS:
        return
    tmp = PARITY_OUT + ".tmp.npy"
    np.save(tmp, np.asarray(PARITY_ROWS, dtype=float))
    os.replace(tmp, PARITY_OUT)
    print(f"parity: wrote {len(PARITY_ROWS)} online feature rows to {PARITY_OUT}", flush=True)


async def shadow_score(client, sem, items: list[dict]) -> None:
    """One micro-batch -> POST /score/batch (nginx spreads concurrent batches over the scorer replicas)."""
    async with sem:
        for attempt in range(3):
            try:
                r = await client.post(SHADOW_URL, json={"items": items})
                if r.status_code == 200:
                    SHADOW.labels("ok").inc(len(items))
                    STATS.shadow_ok += len(items)
                    return
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(0.05 * (attempt + 1))
        SHADOW.labels("error").inc(len(items))
        STATS.shadow_err += len(items)


async def run() -> None:
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    async def ensure_group():
        try:
            await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        return await r.script_load(APPLY_LUA)

    sha = await ensure_group()
    client, sem = None, None
    if SHADOW_URL:
        import httpx

        client = httpx.AsyncClient(timeout=10, limits=httpx.Limits(max_connections=SHADOW_CONC, max_keepalive_connections=SHADOW_CONC))
        sem = asyncio.Semaphore(SHADOW_CONC)
    print(f"worker {CONSUMER} consuming {STREAM} as {GROUP}, batch={BATCH}, shadow={'on' if SHADOW_URL else 'off'}", flush=True)
    last_gauges = time.time()
    while True:
        try:
            resp = await r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=BATCH, block=1000)
        except ResponseError as e:  # store flushed / stream re-created: rebuild the group and the script cache
            if "NOGROUP" not in str(e):
                raise
            sha = await ensure_group()
            continue
        if not resp or not resp[0][1]:
            continue
        t0 = time.perf_counter()
        msgs = resp[0][1]
        pipe = r.pipeline(transaction=False)
        meta, end_marker = [], False
        for _mid, f in msgs:
            e = f.get("e")
            if e == "__end__":
                end_marker = True
                continue
            s, d, sk, dk, t = f["s"], f["d"], f["sk"], f["dk"], int(f["t"])
            score_it = f.get("x") == "1"
            want = e == "p2p" and sk == "0" and dk == "0" and (score_it or DRIFT_SAMPLE >= 1 or random.random() < DRIFT_SAMPLE)
            pipe.evalsha(sha, 4, f"c:{s}", f"c:{d}", f"p:{s}", f"ledger:sod:{t // DAY}", e, sk, dk, f["a"], t, t // DAY,
                          "1" if want else "0", d, s)
            meta.append((f, want, score_it, t))
        res = await pipe.execute() if meta else []
        tasks, per_type = [], {}
        for (f, want, score_it, t), out in zip(meta, res):
            per_type[f["e"]] = per_type.get(f["e"], 0) + 1
            if not want:
                continue
            x = finalize(out, t, float(f["a"]), "ussd" if f.get("c") == "u" else "app")
            DRIFT.add(x)
            SNAPSHOTS.inc()
            STATS.featured += 1
            if score_it and PARITY_OUT:
                PARITY_ROWS.append([int(f["id"]), *x.tolist()])
            if score_it and client is not None:
                payload = {"sender": f["s"], "receiver": f["d"], "amount": float(f["a"]), "t": t,
                           "channel": "ussd" if f.get("c") == "u" else "app", "event_id": int(f["id"]),
                           "features": [None if math.isnan(v) else v for v in x.tolist()],
                           "produced_ms": float(f["pt"]), "source": "shadow"}
                tasks.append(payload)
        if tasks:  # split into SHADOW_CHUNK-sized micro-batches, scored concurrently across replicas
            await asyncio.gather(*[shadow_score(client, sem, tasks[k:k + SHADOW_CHUNK]) for k in range(0, len(tasks), SHADOW_CHUNK)])
        await r.xack(STREAM, GROUP, *[m[0] for m in msgs])
        now = time.time()
        for et, n in per_type.items():
            EVENTS.labels(et).inc(n)
        last_pt = None
        for f, *_ in meta:
            if f["pt"] != last_pt:  # the producer stamps per chunk: observe the histogram once per distinct stamp
                last_pt = f["pt"]
                lag = now - float(last_pt) / 1000
                LAG.observe(lag)
            STATS.lags.append(lag * 1000)
        STATS.n += len(meta)
        STATS.t_first = STATS.t_first or (now - (time.perf_counter() - t0))
        STATS.t_last = now
        dt = time.perf_counter() - t0
        BATCH_LAT.observe(dt)
        STATS.batch_ms.append(dt * 1000)
        if end_marker:
            dump_parity()
            print("end marker:", json.dumps(STATS.snapshot()), flush=True)
        if now - last_gauges > 5:
            update_drift_gauges()
            last_gauges = now


def main() -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("METRICS_PORT", "9100"))), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass
    asyncio.run(run())


if __name__ == "__main__":
    main()
