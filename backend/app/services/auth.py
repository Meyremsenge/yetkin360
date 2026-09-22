"""
Auth service: register, login, refresh-token rotation, logout.

docs/API.md §1.7/§2.1, docs/SECURITY.md §5: access token is a short-lived JWT,
refresh token is an opaque DB-backed value that rotates on every use. Reuse of
an already-rotated refresh token revokes its whole family (theft signal).

Error handling here raises typed exceptions; the API layer (app/api/auth.py)
maps them to HTTP responses per docs/API.md §1.4 error format.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    encode_access_token,
    generate_csrf_token,
    generate_email_token,
    generate_refresh_token,
    hash_email_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import (
    EmailVerificationToken,
    InstitutionMember,
    OrganizationMember,
    PasswordResetToken,
    RefreshToken,
    TalentProfile,
    User,
)
from app.services.audit import log_audit_event
from app.services.outbox import enqueue

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
PASSWORD_RESET_TOKEN_TTL_HOURS = 1

FAILED_LOGIN_LOCK_THRESHOLD = 10
FAILED_LOGIN_LOCK_MINUTES = 15


class InvalidCredentials(Exception):
    pass


class AccountLocked(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


class InvalidEmailToken(Exception):
    pass


class EmailTokenExpired(Exception):
    pass


@dataclass
class IssuedTokens:
    user_id: uuid.UUID
    access_token: str
    refresh_token: str
    csrf_token: str
    refresh_expires_at: datetime


@dataclass
class RegisteredUser:
    user_id: uuid.UUID


@dataclass
class AuthResult:
    tokens: IssuedTokens
    email_verified: bool
    role: str


def summarize_role(session: Session, user: User) -> str:
    """
    Coarse role label for the login/refresh response only — not an
    authorization decision (docs/AUTHORIZATION.md is the source of truth for
    that). Highest-privilege membership wins.

    NOTE: docs/DOMAIN.md lists `users.is_platform_admin`, but that column
    does not exist yet on the User model (app/models/identity.py) as of
    PLAN 1.2/1.3. Treated as False here until it lands; flagged to the user
    rather than added silently under PLAN 1.4's scope.
    """
    if session.execute(
        select(InstitutionMember).where(
            InstitutionMember.user_id == user.id, InstitutionMember.role == "COORDINATOR"
        )
    ).scalars().first():
        return "COORDINATOR"

    if session.execute(
        select(InstitutionMember).where(
            InstitutionMember.user_id == user.id, InstitutionMember.role == "ADMIN"
        )
    ).scalars().first():
        return "INST_ADMIN"

    if session.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id, OrganizationMember.role == "ADMIN"
        )
    ).scalars().first():
        return "ORG_ADMIN"

    if session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).scalars().first():
        return "ORG_MEMBER"

    return "TALENT"


def register_user(session: Session, email: str, password: str, full_name: str) -> RegisteredUser:
    """
    Create a user + empty talent profile in one transaction (docs/API.md §2.1:
    registration never takes a role — role lives on membership, not on User).

    docs/SECURITY.md §4 senaryo 10: registration must not let an attacker
    enumerate which emails are already registered. If the email is already
    taken, this returns as if registration succeeded (a fake, non-existent
    user_id — never the real one, which would itself leak that the account
    exists) and does not touch the existing row. The real account holder
    is notified via outbox: a duplicate-registration attempt is enqueued to
    the email.duplicate_registration_attempt topic, which the outbox worker
    will process asynchronously without blocking this transaction.
    """
    existing = session.execute(select(User).where(User.email == email)).scalars().first()
    if existing is not None:
        log_audit_event(
            session=session,
            actor_user_id=None,
            actor_ip=None,
            action="USER_REGISTER_DUPLICATE_EMAIL",
            subject_type="user",
            subject_id=existing.id,
            result="DENIED",
        )
        # Enqueue email notification (PLAN 1.5: outbox pattern)
        # Payload uses "user_email" (safe key) instead of "email" (sensitive key)
        enqueue(
            session=session,
            topic="email.duplicate_registration_attempt",
            payload={"user_email": email},
        )
        return RegisteredUser(user_id=uuid.uuid4())

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.flush()

    profile = TalentProfile(user_id=user.id, full_name=full_name)
    session.add(profile)
    session.flush()

    log_audit_event(
        session=session,
        actor_user_id=user.id,
        actor_ip=None,
        action="USER_REGISTER",
        subject_type="user",
        subject_id=user.id,
        result="SUCCESS",
    )

    _issue_email_verification_token(session, user.id)

    return RegisteredUser(user_id=user.id)


def _issue_email_verification_token(session: Session, user_id: uuid.UUID) -> None:
    """
    Creates the token row (hash only) and enqueues delivery. The raw token is
    a one-way hash in the DB, so it can only reach the worker through the
    outbox payload itself — app/services/outbox.py whitelists "raw_token" for
    this topic specifically for that reason (see its module docstring).
    """
    raw_token = generate_email_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_TTL_HOURS)

    session.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_email_token(raw_token),
            expires_at=expires_at,
        )
    )
    session.flush()

    enqueue(
        session=session,
        topic="email.verify_email",
        payload={"user_id": str(user_id), "raw_token": raw_token},
    )


def request_password_reset(session: Session, email: str) -> None:
    """
    docs/API.md §2.1: always returns as if the email was sent, whether or not
    the account exists — same enumeration guard as register_user/forgot-password.
    """
    user = session.execute(select(User).where(User.email == email)).scalars().first()
    if user is None:
        return

    raw_token = generate_email_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_TTL_HOURS)

    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_email_token(raw_token),
            expires_at=expires_at,
        )
    )
    session.flush()

    enqueue(
        session=session,
        topic="email.password_reset",
        payload={"user_id": str(user.id), "raw_token": raw_token},
    )

    log_audit_event(
        session=session,
        actor_user_id=None,
        actor_ip=None,
        action="PASSWORD_RESET_REQUESTED",
        subject_type="user",
        subject_id=user.id,
        result="SUCCESS",
    )


def verify_email(session: Session, raw_token: str) -> None:
    # FOR UPDATE closes a double-claim race: without it, two concurrent
    # requests for the same token can both read used_at IS NULL and both
    # succeed.
    token_hash = hash_email_token(raw_token)
    token = session.execute(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == token_hash)
        .with_for_update()
    ).scalars().first()

    if token is None or token.used_at is not None:
        raise InvalidEmailToken()

    if token.expires_at <= datetime.now(timezone.utc):
        raise EmailTokenExpired()

    token.used_at = datetime.now(timezone.utc)

    user = session.execute(select(User).where(User.id == token.user_id)).scalars().first()
    if user is not None:
        user.email_verified_at = datetime.now(timezone.utc)

    session.flush()

    log_audit_event(
        session=session,
        actor_user_id=token.user_id,
        actor_ip=None,
        action="EMAIL_VERIFIED",
        subject_type="user",
        subject_id=token.user_id,
        result="SUCCESS",
    )


def reset_password(session: Session, raw_token: str, new_password: str) -> None:
    # FOR UPDATE closes a double-claim race: without it, two concurrent
    # requests for the same token can both read used_at IS NULL and both
    # succeed.
    token_hash = hash_email_token(raw_token)
    token = session.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    ).scalars().first()

    if token is None or token.used_at is not None:
        raise InvalidEmailToken()

    if token.expires_at <= datetime.now(timezone.utc):
        raise EmailTokenExpired()

    token.used_at = datetime.now(timezone.utc)

    user = session.execute(select(User).where(User.id == token.user_id)).scalars().first()
    if user is not None:
        user.password_hash = hash_password(new_password)
        user.failed_login_count = 0
        user.locked_until = None

        # A password reset is also a credential-theft recovery path — revoke
        # every existing refresh token so a stolen session doesn't survive it.
        # FOR UPDATE closes the race with a concurrent /auth/refresh: without
        # it, refresh_tokens() could read a not-yet-revoked row and rotate it
        # into a fresh token after this revoke commits.
        active_tokens = session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .with_for_update()
        ).scalars().all()
        now = datetime.now(timezone.utc)
        for t in active_tokens:
            t.revoked_at = now

    session.flush()

    log_audit_event(
        session=session,
        actor_user_id=token.user_id,
        actor_ip=None,
        action="PASSWORD_RESET_COMPLETED",
        subject_type="user",
        subject_id=token.user_id,
        result="SUCCESS",
    )


def _issue_tokens(session: Session, user_id: uuid.UUID, family_id: uuid.UUID) -> IssuedTokens:
    refresh_value = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)

    session.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_refresh_token(refresh_value),
            expires_at=expires_at,
        )
    )
    session.flush()

    return IssuedTokens(
        user_id=user_id,
        access_token=encode_access_token(user_id),
        refresh_token=refresh_value,
        csrf_token=generate_csrf_token(),
        refresh_expires_at=expires_at,
    )


def authenticate(session: Session, email: str, password: str, actor_ip: str | None) -> AuthResult:
    """
    docs/API.md §2.1: login failures never distinguish "wrong email" from
    "wrong password" — both raise InvalidCredentials with one generic message.
    """
    user = session.execute(select(User).where(User.email == email)).scalars().first()

    if user is not None and user.locked_until is not None:
        if user.locked_until > datetime.now(timezone.utc):
            raise AccountLocked()

    if user is None or not verify_password(password, user.password_hash):
        if user is not None:
            user.failed_login_count += 1
            if user.failed_login_count >= FAILED_LOGIN_LOCK_THRESHOLD:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=FAILED_LOGIN_LOCK_MINUTES)
            session.flush()
        log_audit_event(
            session=session,
            actor_user_id=user.id if user is not None else None,
            actor_ip=actor_ip,
            action="USER_LOGIN",
            subject_type="user",
            subject_id=user.id if user is not None else None,
            result="DENIED",
        )
        raise InvalidCredentials()

    user.failed_login_count = 0
    user.locked_until = None
    session.flush()

    tokens = _issue_tokens(session, user.id, family_id=uuid.uuid4())

    log_audit_event(
        session=session,
        actor_user_id=user.id,
        actor_ip=actor_ip,
        action="USER_LOGIN",
        subject_type="user",
        subject_id=user.id,
        result="SUCCESS",
    )

    return AuthResult(
        tokens=tokens,
        email_verified=user.email_verified_at is not None,
        role=summarize_role(session, user),
    )


def refresh_tokens(session: Session, refresh_token_value: str, actor_ip: str | None) -> IssuedTokens:
    """
    Rotates the refresh token. Reuse of an already-revoked token revokes the
    entire family (docs/API.md §2.1, docs/SECURITY.md §5: theft signal).
    """
    # FOR UPDATE pairs with reset_password()'s lock on the same row — without
    # it, a reset committing concurrently could revoke this token right after
    # it's read here as still-active, and this call would rotate it anyway.
    token_hash = hash_refresh_token(refresh_token_value)
    token = session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    ).scalars().first()

    if token is None:
        raise InvalidRefreshToken()

    now = datetime.now(timezone.utc)

    if token.revoked_at is not None or token.expires_at <= now:
        if token.revoked_at is not None:
            family_tokens = session.execute(
                select(RefreshToken).where(
                    RefreshToken.family_id == token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
            ).scalars().all()
            for t in family_tokens:
                t.revoked_at = now
            log_audit_event(
                session=session,
                actor_user_id=token.user_id,
                actor_ip=actor_ip,
                action="REFRESH_TOKEN_REUSE_DETECTED",
                subject_type="user",
                subject_id=token.user_id,
                result="DENIED",
            )
            # The caller (app/api/auth.py) turns InvalidRefreshToken into an
            # HTTPException, which makes get_session's generator dependency
            # roll back the whole request transaction — that would silently
            # undo this family-wide revoke, the one security-critical effect
            # of detecting token reuse. Commit it now, before raising, so it
            # survives regardless of what happens after this point.
            session.commit()
        raise InvalidRefreshToken()

    token.revoked_at = now
    session.flush()

    new_tokens = _issue_tokens(session, token.user_id, family_id=token.family_id)

    log_audit_event(
        session=session,
        actor_user_id=token.user_id,
        actor_ip=actor_ip,
        action="REFRESH_TOKEN_ROTATE",
        subject_type="user",
        subject_id=token.user_id,
        result="SUCCESS",
    )

    return new_tokens


def logout(session: Session, refresh_token_value: str | None, actor_user_id: uuid.UUID, actor_ip: str | None) -> None:
    """Revokes the presented refresh token's family, if any. Idempotent."""
    if refresh_token_value is not None:
        token_hash = hash_refresh_token(refresh_token_value)
        token = session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalars().first()
        if token is not None:
            now = datetime.now(timezone.utc)
            family_tokens = session.execute(
                select(RefreshToken).where(
                    RefreshToken.family_id == token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
            ).scalars().all()
            for t in family_tokens:
                t.revoked_at = now
            session.flush()

    log_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        action="USER_LOGOUT",
        subject_type="user",
        subject_id=actor_user_id,
        result="SUCCESS",
    )
