"""Postgres test database, migrated schema, and a fake Ollama client."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_STORAGE = tempfile.mkdtemp(prefix="cite-files-")
os.environ["DATABASE_URL"] = "postgresql+psycopg://cite@127.0.0.1:5432/cite_test"
os.environ["FILE_STORAGE_DIR"] = _STORAGE
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9/v1"
os.environ["COOKIE_SECURE"] = "false"

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal, reset_engine
from app.services.llm import set_llm

get_settings.cache_clear()
reset_engine()


class FakeLLM:
    def __init__(self) -> None:
        self.embed_calls = 0
        self.complete_calls = 0
        self.vector = [0.0] * 768
        self.vector[0] = 1.0
        self.complete_result = '{"answer":"From the library.","cited_chunk_ids":[]}'
        self.embed_error: Exception | None = None
        self.complete_error: Exception | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls += 1
        if self.embed_error:
            raise self.embed_error
        return [list(self.vector) for _ in texts]

    def complete(self, system: str, user: str) -> str:
        self.complete_calls += 1
        if self.complete_error:
            raise self.complete_error
        return self.complete_result


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    admin = psycopg.connect("postgresql://cite@127.0.0.1:5432/postgres", autocommit=True)
    exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = 'cite_test'").fetchone()
    if not exists:
        admin.execute("CREATE DATABASE cite_test")
    admin.close()
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture()
def fake_llm() -> Iterator[FakeLLM]:
    llm = FakeLLM()
    set_llm(llm)  # type: ignore[arg-type]
    yield llm
    set_llm(None)


@pytest.fixture()
def client(fake_llm: FakeLLM) -> Iterator[TestClient]:
    from app.main import app

    db = SessionLocal()
    try:
        db.execute(
            text(
                "TRUNCATE questions, chunks, ingest_jobs, documents, sessions, users RESTART IDENTITY CASCADE"
            )
        )
        db.commit()
    finally:
        db.close()
    with TestClient(app) as test_client:
        yield test_client

