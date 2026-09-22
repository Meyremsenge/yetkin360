"""
Password hashing (Argon2id) and JWT access-token encode/decode.

Refresh tokens are opaque random values, not JWTs — see app/services/auth.py.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_password_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_refresh_token() -> str:
    """Opaque, unguessable refresh token value. Stored in DB only as a hash."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """
    SHA-256, not Argon2id: the token already has 384 bits of entropy from
    secrets.token_urlsafe, so a slow KDF buys nothing and would make every
    /auth/refresh call pay Argon2's cost.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def generate_email_token() -> str:
    """Opaque, unguessable value for email-verification/password-reset links."""
    return secrets.token_urlsafe(32)


def hash_email_token(token: str) -> str:
    """SHA-256, not Argon2id — same reasoning as hash_refresh_token: the token
    already has enough entropy from secrets.token_urlsafe."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def encode_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Returns the user_id encoded in the token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None
