from __future__ import annotations


def test_create_scan_returns_201_with_resource(client, alice_token):
    r = client.post("/v1/scans",
                     headers={"Authorization": f"Bearer {alice_token}"},
                     json={"target": "example.com", "profile": "quick"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["target"] == "example.com"
    assert body["profile"] == "quick"
    assert body["status"] in ("queued", "done")
    assert body["scan_id"]


def test_create_scan_rejects_invalid_target(client, alice_token):
    """The target must be a domain, not a URL or shell metacharacters."""
    for bad in ("http://example.com",
                 "example.com; rm -rf /",
                 "no-tld",
                 ""):
        r = client.post("/v1/scans",
                         headers={"Authorization": f"Bearer {alice_token}"},
                         json={"target": bad})
        assert r.status_code == 422, f"target {bad!r} should be rejected"


def test_get_scan_404_on_unknown_id(client, alice_token):
    r = client.get("/v1/scans/00000000-0000-0000-0000-000000000000",
                    headers={"Authorization": f"Bearer {alice_token}"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "scan.not_found"


def test_create_then_get_roundtrips(client, alice_token):
    create = client.post("/v1/scans",
                          headers={"Authorization": f"Bearer {alice_token}"},
                          json={"target": "nist.gov", "profile": "deep"}).json()
    fetch = client.get(f"/v1/scans/{create['scan_id']}",
                        headers={"Authorization": f"Bearer {alice_token}"})
    assert fetch.status_code == 200
    assert fetch.json()["scan_id"] == create["scan_id"]


def test_list_scans_only_returns_my_scans(client, alice_token):
    """Bob's scans must not leak into Alice's listing.

    Important security property: even though both users share a
    backing store, the `user` claim from the JWT scopes the lookup."""
    # alice creates a scan
    client.post("/v1/scans",
                 headers={"Authorization": f"Bearer {alice_token}"},
                 json={"target": "alice-example.com"})
    # bob authenticates
    bob = client.post("/v1/auth/login",
                       json={"username": "bob", "password": "bob_pw"}).json()
    bob_token = bob["access_token"]
    client.post("/v1/scans",
                 headers={"Authorization": f"Bearer {bob_token}"},
                 json={"target": "bob-example.com"})

    alice_list = client.get("/v1/scans",
                             headers={"Authorization": f"Bearer {alice_token}"}).json()
    assert all(s["target"] == "alice-example.com" for s in alice_list)
    bob_list = client.get("/v1/scans",
                           headers={"Authorization": f"Bearer {bob_token}"}).json()
    assert all(s["target"] == "bob-example.com" for s in bob_list)
