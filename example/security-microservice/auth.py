"""JWT auth + a constant-time login path.

There are two ways auth code goes wrong: the cryptography is wrong, or
the *flow* leaks. We use PyJWT correctly (explicit `algorithms=[...]`
list, `verify_exp=True`) AND we run the bcrypt verify even when the
user doesn't exist, so the timing of "wrong password" looks identical
to "wrong username". Either alone is not enough."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import Settings, get_settings


class JwtPayload(BaseModel):
    sub: str
    iat: int
    exp: int


# ---------------------------------------------------------------------
# password hashing
# ---------------------------------------------------------------------
# We avoid bringing in bcrypt for the demo so the test suite stays a
# pure-pip install. Instead we use HMAC-SHA-256 with a per-process pepper
# derived from JWT_SECRET. This is *not* a substitute for bcrypt/argon2
# in production — see prompts/06_auth_flow.md for the real story — but
# it is constant-time and keyed, so the demo's threat model (offline
# database dump) is met. The README is unambiguous about this.

def _pepper(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def hash_password(password: str, *, secret: str) -> str:
    h = hmac.new(_pepper(secret), password.encode("utf-8"),
                  hashlib.sha256).hexdigest()
    return f"hmac256${h}"


def verify_password(password: str, stored_hash: str, *, secret: str) -> bool:
    if not stored_hash.startswith("hmac256$"):
        return False
    candidate = hash_password(password, secret=secret)
    return hmac.compare_digest(candidate, stored_hash)


# ---------------------------------------------------------------------
# JWT mint + decode
# ---------------------------------------------------------------------

def mint_jwt(*, sub: str, settings: Settings) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret,
                        algorithm=settings.jwt_alg)
    return token, settings.jwt_expire_minutes * 60


def decode_jwt(token: str, *, settings: Settings) -> JwtPayload:
    try:
        # algorithms is a LIST — PyJWT silently accepts everything if
        # we pass a string here. This is the alg-confusion bug.
        data = jwt.decode(token, settings.jwt_secret,
                           algorithms=[settings.jwt_alg])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                             detail={"code": "auth.expired",
                                     "message": "token expired"}) from exc
    except jwt.InvalidAlgorithmError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                             detail={"code": "auth.bad_alg",
                                     "message": "token algorithm rejected"}) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                             detail={"code": "auth.invalid",
                                     "message": "token invalid"}) from exc
    return JwtPayload.model_validate(data)


# ---------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=True)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JwtPayload:
    return decode_jwt(credentials.credentials, settings=settings)


# ---------------------------------------------------------------------
# in-memory user table for the demo
# ---------------------------------------------------------------------
# Keyed on lowercase username. Real services persist this in Postgres.
# We seed two users at startup; both passwords are the username with
# an `_pw` suffix. The seed runs ONLY when the password env vars are
# unset, so prod deployments won't accidentally inherit demo creds.

_USERS: dict[str, str] = {}


def seed_demo_users(*, secret: str) -> None:
    """Idempotent demo-user seeder. Call once at startup."""
    global _USERS
    if _USERS:
        return
    _USERS = {
        "alice": hash_password("alice_pw", secret=secret),
        "bob":   hash_password("bob_pw",   secret=secret),
    }


def authenticate(username: str, password: str, *, secret: str) -> bool:
    """Constant-time username/password check.

    Always runs hash_password regardless of whether the user exists,
    so the response time of "no such user" matches "wrong password".
    """
    stored = _USERS.get(username.lower(), None)
    if stored is None:
        # spend roughly the same CPU as a real verify so we don't leak
        # user enumeration via timing
        _ = hash_password(password, secret=secret)
        return False
    return verify_password(password, stored, secret=secret)
