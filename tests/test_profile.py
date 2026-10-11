from test_cms import AGENT
from test_cms import client as client


def test_profile_and_password_security(client):
    origin = {"Origin": "http://testserver"}
    old = "original-password-long"
    new = "changed-password-long"
    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/profile", headers=AGENT).status_code == 403
    assert (
        client.post(
            "/api/setup",
            json={"token": "o" * 40, "username": "owner", "password": old},
            headers=origin,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": old}, headers=origin
        ).status_code
        == 200
    )
    previous_cookie = client.cookies.get("bdsg_session")
    session = client.get("/api/session").json()
    headers = origin | {"X-CSRF-Token": session["csrf"]}
    profile = {"display_name": "Tên mới", "email": "owner@example.com", "bio": "Giới thiệu"}
    assert client.put("/api/profile", json=profile).status_code == 403
    assert (
        client.put("/api/profile", json=profile, headers=headers).json()["display_name"]
        == "Tên mới"
    )
    data = client.get("/api/profile").json()
    assert "salt" not in data and "password" not in data
    assert (
        client.post(
            "/api/profile/password",
            json={"current_password": "wrong", "new_password": new},
            headers=headers,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/profile/password", json={"current_password": old, "new_password": new}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/profile/password",
            json={"current_password": old, "new_password": new},
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get("/api/session").status_code == 401
    assert (
        client.get(
            "/api/session", headers={"Cookie": "bdsg_session=" + previous_cookie}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": old}, headers=origin
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/session", json={"username": "owner", "password": new}, headers=origin
        ).status_code
        == 200
    )
    assert client.get("/api/profile").json()["display_name"] == "Tên mới"
