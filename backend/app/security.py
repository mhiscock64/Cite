"""Password hashing and opaque session cookies."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_hasher = PasswordHasher()
COOKIE_NAME = "cite_session"
SESSION_DAYS = 14


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def new_session_token() -> tuple[str, str, datetime]:
    """Return (raw token, sha256 hex, expiry). Only the hash is stored."""
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    return raw, digest, expires


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
