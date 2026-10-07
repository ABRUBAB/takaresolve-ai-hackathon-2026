"""Validation errors that cannot crash the error response.

FastAPI echoes the rejected input inside a 422 response. When that input is a non-finite number (JSON `1e309`, or the
non-standard `NaN` / `Infinity` tokens Python's parser accepts), the default handler fails to serialise it and the
client gets a 500 instead of a 422 (found by backend/tests/test_security.py). Same response shape, finite values only.
"""
from __future__ import annotations

import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)  # "inf", "-inf", "nan"
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_finite(v) for v in value]
    return value


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": _finite(jsonable_encoder(exc.errors()))})


def install(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error)
