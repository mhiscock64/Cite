"""User-scoped files on local disk. Bytes never go in Postgres."""

import shutil
from pathlib import Path
from uuid import UUID

from app.config import get_settings


def document_dir(user_id: UUID, document_id: UUID) -> Path:
    root = Path(get_settings().file_storage_dir).resolve()
    path = (root / str(user_id) / str(document_id)).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Refusing to write outside the storage root")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_bytes(user_id: UUID, document_id: UUID, filename: str, data: bytes) -> Path:
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Invalid filename")
    directory = document_dir(user_id, document_id)
    target = directory / safe_name
    target.write_bytes(data)
    return target


def remove_document_files(user_id: UUID, document_id: UUID) -> None:
    root = Path(get_settings().file_storage_dir).resolve()
    path = (root / str(user_id) / str(document_id)).resolve()
    if path.is_relative_to(root) and path.exists():
        shutil.rmtree(path)
