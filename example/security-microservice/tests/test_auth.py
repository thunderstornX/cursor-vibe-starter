from __future__ import annotations

import jwt as pyjwt
import pytest


def test_login_happy_path(client):
    r = client.post("/v1/auth/login",
                     json={"username": "alice", "password": "alice_pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["expires_in"] > 0
    # Login response MUST NOT include user object — that's a leak.
    assert "user" not in body
    assert "username" not in body


def test_login_wrong_password_is_401(client):
    r = client.post("/v1/auth/login",
                     json={"username": "alice", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "auth.bad_credentials"


def test_login_unknown_user_is_401_with_same_code(client):
    """Username enumeration prevention: same code as wrong-password."""
    r = client.post("/v1/auth/login",
                     json={"username": "nobody", "password": "irrelevant"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "auth.bad_credentials"


def test_login_validates_field_lengths(client):
    r = client.post("/v1/auth/login",
                     json={"username": "", "password": ""})
    assert r.status_code == 422


def test_protected_route_requires_bearer(client):
    """No Authorization header -> 403 from FastAPI's HTTPBearer
    auto_error path. Documented FastAPI behaviour; what matters is
    the route is gated."""
    r = client.post("/v1/scans", json={"target": "example.com"})
    assert r.status_code in (401, 403)


def test_protected_route_rejects_alg_none_token(client):
    """Hand-craft an alg=none token and confirm the service refuses
    it. This is the JWT alg-confusion bug; PyJWT will silently accept
    if `algorithms` is a string instead of a list."""
    forged = pyjwt.encode({"sub": "alice"}, "", algorithm="none")
    r = client.get(f"/v1/scans/anything",
                    headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    code = r.json()["error"]["code"]
    assert code in ("auth.invalid", "auth.bad_alg")


def test_protected_route_rejects_tampered_token(client, alice_token):
    bad = alice_token[:-3] + "xyz"
    r = client.get("/v1/scans/anything",
                    headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "auth.invalid"
