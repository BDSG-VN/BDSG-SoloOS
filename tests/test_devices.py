from test_cms import AGENT, OWNER
from test_cms import client as client


def test_pairing_one_use_scope_and_revocation(client):
    assert client.post("/api/devices/pair", headers=AGENT, json={"name": "test"}).status_code == 403
    result = client.post(
        "/api/devices/pair", headers=OWNER, json={"name": "test", "scopes": ["read"]}
    )
    assert result.status_code == 200, result.text
    code = result.json()["code"]
    device = client.post("/api/devices/redeem", json={"code": code}).json()
    assert "token" in device, device
    assert client.post("/api/devices/redeem", json={"code": code}).status_code == 422
    auth = {"Authorization": "Bearer " + device["token"]}
    assert client.get("/api/tasks", headers=auth).status_code == 200
    assert client.post("/api/tasks", headers=auth, json={"title": "denied"}).status_code == 403
    assert client.get("/api/cms/content", headers=auth).status_code == 403
    assert (
        client.post("/api/devices/pair", headers=auth, json={"name": "denied"}).status_code == 403
    )
    listing = client.get("/api/devices", headers=OWNER)
    assert device["token"] not in listing.text and code not in listing.text
    assert client.delete("/api/devices/self", headers=auth).status_code == 200
    assert client.get("/api/tasks", headers=auth).status_code == 401


def test_read_and_approval_scopes_combine():
    from server.core.devices import permits

    assert permits(["read", "approvals"], "GET", "/api/confirmations")
    assert permits(["read", "approvals"], "GET", "/api/tasks")
    assert not permits(["read"], "GET", "/api/confirmations")
