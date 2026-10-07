"""Register, login, logout, and the unauthenticated 401."""

from tests.helpers import register


def test_register_login_me_logout(client):
    body = register(client)
    assert body["email"] == "ada@example.com"
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]

    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401

    bad = client.post("/auth/login", json={"email": "ada@example.com", "password": "nope-nope"})
    assert bad.status_code == 401

    good = client.post("/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    assert good.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_duplicate_email_and_anonymous_library(client):
    register(client)
    client.post("/auth/logout")
    again = client.post("/auth/register", json={"email": "ada@example.com", "password": "correct-horse"})
    assert again.status_code == 409
    assert client.get("/documents").status_code == 401
    assert client.post("/ask", json={"question": "anything"}).status_code == 401
