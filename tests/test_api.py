import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from server.config import Settings
from server.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        "o" * 40,
        "a" * 40,
        Fernet.generate_key().decode(),
        tmp_path,
        ("http://testserver",),
        ("testserver",),
    )
    with TestClient(create_app(settings)) as client:
        yield client


def login(client):
    response = client.post(
        "/api/session", json={"token": "o" * 40}, headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    return client.get("/api/session").json()["csrf"]


def test_auth_and_csrf(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/brain").status_code == 401
    assert client.post("/api/session", json={"token": "o" * 40}).status_code == 403
    csrf = login(client)
    assert client.post("/api/tasks", json={"title": "blocked"}).status_code == 403
    assert (
        client.post(
            "/api/tasks", json={"title": "blocked"}, headers={"X-CSRF-Token": "invented"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/tasks", json={"title": "allowed"}, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/tasks",
            json={"title": "blocked"},
            headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"},
        ).status_code
        == 403
    )


def test_agent_cannot_approve_or_configure_or_save_brain(client):
    headers = {"Authorization": "Bearer " + "a" * 40}
    assert client.get("/api/confirmations", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/confirmations/fake/decision", json={"approved": True}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/mcp/connectors", json={"id": "test", "command": "echo"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/brain", json={"path": "wiki/test.md", "content": "no"}, headers=headers
        ).status_code
        == 403
    )


def test_cors_and_invalid_bearer_cannot_fallback_to_owner_cookie(client):
    login(client)
    assert client.get("/api/brain", headers={"Authorization": "Bearer fake"}).status_code == 401
    trusted = client.options(
        "/api/tasks",
        headers={"Origin": "http://testserver", "Access-Control-Request-Method": "POST"},
    )
    assert trusted.headers["access-control-allow-origin"] == "http://testserver"
    untrusted = client.options(
        "/api/tasks",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in untrusted.headers
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_owner_brain_confirmation_flow(client):
    csrf = login(client)
    headers = {"X-CSRF-Token": csrf}
    pending = client.post(
        "/api/brain", json={"path": "wiki/goal.md", "content": "My goal"}, headers=headers
    )
    assert pending.json()["status"] == "requires_confirmation"
    confirmation_id = pending.json()["confirmation_id"]
    assert client.get("/api/brain").json() == []
    approved = client.post(
        f"/api/confirmations/{confirmation_id}/decision", json={"approved": True}, headers=headers
    )
    assert approved.json()["status"] == "completed"
    assert client.get("/api/brain").json()[0]["content"] == "My goal"
    assert (
        client.post(
            f"/api/confirmations/{confirmation_id}/decision",
            json={"approved": True},
            headers=headers,
        ).status_code
        == 403
    )


def test_security_headers_and_demo(client):
    login(client)
    response = client.get("/api/demo/stream")
    assert '"type": "done"' in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_login_unicode_and_rate_limit(client):
    headers = {"Origin": "http://testserver"}
    assert (
        client.post(
            "/api/session", json={"token": "khóa-không-hợp-lệ"}, headers=headers
        ).status_code
        == 401
    )
    for _ in range(9):
        assert (
            client.post("/api/session", json={"token": "wrong"}, headers=headers).status_code == 401
        )
    response = client.post("/api/session", json={"token": "wrong"}, headers=headers)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_model_cannot_supply_approval_flag(client):
    headers = {"Authorization": "Bearer " + "a" * 40}
    response = client.post(
        "/api/mcp/second-brain/call",
        headers=headers,
        json={"tool": "write_note", "arguments": {}, "approved": True},
    )
    assert response.status_code == 422


def test_logout_revokes_saved_cookie(client):
    csrf = login(client)
    cookie = client.cookies.get("bdsg_session")
    assert client.delete("/api/session").status_code == 403
    assert client.delete("/api/session", headers={"X-CSRF-Token": csrf}).status_code == 200
    client.cookies.set("bdsg_session", cookie)
    assert client.get("/api/brain").status_code == 401


def test_new_workspaces_are_owner_only_and_csrf_protected(client):
    for path in ["/api/ai/accounts", "/api/workspace/sessions", "/api/automation"]:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer " + "a" * 40}).status_code == 403
    csrf = login(client)
    assert client.post("/api/ai/chatgpt/start", json={}).status_code == 403
    assert (
        client.post("/api/workspace/sessions", json={}, headers={"X-CSRF-Token": csrf}).status_code
        == 200
    )


def test_library_scoped_sessions_and_public_snapshot_revocation(client):
    headers = {"Authorization": "Bearer " + "o" * 40}
    created = client.post("/api/library", headers=headers, json={"title": "Private brain"}).json()
    identifier = created["id"]
    session = client.post(
        "/api/workspace/sessions",
        headers=headers,
        json={"title": "Private chat", "brain_id": identifier},
    ).json()
    bad = client.post(
        "/api/library/default/learn", headers=headers, json={"conversation": session["id"]}
    )
    assert bad.status_code == 422
    client.app.state.brain.add(session["id"], "user", "original snapshot")
    share = client.post("/api/shares", headers=headers, json={"conversation": session["id"]}).json()
    token = share["url"].split("/")[-1]
    assert (
        client.get("/api/shared/" + token).json()["messages"][0]["content"] == "original snapshot"
    )
    client.app.state.brain.add(session["id"], "user", "private later")
    assert "private later" not in client.get("/api/shared/" + token).text
    assert client.get("/api/shares").status_code == 401
    assert client.delete("/api/shares/" + share["id"], headers=headers).status_code == 200
    assert client.get("/api/shared/" + token).status_code == 404
