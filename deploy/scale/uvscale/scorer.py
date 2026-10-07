"""Stateless scorer replica: online features from Redis -> AI-1 model -> policy -> Postgres. Scale with replicas.

Run: uvicorn uvscale.scorer:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools --no-access-log
"""
from __future__ import annotations

import math
import os
import socket
import time
from contextlib import asynccontextmanager
from typing import Literal

import asyncpg
import numpy as np
import psutil
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

from uvscale import db
from uvscale.model import PauseModel, TextModel
from uvscale.online_features import DAY, FEATURES, READ_LUA, finalize, keys

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
PG_DSN = os.environ.get("PG_DSN", "postgresql://uvera:uvera@postgres:5432/uvera")
DB_WRITE = os.environ.get("DB_WRITE", "batch")  # batch | sync | off
EXPLAIN = os.environ.get("EXPLAIN", "auto")  # auto (TreeSHAP when not low risk) | always | never
SIM_NOW_T = int(os.environ.get("SIM_NOW_T", str(120 * DAY + 12 * 3600)))
REPLICA = socket.gethostname()
BUCKETS = (.001, .002, .003, .005, .0075, .01, .015, .02, .03, .05, .075, .1, .15, .25, .5, 1, 2.5, 5)

REQ_LAT = Histogram("uvera_request_seconds", "Server-side request latency", ["endpoint"], buckets=BUCKETS)
STAGE_LAT = Histogram("uvera_stage_seconds", "Latency per scoring stage", ["stage"], buckets=BUCKETS)
REQS = Counter("uvera_requests_total", "Requests by endpoint and outcome", ["endpoint", "outcome"])
DECISIONS = Counter("uvera_decisions_total", "Pause Check decisions by risk level", ["risk_level", "unsure"])
MODEL_INFO = Gauge("uvera_model_info", "Served model version (value 1)", ["model", "version", "sha256", "verified"])
DB_QUEUE = Gauge("uvera_db_queue_rows", "Decision rows waiting for the batched Postgres writer")
RSS = Gauge("uvera_process_rss_bytes", "Resident memory of this replica")

S: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    S["model"] = PauseModel()
    S["text"] = TextModel() if os.environ.get("LOAD_TEXT", "1") == "1" else None
    for m in [S["model"]] + ([S["text"]] if S["text"] else []):
        MODEL_INFO.labels(m.info["model"], m.version, m.info["sha256"][:16], str(m.verification["all_ok"]).lower()).set(1)
    S["redis"] = aioredis.from_url(REDIS_URL, decode_responses=True, max_connections=256)
    S["read_sha"] = await S["redis"].script_load(READ_LUA)
    S["pool"] = await asyncpg.create_pool(PG_DSN, min_size=2, max_size=int(os.environ.get("PG_POOL", "8")))
    S["writer"] = db.DecisionWriter(S["pool"], DB_WRITE)
    S["writer"].start()
    async with S["pool"].acquire() as con:
        for m in [S["model"]] + ([S["text"]] if S["text"] else []):
            await con.execute("INSERT INTO model_deployments (replica, model, version, sha256, verified) VALUES ($1,$2,$3,$4,$5)",
                              REPLICA, m.info["model"], m.version, m.info["sha256"], m.verification["all_ok"])
    S["startup_s"] = time.perf_counter() - t0
    yield
    await S["writer"].flush()
    await S["pool"].close()
    await S["redis"].aclose()


app = FastAPI(title="UVERA scorer", default_response_class=ORJSONResponse, lifespan=lifespan)


class TransferIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender: str = Field(min_length=2, max_length=32)
    receiver: str = Field(min_length=2, max_length=32)
    amount: float = Field(gt=0, le=1_000_000)
    channel: Literal["app", "ussd"] = "app"
    t: int | None = Field(None, ge=0, description="event time, seconds since the synthetic calendar start")
    event_id: int | None = None
    sender_balance: float | None = Field(None, ge=0, description="ledger balance at start of day, if the core sends it")
    features: list[float | None] | None = Field(None, description="precomputed point-in-time features (stream shadow mode)")
    produced_ms: float | None = None
    source: Literal["api", "shadow", "loadtest"] = "api"
    explain: Literal["auto", "always", "never"] | None = None


class TextIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=3, max_length=1000)


class AlertIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    wallet: str = Field(min_length=2, max_length=32)
    kind: str = Field("agent_report", max_length=40)
    level: Literal["low", "medium", "high"] = "medium"
    event_id: int | None = None


@app.post("/score/transfer")
async def score_transfer(body: TransferIn) -> dict:
    t0 = time.perf_counter()
    if body.sender == body.receiver:
        REQS.labels("transfer", "rejected").inc()
        raise HTTPException(422, "sender and receiver must differ")
    t = body.t if body.t is not None else SIM_NOW_T
    try:
        if body.features is not None:
            if len(body.features) != len(FEATURES):
                raise HTTPException(422, f"features must have {len(FEATURES)} values")
            x = np.array([math.nan if v is None else v for v in body.features], float)
            feature_source = "request"
        else:
            raw = await S["redis"].evalsha(S["read_sha"], 4, *keys(body.sender, body.receiver, t // DAY), t // DAY, body.receiver, body.sender)
            x = finalize(raw, t, body.amount, body.channel, body.sender_balance)
            feature_source = "online_store"
        t1 = time.perf_counter()
        r = S["model"].score(x, body.amount, body.explain or EXPLAIN)
        t2 = time.perf_counter()
        latency_ms = (t2 - t0) * 1000
        await S["writer"].write(db.decision_row(body, r, latency_ms, REPLICA, body.source))
        t3 = time.perf_counter()
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - count, then surface as 503 so the load balancer can retry elsewhere
        REQS.labels("transfer", "error").inc()
        raise HTTPException(503, f"scoring failed: {type(e).__name__}") from e
    STAGE_LAT.labels("features").observe(t1 - t0)
    STAGE_LAT.labels("model").observe(t2 - t1)
    STAGE_LAT.labels("db").observe(t3 - t2)
    REQ_LAT.labels("transfer").observe(t3 - t0)
    REQS.labels("transfer", r["risk_level"]).inc()
    DECISIONS.labels(r["risk_level"], str(r["unsure"]).lower()).inc()
    return {**r, "features": dict(zip(FEATURES, [None if v != v else round(float(v), 4) for v in x])),
            "feature_source": feature_source, "latency_ms": round((t3 - t0) * 1000, 3), "replica": REPLICA}


class BatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TransferIn] = Field(min_length=1, max_length=1000)


@app.post("/score/batch")
async def score_batch(body: BatchIn) -> dict:
    """Micro-batch scoring for the stream (shadow / post-event) path: one vectorised model call per batch.
    Items without precomputed features are read from the online store in one Redis pipeline."""
    t0 = time.perf_counter()
    items = body.items
    X = np.empty((len(items), len(FEATURES)))
    need = [i for i, it in enumerate(items) if it.features is None]
    if need:
        pipe = S["redis"].pipeline(transaction=False)
        for i in need:
            it = items[i]
            t = it.t if it.t is not None else SIM_NOW_T
            pipe.evalsha(S["read_sha"], 4, *keys(it.sender, it.receiver, t // DAY), t // DAY, it.receiver, it.sender)
        raws = await pipe.execute()
        for i, raw in zip(need, raws):
            it = items[i]
            X[i] = finalize(raw, it.t if it.t is not None else SIM_NOW_T, it.amount, it.channel, it.sender_balance)
    for i, it in enumerate(items):
        if it.features is not None:
            X[i] = [math.nan if v is None else v for v in it.features]
    t1 = time.perf_counter()
    res = S["model"].score_batch(X, [it.amount for it in items], items[0].explain or EXPLAIN)
    t2 = time.perf_counter()
    per_ms = (t2 - t0) * 1000 / len(items)
    for it, r in zip(items, res):
        await S["writer"].write(db.decision_row(it, r, per_ms, REPLICA, it.source))
        DECISIONS.labels(r["risk_level"], str(r["unsure"]).lower()).inc()
    t3 = time.perf_counter()
    STAGE_LAT.labels("batch_features").observe(t1 - t0)
    STAGE_LAT.labels("batch_model").observe(t2 - t1)
    REQ_LAT.labels("batch").observe(t3 - t0)
    REQS.labels("batch", "ok").inc()
    return {"n": len(items), "latency_ms": round((t3 - t0) * 1000, 3), "replica": REPLICA,
            "results": [{"event_id": it.event_id, "risk_level": r["risk_level"], "p_calibrated": round(r["p_calibrated"], 6),
                         "unsure": r["unsure"], "state": r["state"]} for it, r in zip(items, res)]}


@app.post("/score/text")
async def score_text(body: TextIn) -> dict:
    if S["text"] is None:
        raise HTTPException(404, "text model not loaded")
    t0 = time.perf_counter()
    r = S["text"].check(body.text)
    REQ_LAT.labels("text").observe(time.perf_counter() - t0)
    REQS.labels("text", r["state"]).inc()
    return {**r, "latency_ms": round((time.perf_counter() - t0) * 1000, 3), "replica": REPLICA}


@app.post("/alerts")
async def alerts(body: AlertIn) -> dict:
    t0 = time.perf_counter()
    aid = await db.create_alert(S["pool"], body.wallet, body.kind, body.level, body.event_id, f"svc:{REPLICA}")
    REQ_LAT.labels("alert").observe(time.perf_counter() - t0)
    REQS.labels("alert", "created").inc()
    return {"alert_id": aid}


@app.post("/cases/link")
async def cases_link(body: AlertIn) -> dict:
    t0 = time.perf_counter()
    r = await db.link_case(S["pool"], body.wallet, body.kind, f"svc:{REPLICA}")
    REQ_LAT.labels("case_link").observe(time.perf_counter() - t0)
    REQS.labels("case_link", "created" if r["case_created"] else "linked").inc()
    return r


@app.get("/cases/{case_id}")
async def case_get(case_id: int) -> dict:
    t0 = time.perf_counter()
    c = await db.get_case(S["pool"], case_id)
    REQ_LAT.labels("case_get").observe(time.perf_counter() - t0)
    if c is None:
        REQS.labels("case_get", "not_found").inc()
        raise HTTPException(404, "unknown case")
    REQS.labels("case_get", "ok").inc()
    return c


@app.get("/model")
async def model_info() -> dict:
    return {"replica": REPLICA, "ai1": {**S["model"].info, "artifacts": S["model"].verification},
            "ai2": {**S["text"].info, "artifacts": S["text"].verification} if S["text"] else None,
            "explain_mode": EXPLAIN, "db_write_mode": DB_WRITE}


@app.get("/health")
async def health() -> dict:
    ok_redis = bool(await S["redis"].ping())
    async with S["pool"].acquire() as con:
        ok_pg = await con.fetchval("SELECT 1") == 1
    rss = psutil.Process().memory_info().rss
    return {"status": "ok" if ok_redis and ok_pg else "degraded", "replica": REPLICA, "redis": ok_redis, "postgres": ok_pg,
            "model_version": S["model"].version, "artifacts_verified": S["model"].verification["all_ok"],
            "rss_mb": round(rss / 2**20, 1), "startup_s": round(S["startup_s"], 2), "decisions_written": S["writer"].written,
            "db_queue": len(S["writer"].queue)}


@app.get("/metrics")
async def metrics() -> Response:
    RSS.set(psutil.Process().memory_info().rss)
    DB_QUEUE.set(len(S["writer"].queue))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
