"""Turn a queued document into chunks and, when Ollama is up, embeddings.

The document row is committed as `queued` before the background task runs.
A matching ingest_jobs row moves queued → running → ready or failed so a
restart can see work that did not finish. Embedding failure does not fail
the document: keyword search still works with a null vector.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import trafilatura
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Chunk, Document, IngestJob
from app.services.chunking import chunk_document
from app.services.fetch_url import FetchError, fetch_public_url
from app.services.llm import ModelUnreachable, get_llm
from app.services.ssrf import SSRFError

EMBED_BATCH = 32


class IngestError(ValueError):
    pass


def run_ingest(document_id: str) -> None:
    db = SessionLocal()
    try:
        doc_uuid = UUID(document_id)
        doc = db.get(Document, doc_uuid)
        if doc is None:
            return
        job = db.scalar(select(IngestJob).where(IngestJob.document_id == doc.id))
        if job is not None:
            job.status = "running"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
        try:
            text, title = _extract(doc)
            drafts = chunk_document(text)
            if not drafts:
                raise IngestError("No text extracted")
            db.query(Chunk).filter(Chunk.document_id == doc.id).delete(synchronize_session=False)
            chunks: list[Chunk] = []
            for draft in drafts:
                chunk = Chunk(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    position=draft.position,
                    heading=draft.heading,
                    text=draft.text,
                )
                db.add(chunk)
                chunks.append(chunk)
            db.flush()
            _try_embed(chunks)
            if title and doc.title in {"Untitled", "Untitled note", "Untitled file"}:
                doc.title = title[:200]
            doc.status = "ready"
            doc.error = None
            if job is not None:
                job.status = "ready"
                job.error = None
                job.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            db.rollback()
            message = _error_message(exc)
            failed = db.get(Document, doc_uuid)
            failed_job = db.scalar(select(IngestJob).where(IngestJob.document_id == doc_uuid))
            if failed is not None:
                failed.status = "failed"
                failed.error = message
            if failed_job is not None:
                failed_job.status = "failed"
                failed_job.error = message
                failed_job.updated_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _try_embed(chunks: list[Chunk]) -> None:
    try:
        llm = get_llm()
        for start in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[start : start + EMBED_BATCH]
            vectors = llm.embed([chunk.text for chunk in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                chunk.embedding = vector
    except ModelUnreachable:
        for chunk in chunks:
            chunk.embedding = None


def _extract(doc: Document) -> tuple[str, str | None]:
    if doc.source_type == "url":
        if not doc.source_url:
            raise IngestError("URL document has no source URL")
        try:
            body, _final = fetch_public_url(doc.source_url)
        except SSRFError as exc:
            raise IngestError(str(exc)) from exc
        except FetchError as exc:
            raise IngestError(str(exc)) from exc
        html = body.decode("utf-8", errors="replace")
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
        meta = trafilatura.extract_metadata(html)
        title = meta.title.strip() if meta and meta.title else None
        return extracted.strip(), title
    if not doc.file_path:
        raise IngestError("File is missing")
    path = Path(doc.file_path)
    if not path.is_file():
        raise IngestError("File is missing")
    if path.suffix.lower() == ".pdf":
        return _pdf_text(path), None
    return path.read_text(encoding="utf-8", errors="replace").strip(), None


def _pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(page for page in pages if page).strip()


def _error_message(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:500]
