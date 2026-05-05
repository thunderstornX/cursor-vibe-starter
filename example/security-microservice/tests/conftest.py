"""Shared fixtures.

We pre-set a real (random) JWT_SECRET in the test process so
``Settings`` doesn't refuse to boot. We patch the redis dependency to
a fakeredis instance so tests don't need a real broker, and pre-seed
the demo users."""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient

# Ensure the service module is importable when pytest is run from the
# repo root.
_SVC = Path(__file__).resolve().parents[1]
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

# Seed env BEFORE main is imported so Settings() validates against a
# real secret rather than blowing up.
os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(64))
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
# Default test rate limit is high so unrelated tests don't trip it.
# The dedicated rate-limit test scopes its own limit explicitly.
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "10000")


@pytest.fixture
def fake_redis():
    return fakeredis.FakeRedis()


@pytest.fixture
def client(fake_redis):
    """A TestClient with the redis dependency overridden + demo users
    seeded. We rebuild the app each test so middleware state (the
    rate-limit counters) is fresh."""
    from auth import seed_demo_users
    from config import get_settings
    from redis_dep import get_redis
    import importlib
    import main

    importlib.reload(main)  # rebuild middleware with the new fake redis

    settings = get_settings()
    seed_demo_users(secret=settings.jwt_secret)

    main.app.dependency_overrides[get_redis] = lambda: fake_redis

    return TestClient(main.app)


@pytest.fixture
def alice_token(client):
    r = client.post("/v1/auth/login",
                     json={"username": "alice", "password": "alice_pw"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
