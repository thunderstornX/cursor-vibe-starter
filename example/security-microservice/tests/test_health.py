def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "security-microservice"
    assert body["version"] == "1.0.0"


def test_health_does_not_require_auth(client):
    """Liveness must NOT depend on the auth path; a bug there would
    quietly take down the readiness signal."""
    r = client.get("/health", headers={})  # no Authorization header
    assert r.status_code == 200


def test_health_response_includes_request_id(client):
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")
