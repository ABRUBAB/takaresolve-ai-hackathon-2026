"""Demo authentication: short-lived JWTs for three roles. Agents and customers can only read their own data.

Signing keys form a keyring so they can be rotated without logging everyone out (docs/security.md):
  JWT_KEYS_FILE  a file OUTSIDE the repository with "kid:secret" entries (comma or new-line separated), or
  JWT_KEYS       the same list in an environment variable / platform secret.
The FIRST key signs new tokens; every listed key still verifies, so a retired key is simply removed from the list.
JWT_SECRET (a single key) still works; with nothing set a random key is made per start (demo tokens are issued again).
Every token must name a known key id (`kid` header), use HS256 (alg "none" or any other algorithm is refused) and carry
exp, iat, sub and a valid role.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, Request

from app.core.config import ROOT, settings

ROLES = {"customer", "agent", "ops"}
ALGO = "HS256"
MIN_SECRET_LEN = 32  # HS256 keys shorter than the 256-bit hash output are refused (RFC 7518, section 3.2)
KID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
log = logging.getLogger("uvera")


@dataclass(frozen=True)
class Keyring:
    keys: dict[str, str]  # kid -> secret; insertion order: the first one signs
    source: str

    @property
    def active_kid(self) -> str:
        return next(iter(self.keys))


def parse_keys(spec: str) -> dict[str, str]:
    """Parse 'kid:secret,kid:secret' (also one per line, '#' comments, or the 'JWT_KEYS=...' line rotate_jwt_key.py prints)."""
    keys: dict[str, str] = {}
    for line in spec.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("JWT_KEYS="):
            line = line[len("JWT_KEYS="):]
        for part in line.split(","):
            part = part.strip()
            if not part:
                continue
            kid, sep, secret = part.partition(":")
            kid, secret = kid.strip(), secret.strip()
            if not sep or not KID_RE.match(kid):
                raise ValueError("JWT key entries must look like kid:secret (kid: letters, digits, . _ -)")
            if len(secret) < MIN_SECRET_LEN:
                raise ValueError(f"JWT key '{kid}' is shorter than {MIN_SECRET_LEN} characters")
            if kid in keys:
                raise ValueError(f"JWT key id '{kid}' is listed twice")
            keys[kid] = secret
    return keys


def load_keyring(jwt_keys: str = "", jwt_keys_file: str = "", jwt_secret: str = "") -> Keyring:
    if jwt_keys_file:
        path = Path(jwt_keys_file).expanduser().resolve()
        try:
            path.relative_to(ROOT.resolve())
            log.warning("JWT_KEYS_FILE is inside the repository folder; keep signing keys outside it (docs/security.md)")
        except ValueError:
            pass
        keys = parse_keys(path.read_text(encoding="utf-8"))
        source = "file"
    elif jwt_keys:
        keys, source = parse_keys(jwt_keys), "env"
    else:
        # single key (JWT_SECRET, or the random per-start key from config.py); its id is derived from the key itself
        keys, source = {"k-" + hashlib.sha256(jwt_secret.encode()).hexdigest()[:8]: jwt_secret}, "single"
    if not keys:
        raise ValueError("the JWT keyring is empty")
    return Keyring(keys, source)


keyring = load_keyring(settings.jwt_keys, settings.jwt_keys_file, settings.jwt_secret)


def issue(role: str, subject: str, hours: int = 12) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    now = int(time.time())
    kid = keyring.active_kid
    return jwt.encode({"role": role, "sub": subject, "iat": now, "exp": now + hours * 3600}, keyring.keys[kid],
                      algorithm=ALGO, headers={"kid": kid})


def _reject(reason: str) -> HTTPException:
    log.info('{"auth_rejected": "%s"}', reason)
    return HTTPException(401, "Invalid or expired token")


def current(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in with a demo role first")
    token = auth[7:].strip()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise _reject("malformed token") from e
    if header.get("alg") != ALGO:  # never "none", never an algorithm the attacker picks
        raise _reject("algorithm not allowed")
    kid = header.get("kid")
    secret = keyring.keys.get(kid) if isinstance(kid, str) else None
    if secret is None:
        raise _reject("unknown or retired key id")
    try:
        claims = jwt.decode(token, secret, algorithms=[ALGO], options={"require": ["exp", "iat", "sub", "role"]})
    except jwt.PyJWTError as e:
        raise _reject(type(e).__name__) from e
    if claims.get("role") not in ROLES or not isinstance(claims.get("sub"), str):
        raise _reject("bad role or subject")
    return claims


def require(*roles: str):
    def dep(user: dict = Depends(current)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"This needs the {' or '.join(roles)} role")
        return user

    dep.roles = roles  # read by the security tests to build the role matrix
    return dep


def own(user: dict, subject: str) -> None:
    """Operations staff may read anything; customers and agents only their own record."""
    if user["role"] != "ops" and user["sub"] != subject:
        raise HTTPException(403, "You can only see your own data")
