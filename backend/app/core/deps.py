"""
Request-scoped dependencies: DB session, current user, CSRF enforcement.
"""

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.models import User

_engine = create_engine(settings.database_url)
_SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Generator[Session, None, None]:
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """docs/API.md §1.7: access token travels as an httpOnly cookie, not a header."""
    access_token = request.cookies.get("access_token")
    if access_token is None:
        raise ApiError(401, "UNAUTHENTICATED", "Kimlik doğrulaması gerekli.")

    user_id = decode_access_token(access_token)
    if user_id is None:
        raise ApiError(401, "UNAUTHENTICATED", "Oturum geçersiz veya süresi dolmuş.")

    user = session.execute(select(User).where(User.id == user_id)).scalars().first()
    if user is None or user.status not in ("PENDING", "ACTIVE"):
        raise ApiError(401, "UNAUTHENTICATED", "Oturum geçersiz veya süresi dolmuş.")

    return user


def require_email_verified(current_user: User = Depends(get_current_user)) -> User:
    """
    docs/API.md §2.1, docs/AUTHORIZATION.md G6: no write succeeds until the
    account's email is verified. Endpoints that mutate state depend on this
    instead of get_current_user directly; read-only endpoints and
    /auth/logout intentionally keep using get_current_user so an unverified
    user can still read their own data and sign out.
    """
    if current_user.email_verified_at is None:
        raise ApiError(401, "EMAIL_NOT_VERIFIED", "E-posta doğrulanmadan bu işlem yapılamaz.")
    return current_user


def require_csrf(request: Request) -> None:
    """
    docs/API.md §2.1: write methods must present X-CSRF-Token matching the
    csrf_token cookie. This is the documented exception to the 404-not-403
    rule — a CSRF failure returns 403 because it does not leak resource
    existence.
    """
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise ApiError(403, "CSRF_FAILED", "CSRF doğrulaması başarısız.")
