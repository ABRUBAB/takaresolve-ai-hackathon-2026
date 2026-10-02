"""UVERA API entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agent, customer, health, meta, ops
from app.core.config import settings
from app.core.telemetry import TraceMiddleware
from app.state import state


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.warm_on_start:
        state.start()  # loads the world and the AI engines in the background
    yield


app = FastAPI(
    title="UVERA API",
    version=settings.app_version,
    description="AI that pauses scams before money moves. Synthetic data only. The AI recommends; humans decide.",
    lifespan=lifespan,
)
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Trace-Id"],
    expose_headers=["X-Trace-Id"],
)
for r in (health.router, meta.router, customer.router, agent.router, ops.router):
    app.include_router(r, prefix="/v1")


@app.get("/")
def root() -> dict:
    return {"name": "UVERA API", "docs": "/docs", "health": "/v1/health/ready", "synthetic_data": True}
