"""Request dependencies."""

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.models import Session as SessionRow
from app.security import COOKIE_NAME, hash_token


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def current_user(
    db: Session = Depends(get_db),
    cite_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> User:
    if not cite_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    row = db.scalar(select(SessionRow).where(SessionRow.token_hash == hash_token(cite_session)))
    if row is None or _as_utc(row.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user
