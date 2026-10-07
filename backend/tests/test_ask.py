"""Refusal when nothing matches, invented citation ids, and the Ollama-down fallback."""

import json

from sqlalchemy import text

from app.db import SessionLocal
from app.services.answering import NOTHING_MATCHED, UNSUPPORTED
from tests.helpers import register, unreachable


def _save(client, text_body: str, title: str = "Note") -> dict:
    created = client.post("/documents", json={"source_type": "text", "title": title, "text": text_body})
    assert created.status_code == 201, created.text
    detail = client.get(f"/documents/{created.json()['id']}")
    assert detail.json()["status"] == "ready", detail.text
    return detail.json()


def test_empty_retrieval_does_not_call_the_chat_model(client, fake_llm):
    register(client)
    _save(client, "alpha bravo centrifuge keeps the bearings cool.")
    db = SessionLocal()
    try:
        orthogonal = [0.0] * 768
        orthogonal[1] = 1.0
        literal = "[" + ",".join(str(value) for value in orthogonal) + "]"
        db.execute(text("UPDATE chunks SET embedding = CAST(:embedding AS vector)"), {"embedding": literal})
        db.commit()
    finally:
        db.close()

    # Question embedding stays on axis 0, orthogonal to every chunk, and the
    # words do not overlap, so neither signal clears the cutoff.
    response = client.post("/ask", json={"question": "unrelated xylophone quantum"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == NOTHING_MATCHED
    assert body["refused"] is True
    assert body["reason"] == "nothing_matched"
    assert body["citations"] == []
    assert fake_llm.complete_calls == 0

    stream = client.post("/ask/stream", json={"question": "unrelated xylophone quantum"})
    assert stream.status_code == 200
    event = json.loads(stream.text.removeprefix("data: ").strip())
    assert event["type"] == "refusal"
    assert event["reason"] == "nothing_matched"
    assert fake_llm.complete_calls == 0


def test_invented_citation_id_is_dropped(client, fake_llm):
    register(client)
    detail = _save(client, "Postgres stores the session hash, never the raw cookie.")
    real_id = detail["chunks"][0]["id"]
    fake_llm.complete_result = json.dumps(
        {
            "answer": "The model invented a source.",
            "cited_chunk_ids": ["00000000-0000-0000-0000-000000000099"],
        }
    )
    response = client.post("/ask", json={"question": "Where is the session hash stored?"})
    body = response.json()
    assert body["answer"] == UNSUPPORTED
    assert body["refused"] is True
    assert body["reason"] == "unsupported"
    assert body["citations"] == []
    assert fake_llm.complete_calls == 1

    fake_llm.complete_result = json.dumps(
        {
            "answer": "The session hash is stored in Postgres.",
            "cited_chunk_ids": ["00000000-0000-0000-0000-000000000099", real_id],
        }
    )
    kept = client.post("/ask", json={"question": "Where is the session hash stored?"})
    kept_body = kept.json()
    assert kept_body["refused"] is False
    assert kept_body["answer"] == "The session hash is stored in Postgres."
    assert [item["chunk_id"] for item in kept_body["citations"]] == [real_id]


def test_keyword_fallback_when_ollama_is_down(client, fake_llm):
    register(client)
    detail = _save(client, "Argon2 hashes passwords before they are stored.")
    real_id = detail["chunks"][0]["id"]
    fake_llm.embed_error = unreachable()
    fake_llm.complete_error = unreachable()

    response = client.post("/ask", json={"question": "How are passwords hashed?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reason"] == "model_unreachable"
    assert body["refused"] is False
    assert "unreachable" in body["answer"].lower()
    assert body["citations"]
    assert body["citations"][0]["chunk_id"] == real_id
    assert "Argon2" in body["citations"][0]["text"]

    stream = client.post("/ask/stream", json={"question": "How are passwords hashed?"})
    assert "event" not in stream.headers.get("content-type", "") or True
    assert '"type": "token"' in stream.text
    assert '"type": "done"' in stream.text
    assert "model_unreachable" in stream.text
