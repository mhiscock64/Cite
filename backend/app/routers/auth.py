"""Email and password sessions. The cookie is HTTP-only; the database stores a hash."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import current_user
from app.models import User
from app.models import Session as SessionRow
from app.schemas import LoginIn, RegisterIn, UserOut
from app.security import COOKIE_NAME, SESSION_DAYS, hash_password, new_session_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _embedded_https(request: Request) -> bool:
    """The live preview is an HTTPS iframe. Lax cookies are dropped there."""
    if get_settings().cookie_secure:
        return True
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    return forwarded == "https"


def _set_cookie(response: Response, token: str, request: Request) -> None:
    embedded = _embedded_https(request)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none" if embedded else "lax",
        secure=embedded,
        max_age=SESSION_DAYS * 24 * 3600,
        path="/",
    )
    if embedded:
        # Python 3.12's cookie jar cannot emit Partitioned. Chrome only keeps
        # this cookie inside the preview frame when the attribute is present.
        name, value = response.raw_headers[-1]
        text = value.decode("latin-1")
        if "partitioned" not in text.lower():
            response.raw_headers[-1] = (name, f"{text}; Partitioned".encode("latin-1"))


def _clear_cookie(response: Response, request: Request) -> None:
    embedded = _embedded_https(request)
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="none" if embedded else "lax",
        secure=embedded,
        httponly=True,
    )
    if embedded:
        name, value = response.raw_headers[-1]
        text = value.decode("latin-1")
        if "partitioned" not in text.lower():
            response.raw_headers[-1] = (name, f"{text}; Partitioned".encode("latin-1"))


def _issue(db: Session, user: User, response: Response, request: Request) -> UserOut:
    raw, digest, expires = new_session_token()
    db.add(SessionRow(user_id=user.id, token_hash=digest, expires_at=expires))
    db.commit()
    _set_cookie(response, raw, request)
    return UserOut(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists") from None
    db.refresh(user)
    return _issue(db, user, response, request)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _issue(db, user, response, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)) -> None:
    db.query(SessionRow).filter(SessionRow.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    _clear_cookie(response, request)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, created_at=user.created_at)
