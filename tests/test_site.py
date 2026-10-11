from test_cms import AGENT, OWNER
from test_cms import client as client


def test_home_is_public_and_templates_stay_drafts(client):
    home = client.get("/")
    assert home.status_code == 200
    assert "Khám phá bài viết" in home.text
    assert "BDSG_OWNER_TOKEN" not in home.text
    assert client.get("/api/cms/themes").status_code == 401
    assert client.get("/api/cms/themes", headers=AGENT).status_code == 403
    themes = client.get("/api/cms/themes", headers=OWNER).json()
    assert len(themes) == 8
    for theme in themes:
        response = client.post("/api/cms/themes/" + theme["id"] + "/draft", headers=OWNER)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "draft"
    assert client.get("/").text == home.text


def test_site_metadata_escaped_and_theme_validated(client):
    data = {
        "title": "<script>alert(1)</script>",
        "tagline": "<img onerror=alert(1)>",
        "theme": "travel",
    }
    assert client.put("/api/cms/site", json=data, headers=OWNER).status_code == 200
    page = client.get("/").text
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
    assert (
        client.put("/api/cms/site", json=data | {"theme": "bad"}, headers=OWNER).status_code == 422
    )


def test_customer_session_cannot_access_admin(client):
    origin = {"Origin": "http://testserver"}
    body = {"email": "guest@example.com", "name": "Guest", "password": "correct horse battery"}
    assert client.post("/api/members/register", json=body, headers=origin).status_code == 403
    assert (
        client.put("/api/cms/site", json={"registration": True}, headers=OWNER).status_code == 200
    )
    assert client.post("/api/members/register", json=body).status_code == 403
    assert client.post("/api/members/register", json=body, headers=origin).status_code == 201
    login = {"email": body["email"], "password": body["password"]}
    assert client.post("/api/members/login", json=login, headers=origin).status_code == 200
    session = client.get("/api/members/session").json()
    assert session["name"] == "Guest"
    assert client.get("/api/session").status_code == 401
    assert client.get("/api/cms/content").status_code == 401
    assert client.post("/api/tasks", json={"title": "unauthorized"}).status_code == 401
    assert client.delete("/api/members/session").status_code == 403
    assert (
        client.delete("/api/members/session", headers={"X-CSRF-Token": session["csrf"]}).status_code
        == 204
    )
    assert client.get("/api/members/session").status_code == 401


def test_installer_is_once_and_requires_server_key(client):
    origin = {"Origin": "http://testserver"}
    body = {"token": "o" * 40, "username": "owner", "password": "sufficiently long password"}
    assert client.get("/api/setup").json() == {"installed": False}
    assert (
        client.post("/api/setup", json=body | {"token": "x" * 40}, headers=origin).status_code
        == 401
    )
    assert client.post("/api/setup", json=body, headers=origin).status_code == 200
    assert client.post("/api/setup", json=body, headers=origin).status_code == 422
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": body["password"]}, headers=origin
        ).status_code
        == 200
    )
    assert client.get("/api/session").status_code == 200
    assert (
        client.post(
            "/api/session", json={"username": "other", "password": body["password"]}, headers=origin
        ).status_code
        == 401
    )


def test_owner_and_customer_sessions_can_coexist(client):
    from test_api import login

    login(client)
    assert (
        client.put("/api/cms/site", json={"registration": True}, headers=OWNER).status_code == 200
    )
    origin = {"Origin": "http://testserver"}
    credentials = {"email": "dual@example.com", "password": "twelve or more characters"}
    assert (
        client.post(
            "/api/members/register", headers=origin, json=credentials | {"name": "Dual"}
        ).status_code
        == 201
    )
    assert client.post("/api/members/login", headers=origin, json=credentials).status_code == 200
    member = client.get("/api/members/session").json()
    assert (
        client.delete("/api/members/session", headers={"X-CSRF-Token": member["csrf"]}).status_code
        == 204
    )
    assert client.get("/api/session").status_code == 200


def test_discovery_never_exposes_drafts(client):
    from test_cms import create, transition

    doc = create(client, title="Secret draft keyword", kind="post", slug="secret")
    for path in ["/search?q=keyword", "/feed.xml", "/sitemap.xml"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "Secret draft keyword" not in response.text
        assert "/news/secret" not in response.text
    transition(client, doc, "publish")
    assert "Secret draft keyword" in client.get("/search?q=keyword").text
    assert "/news/secret" in client.get("/sitemap.xml").text
    assert "Secret draft keyword" in client.get("/feed.xml").text
    assert "Disallow: /admin" in client.get("/robots.txt").text
