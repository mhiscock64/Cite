"""SQLAlchemy engine and session factory."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine() -> None:
    """Tests change DATABASE_URL before import; this rebuilds the pool if needed."""
    global engine, SessionLocal
    engine.dispose()
    engine = _engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
