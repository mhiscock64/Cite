"""Text, PDF, rejected file types, and the ingest job row."""

from fpdf import FPDF
from sqlalchemy import text

from app.db import SessionLocal
from tests.helpers import register


def _pdf_bytes(sentence: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.multi_cell(0, 10, sentence)
    return bytes(pdf.output())


def test_paste_becomes_ready_with_chunks_and_a_job(client):
    register(client)
    response = client.post(
        "/documents",
        json={
            "source_type": "text",
            "text": "# Storage\n\nArgon2 hashes the password. The session cookie is HTTP only.",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "queued"
    document_id = response.json()["id"]
    detail = client.get(f"/documents/{document_id}")
    body = detail.json()
    assert body["status"] == "ready", body
    assert body["error"] is None
    assert body["chunk_count"] >= 1
    assert "Argon2" in body["chunks"][0]["text"] or any("Argon2" in chunk["text"] for chunk in body["chunks"])

    db = SessionLocal()
    try:
        job = db.execute(
            text("SELECT status, error FROM ingest_jobs WHERE document_id = :id"),
            {"id": document_id},
        ).one()
    finally:
        db.close()
    assert job.status == "ready"
    assert job.error is None


def test_pdf_upload_and_rejected_type(client):
    register(client)
    rejected = client.post(
        "/documents/upload",
        files={"file": ("notes.exe", b"MZ not a document", "application/octet-stream")},
    )
    assert rejected.status_code == 400

    uploaded = client.post(
        "/documents/upload",
        files={"file": ("hybrid.pdf", _pdf_bytes("Hybrid retrieval cites the source chunk."), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    detail = client.get(f"/documents/{uploaded.json()['id']}")
    assert detail.json()["status"] == "ready", detail.text
    assert "Hybrid retrieval" in detail.json()["chunks"][0]["text"]


def test_markdown_upload(client):
    register(client)
    uploaded = client.post(
        "/documents/upload",
        files={"file": ("note.md", b"# Title\n\nA markdown file about pgvector.", "text/markdown")},
    )
    assert uploaded.status_code == 201
    detail = client.get(f"/documents/{uploaded.json()['id']}")
    assert detail.json()["status"] == "ready"
    assert detail.json()["source_type"] == "file"
