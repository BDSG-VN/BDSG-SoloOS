import io
import json
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from PIL import Image

from server.config import Settings
from server.core.cms import CMSStore, ConflictError, ContentInput
from server.engines.cms_writer import generate_content
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


OWNER = {"Authorization": "Bearer " + "o" * 40}
AGENT = {"Authorization": "Bearer " + "a" * 40}
CONTENT = {
    "kind": "page",
    "title": "Trang chủ",
    "slug": "home",
    "blocks": [{"type": "paragraph", "text": "First published content"}],
}


def create(client, **changes):
    r = client.post("/api/cms/content", headers=OWNER, json=CONTENT | changes)
    assert r.status_code == 200, r.text
    return r.json()


def transition(client, doc, action):
    r = client.post(
        f"/api/cms/content/{doc['id']}/transition",
        headers=OWNER,
        json={"action": action, "expected_version": doc["version"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_publish_snapshot_revision_and_homepage(client):
    doc = create(client)
    assert client.get("/pages/home").status_code == 404
    assert (
        client.put("/api/cms/homepage", headers=OWNER, json={"content_id": doc["id"]}).status_code
        == 422
    )
    doc = transition(client, doc, "publish")
    assert (
        client.put("/api/cms/homepage", headers=OWNER, json={"content_id": doc["id"]}).status_code
        == 200
    )
    assert "First published content" in client.get("/").text
    changed = CONTENT | {"blocks": [{"type": "paragraph", "text": "Private second draft"}]}
    body = {"content": changed, "expected_version": doc["version"]}
    result = client.put(f"/api/cms/content/{doc['id']}", headers=OWNER, json=body)
    assert result.status_code == 200
    doc = result.json()
    assert doc["has_unpublished_changes"]
    assert "Private second draft" not in client.get("/").text
    assert client.put(f"/api/cms/content/{doc['id']}", headers=OWNER, json=body).status_code == 409
    assert (
        "Private second draft"
        in client.get(f"/api/cms/content/{doc['id']}/preview", headers=OWNER).text
    )
    doc = transition(client, doc, "publish")
    assert "Private second draft" in client.get("/").text
    r = client.post(
        f"/api/cms/content/{doc['id']}/restore-revision",
        headers=OWNER,
        json={"revision": 1, "expected_version": doc["version"]},
    )
    assert r.status_code == 200
    assert r.json()["blocks"][0]["text"] == "First published content"
    assert "Private second draft" in client.get("/").text
    doc = transition(client, r.json(), "trash")
    assert client.get("/pages/home").status_code == 404
    assert client.get("/api/cms/settings", headers=OWNER).json()["homepage_id"] is None
    doc = transition(client, doc, "restore")
    assert doc["status"] == "draft"
    assert client.get("/pages/home").status_code == 404


def test_owner_only_csrf_and_xss(client):
    assert client.get("/api/cms/content").status_code == 401
    assert client.post("/api/cms/content", headers=AGENT, json=CONTENT).status_code == 403
    doc = create(
        client,
        title="<script>alert(1)</script>",
        blocks=[{"type": "paragraph", "text": '<img src=x onerror="alert(1)">'}],
    )
    for path in (f"/content/{doc['id']}/preview", "/settings", "/media"):
        assert client.get("/api/cms" + path, headers=AGENT).status_code == 403
    assert (
        client.post(
            f"/api/cms/content/{doc['id']}/transition",
            headers=AGENT,
            json={"action": "publish", "expected_version": 1},
        ).status_code
        == 403
    )
    doc = transition(client, doc, "publish")
    text = client.get("/pages/home").text
    assert "<script>alert" not in text and "&lt;script&gt;" in text
    assert "<img src=x" not in text and "&lt;img" in text
    client.post("/api/session", json={"token": "o" * 40}, headers={"Origin": "http://testserver"})
    assert client.post("/api/cms/content", json=CONTENT).status_code == 403
    for href in ("javascript:alert(1)", "//evil.example", "/\\evil.example", "data:text/html,evil"):
        assert (
            client.post(
                "/api/cms/content",
                headers=OWNER,
                json=CONTENT | {"blocks": [{"type": "button", "href": href}]},
            ).status_code
            == 422
        )


def test_media_private_until_published(client):
    raw = io.BytesIO()
    Image.new("RGB", (10, 20), "green").save(raw, format="PNG")
    response = client.post(
        "/api/cms/media", headers=OWNER | {"Content-Type": "image/png"}, content=raw.getvalue()
    )
    assert response.status_code == 200
    src = response.json()["src"]
    assert client.get(src).status_code == 404
    assert client.get("/api/cms" + src).status_code == 401
    private = client.get("/api/cms" + src, headers=OWNER)
    assert private.headers["content-type"] == "image/webp"
    assert private.content[:4] == b"RIFF"
    doc = create(client, blocks=[{"type": "image", "src": src, "alt": "Ảnh"}])
    assert client.get(src).status_code == 404
    doc = transition(client, doc, "publish")
    assert client.get(src).status_code == 200
    transition(client, doc, "unpublish")
    assert client.get(src).status_code == 404
    assert (
        client.post(
            "/api/cms/media", headers=OWNER | {"Content-Type": "image/svg+xml"}, content=b"<svg/>"
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/cms/media", headers=OWNER | {"Content-Type": "image/png"}, content=b"<script/>"
        ).status_code
        == 422
    )


def test_slug_collision_and_optimistic_version(tmp_path):
    store = CMSStore(tmp_path / "cms.db")
    doc = store.save(CONTENT)
    with pytest.raises(ConflictError):
        store.save(CONTENT)
    with pytest.raises(ConflictError):
        store.transition(doc["id"], 999, "publish")
    assert ContentInput(title="Điều hành doanh nghiệp").slug == "dieu-hanh-doanh-nghiep"


def test_gateway_encrypted_and_not_disclosed(client):
    values = {
        "base_url": "https://ai.example/v1",
        "model": "test",
        "api_key": "private-key-do-not-print",
    }
    assert client.put("/api/cms/gateway", headers=AGENT, json=values).status_code == 403
    assert client.put("/api/cms/gateway", headers=OWNER, json=values).status_code == 200
    assert values["api_key"] not in client.get("/api/cms/settings", headers=OWNER).text
    assert values["api_key"].encode() not in client.app.state.cms.path.read_bytes()
    assert client.app.state.cms.gateway()["api_key"] == values["api_key"]
    assert client.get("/api/engines", headers=OWNER).json()["model"] == "test"
    client.put(
        "/api/cms/gateway",
        headers=OWNER,
        json={"base_url": "https://new.example/v1", "model": "test"},
    )
    assert client.app.state.cms.gateway()["api_key"] == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "finish,extra,success",
    [("stop", {}, True), ("length", {}, False), ("stop", {"status": "published"}, False)],
)
async def test_ai_proposal_never_saves_or_publishes(tmp_path, monkeypatch, finish, extra, success):
    cms = CMSStore(tmp_path / "cms.db", Fernet.generate_key().decode())
    cms.configure_gateway("https://ai.example/v1", "test", "secret")
    proposal = json.dumps(CONTENT | extra, ensure_ascii=False)
    chunks = [proposal[:20], proposal[20:]]
    wire = "".join(
        "data: " + json.dumps({"choices": [{"delta": {"content": chunk}}]}) + "\n\n"
        for chunk in chunks
    )
    wire += (
        "data: "
        + json.dumps({"choices": [{"delta": {}, "finish_reason": finish}]})
        + "\n\ndata: [DONE]\n\n"
    )

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, text=wire)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        "server.engines.cms_writer.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    body = SimpleNamespace(
        instruction="Tạo trang chủ",
        kind="page",
        content_id=None,
        reference_text="Facts",
        sources=[],
    )
    events = [
        json.loads(chunk[6:]) async for chunk in generate_content(body, SimpleNamespace(cms=cms))
    ]
    assert any(e["type"] == "proposal" for e in events) == success
    assert events[-1]["type"] == ("done" if success else "error")
    assert cms.list() == [] and cms.public() == [] and cms.homepage() is None


