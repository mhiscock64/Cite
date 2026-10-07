"""A second user cannot see or delete someone else's documents."""

from tests.helpers import register


def test_other_user_document_is_404_and_invisible_to_search(client):
    register(client, "ada@example.com")
    created = client.post(
        "/documents",
        json={
            "source_type": "text",
            "title": "Private note",
            "text": "The zephyr quartz protocol lives only in Ada's notebook.",
        },
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    ready = client.get(f"/documents/{document_id}")
    assert ready.json()["status"] == "ready"
    assert ready.json()["chunks"]

    client.post("/auth/logout")
    register(client, "grace@example.com")
    assert client.get(f"/documents/{document_id}").status_code == 404
    assert client.delete(f"/documents/{document_id}").status_code == 404
    assert client.get("/documents").json() == []

    asked = client.post("/ask", json={"question": "zephyr quartz protocol"})
    assert asked.status_code == 200, asked.text
    assert asked.json()["reason"] == "nothing_matched"
    assert asked.json()["citations"] == []

    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    assert client.get(f"/documents/{document_id}").status_code == 200
    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
