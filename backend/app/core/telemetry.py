"""Trace IDs, structured logs, latency + model-health counters, and a simple per-client rate limit."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import Counter, defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

log = logging.getLogger("uvera")
logging.basicConfig(level=settings.log_level.upper(), format="%(message)s")


class Telemetry:
    def __init__(self):
        self.latency = defaultdict(lambda: deque(maxlen=500))
        self.counts = Counter()

    def observe(self, route: str, ms: float, status: int) -> None:
        self.latency[route].append(ms)
        self.counts[f"requests:{route}"] += 1
        if status >= 500:
            self.counts["errors_5xx"] += 1

    def inc(self, key: str, n: int = 1) -> None:
        self.counts[key] += n

    def summary(self) -> dict:
        routes = {}
        for r, v in self.latency.items():
            s = sorted(v)
            routes[r] = {"n": len(s), "p50_ms": round(s[len(s) // 2], 1), "p95_ms": round(s[int(len(s) * 0.95) - 1 if len(s) > 1 else 0], 1)}
        return {"routes": routes, "counters": dict(self.counts)}


telemetry = Telemetry()


def mask(value: str) -> str:
    return value if len(value) < 5 else value[:3] + "***" + value[-2:]


class TraceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.hits = defaultdict(lambda: deque(maxlen=settings.rate_limit_per_minute + 1))

    async def dispatch(self, request: Request, call_next):
        trace = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
        request.state.trace_id = trace
        client = request.client.host if request.client else "unknown"
        now = time.time()
        q = self.hits[client]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute and request.url.path.startswith("/v1/") and "/health/" not in request.url.path:
            return JSONResponse({"detail": "Too many requests, slow down", "trace_id": trace}, status_code=429,
                                headers={"x-trace-id": trace})
        q.append(now)
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000
        route = request.scope.get("route").path if request.scope.get("route") else request.url.path
        telemetry.observe(route, ms, response.status_code)
        response.headers["x-trace-id"] = trace
        log.info(json.dumps({"trace_id": trace, "method": request.method, "route": route, "status": response.status_code,
                             "ms": round(ms, 1), "client": mask(client)}))
        return response