def test_real_cms_mcp_requires_confirmation(client):
    result = client.post(
        "/api/mcp/cms-write/call",
        headers=AGENT,
        json={"tool": "save_content_draft", "arguments": {"content": CONTENT}},
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "requires_confirmation"
    assert client.app.state.cms.list() == []
    pending = client.get("/api/confirmations", headers=OWNER).json()
    decision = client.post(
        f"/api/confirmations/{pending[0]['id']}/decision", headers=OWNER, json={"approved": True}
    )
    assert decision.status_code == 200, decision.text
    assert len(client.app.state.cms.list()) == 1
    assert client.app.state.cms.public() == []
    assert (
        client.post(
            "/api/mcp/cms-write/call", headers=AGENT, json={"tool": "publish", "arguments": {}}
        ).status_code
        == 403
    )


def test_remote_http_key_downgrade_is_rejected(client):
    client.put(
        "/api/cms/gateway",
        headers=OWNER,
        json={"base_url": "https://ai.example/v1", "model": "test", "api_key": "key"},
    )
    assert (
        client.put(
            "/api/cms/gateway",
            headers=OWNER,
            json={"base_url": "http://ai.example/v1", "model": "test"},
        ).status_code
        == 422
    )
    assert client.app.state.cms.gateway()["base_url"] == "https://ai.example/v1"
    assert client.app.state.cms.gateway()["api_key"] == "key"


def test_missing_media_cannot_be_published(client):
    doc = create(client, blocks=[{"type": "image", "src": "/media/" + "a" * 32 + ".webp"}])
    assert (
        client.post(
            f"/api/cms/content/{doc['id']}/transition",
            headers=OWNER,
            json={"action": "publish", "expected_version": doc["version"]},
        ).status_code
        == 422
    )
    assert client.get("/pages/home").status_code == 404
