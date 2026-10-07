"""Save notes, files, and URLs. Reads are scoped to the signed-in user.

Another user's document is a 404, not a 403, so ids are not an oracle.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user
from app.models import Chunk, Document, IngestJob, User
from app.schemas import ChunkOut, DocumentCreate, DocumentDetail, DocumentOut
from app.services.ingest import run_ingest
from app.services.ssrf import SSRFError, ensure_public_http_url
from app.services.storage import remove_document_files, write_bytes

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


def _owned(db: Session, user: User, document_id: UUID) -> Document:
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


def _out(doc: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type,  # type: ignore[arg-type]
        source_url=doc.source_url,
        status=doc.status,  # type: ignore[arg-type]
        error=doc.error,
        created_at=doc.created_at,
        chunk_count=chunk_count,
    )


def _queue(db: Session, user: User, doc: Document, background: BackgroundTasks) -> DocumentOut:
    db.add(doc)
    db.flush()
    db.add(IngestJob(document_id=doc.id, user_id=user.id, status="queued"))
    db.commit()
    db.refresh(doc)
    background.add_task(run_ingest, str(doc.id))
    return _out(doc, 0)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    body: DocumentCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DocumentOut:
    if body.source_type == "url":
        url = (body.url or "").strip()
        try:
            ensure_public_http_url(url)
        except SSRFError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        title = (body.title or "").strip() or _host_title(url)
        doc = Document(
            user_id=user.id,
            title=title[:200],
            source_type="url",
            source_url=url,
            status="queued",
        )
        return _queue(db, user, doc, background)

    text = (body.text or "").strip()
    title = (body.title or "").strip() or _note_title(text)
    doc = Document(
        user_id=user.id,
        title=title[:200],
        source_type="text",
        status="queued",
    )
    db.add(doc)
    db.flush()
    path = write_bytes(user.id, doc.id, "source.txt", text.encode("utf-8"))
    doc.file_path = str(path)
    db.add(IngestJob(document_id=doc.id, user_id=user.id, status="queued"))
    db.commit()
    db.refresh(doc)
    background.add_task(run_ingest, str(doc.id))
    return _out(doc, 0)


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DocumentOut:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only .txt, .md, and .pdf files are allowed")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    label = (title or "").strip() or filename
    doc = Document(
        user_id=user.id,
        title=label[:200],
        source_type="file",
        status="queued",
    )
    db.add(doc)
    db.flush()
    path = write_bytes(user.id, doc.id, filename, data)
    doc.file_path = str(path)
    db.add(IngestJob(document_id=doc.id, user_id=user.id, status="queued"))
    db.commit()
    db.refresh(doc)
    background.add_task(run_ingest, str(doc.id))
    return _out(doc, 0)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[DocumentOut]:
    rows = db.execute(
        select(Document, func.count(Chunk.id))
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .where(Document.user_id == user.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_out(doc, int(count)) for doc, count in rows]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> DocumentDetail:
    doc = _owned(db, user, document_id)
    chunks = db.scalars(
        select(Chunk).where(Chunk.document_id == doc.id, Chunk.user_id == user.id).order_by(Chunk.position)
    ).all()
    base = _out(doc, len(chunks))
    return DocumentDetail(
        **base.model_dump(),
        chunks=[ChunkOut(id=chunk.id, position=chunk.position, heading=chunk.heading, text=chunk.text) for chunk in chunks],
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    doc = _owned(db, user, document_id)
    remove_document_files(user.id, doc.id)
    db.delete(doc)
    db.commit()


def _note_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return "Untitled note"


def _host_title(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).hostname or "Link"
    return host[:200]
