"""Demo authentication: short-lived JWTs for three roles. Agents and customers can only read their own data."""
from __future__ import annotations

import time

import jwt
from fastapi import Depends, HTTPException, Request

from app.core.config import settings

ROLES = {"customer", "agent", "ops"}
ALGO = "HS256"


def issue(role: str, subject: str, hours: int = 12) -> str:
    now = int(time.time())
    return jwt.encode({"role": role, "sub": subject, "iat": now, "exp": now + hours * 3600}, settings.jwt_secret, algorithm=ALGO)


def current(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in with a demo role first")
    try:
        return jwt.decode(auth[7:], settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Invalid or expired token") from e


def require(*roles: str):
    def dep(user: dict = Depends(current)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"This needs the {' or '.join(roles)} role")
        return user

    return dep


def own(user: dict, subject: str) -> None:
    """Operations staff may read anything; customers and agents only their own record."""
    if user["role"] != "ops" and user["sub"] != subject:
        raise HTTPException(403, "You can only see your own data")
