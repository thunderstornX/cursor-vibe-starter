from __future__ import annotations

import importlib
import os


def test_rate_limit_returns_429_with_retry_after(monkeypatch, fake_redis):
    """After RATE_LIMIT_PER_MINUTE consecutive calls from the same
    JWT, further calls in the same minute window get a structured 429
    with a `Retry-After` header so well-behaved clients back off."""
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "5")
    # rebuild the app under the new limit
    import config, main
    config.get_settings.cache_clear() if hasattr(config.get_settings, "cache_clear") else None
    importlib.reload(config)
    importlib.reload(main)
    from fastapi.testclient import TestClient
    from redis_dep import get_redis
    main.app.dependency_overrides[get_redis] = lambda: fake_redis
    client = TestClient(main.app)

    # log alice in (this counts as one rate-limited request)
    tok = client.post("/v1/auth/login",
                       json={"username": "alice",
                              "password": "alice_pw"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    last_status = None
    for _ in range(20):
        r = client.get("/v1/scans", headers=headers)
        last_status = r.status_code
        if last_status == 429:
            assert r.json()["error"]["code"] == "rate.limited"
            assert r.headers.get("Retry-After") == "60"
            return
    raise AssertionError(f"never hit 429; last_status={last_status}")


def test_health_is_exempt_from_rate_limit(client):
    """Rate-limiting /health would amplify outages: an automatic
    health prober would suddenly start failing under load."""
    for _ in range(200):
        assert client.get("/health").status_code == 200
