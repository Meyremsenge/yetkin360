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

from sqlalchemy import select, update
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
from app.services.institution import create_institution
from app.services.organization import DuplicateLegalIdError, create_organization, is_free_email_domain
from app.services.outbox import enqueue

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
PASSWORD_RESET_TOKEN_TTL_HOURS = 1

# Resend limits are derived from the tokens table itself (created_at), so they
# hold across processes and restarts and need no in-memory state.
RESEND_VERIFICATION_COOLDOWN_SECONDS = 60
RESEND_VERIFICATION_MAX_PER_HOUR = 5

FAILED_LOGIN_LOCK_THRESHOLD = 10
FAILED_LOGIN_LOCK_MINUTES = 15

# YET-183: Argon2 must run on every register/login branch, otherwise response
# time reveals whether an e-mail is registered. Verifying against this hash
# (made by the real hasher, so same cost parameters) is the stand-in when
# there is no stored hash to check.
_DUMMY_PASSWORD_HASH = hash_password(uuid.uuid4().hex)


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
    """
    if user.is_platform_admin:
        return "PLATFORM_ADMIN"

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


class CorporateEmailRequired(Exception):
    """ORGANIZATION registration attempted with a free e-mail provider address."""


class LegalIdTaken(Exception):
    """ORGANIZATION registration attempted with a legal_id another organization holds."""


def register_user(
    session: Session,
    email: str,
    password: str,
    full_name: str,
    account_kind: str = "TALENT",
    entity_name: str | None = None,
    legal_id: str | None = None,
) -> RegisteredUser:
    """
    Create a user + empty talent profile in one transaction (docs/API.md §2.1:
    registration itself grants no role — role still lives on membership, not
    on User). account_kind only decides whether an Organization/Institution
    is created alongside the user, with the caller as its ADMIN — identical
    to what the caller could already do a moment later via
    POST /organizations or POST /institutions. It is NOT a new trust
    boundary: creating an organization has always been self-service (T1,
    unverified until an admin raises it), and institution creation already
    required no invitation either.

    docs/SECURITY.md §4 senaryo 10: registration must not let an attacker
    enumerate which emails are already registered. If the email is already
    taken, this returns as if registration succeeded (a fake, non-existent
    user_id — never the real one, which would itself leak that the account
    exists) and does not touch the existing row. The real account holder
    is notified via outbox: a duplicate-registration attempt is enqueued to
    the email.duplicate_registration_attempt topic, which the outbox worker
    will process asynchronously without blocking this transaction.
    """
    # An organization account is created from a corporate address, so the
    # verification e-mail below always goes to one. Decided from the request
    # alone (never from whether the account exists) — no enumeration signal.
    if account_kind == "ORGANIZATION" and is_free_email_domain(email.rsplit("@", 1)[-1]):
        raise CorporateEmailRequired()

    # Hash before branching so both paths pay the same Argon2 cost (YET-183).
    password_hash = hash_password(password)

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

    user = User(email=email, password_hash=password_hash)
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

    if account_kind == "ORGANIZATION":
        assert entity_name is not None  # enforced by RegisterRequest validator
        try:
            organization = create_organization(
                name=entity_name,
                domain=None,
                legal_id=legal_id,
                caller_user_id=user.id,
                session=session,
            )
        except DuplicateLegalIdError as exc:
            # Caller (route) turns this into 409; get_session rolls the whole
            # registration back, so no user is left behind without its organization.
            raise LegalIdTaken() from exc
        log_audit_event(
            session=session,
            actor_user_id=user.id,
            actor_ip=None,
            action="CREATE_ORGANIZATION",
            subject_type="organization",
            subject_id=organization.id,
            result="SUCCESS",
            metadata={"name": entity_name, "via": "register"},
        )
    elif account_kind == "INSTITUTION":
        assert entity_name is not None  # enforced by RegisterRequest validator
        institution = create_institution(
            name=entity_name,
            domain=None,
            caller_user_id=user.id,
            session=session,
        )
        log_audit_event(
            session=session,
            actor_user_id=user.id,
            actor_ip=None,
            action="CREATE_INSTITUTION",
            subject_type="institution",
            subject_id=institution.id,
            result="SUCCESS",
            metadata={"name": entity_name, "via": "register"},
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


def resend_email_verification(session: Session, user_id: uuid.UUID, actor_ip: str | None) -> bool:
    """
    Issue a fresh verification token for an authenticated, unverified user
    (docs/API.md §2.1; docs/arsiv/HATA.md IS-08: the 24h token otherwise expires and
    leaves the account unverified for good).

    Returns True when a token was issued. Returns False — a silent no-op for the
    caller, who always answers 204 — when the e-mail is already verified or a
    limit is hit (1/minute, 5/hour, counted from the tokens table, which
    includes the registration token). A silent no-op keeps an attacker from
    flooding the outbox or learning the limit state; the recipient is always
    the account's own address, resolved by the worker from the user id.

    Previous unused tokens are invalidated (used_at) so only the newest link
    works. The user row is locked FOR UPDATE to serialise concurrent resends.
    """
    user = session.execute(
        select(User).where(User.id == user_id).with_for_update()
    ).scalars().first()
    if user is None or user.email_verified_at is not None:
        return False

    now = datetime.now(timezone.utc)
    recent = session.execute(
        select(EmailVerificationToken.created_at)
        .where(EmailVerificationToken.user_id == user_id)
        .where(EmailVerificationToken.created_at > now - timedelta(hours=1))
        .order_by(EmailVerificationToken.created_at.desc())
    ).scalars().all()
    if recent and recent[0] > now - timedelta(seconds=RESEND_VERIFICATION_COOLDOWN_SECONDS):
        return False
    if len(recent) >= RESEND_VERIFICATION_MAX_PER_HOUR:
        return False

    session.execute(
        update(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user_id)
        .where(EmailVerificationToken.used_at.is_(None))
        .values(used_at=now)
    )
    _issue_email_verification_token(session, user_id)

    log_audit_event(
        session=session,
        actor_user_id=user_id,
        actor_ip=actor_ip,
        action="EMAIL_VERIFICATION_RESENT",
        subject_type="user",
        subject_id=user_id,
        result="SUCCESS",
    )
    return True


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

    L-03 (plan.md): status check happens after user lookup but before password
    verification to avoid timing variations that could leak account status.

    AC-3, AC-1, AC-2: failed login counts, locks, and audit events are committed
    before raising exceptions, so they survive the get_session rollback handler.
    """
    user = session.execute(select(User).where(User.email == email)).scalars().first()

    # L-03: Check if user is suspended/deleted immediately after lookup,
    # before password verification. Raise same error as wrong password to
    # prevent enumeration. (AC-5, AC-S2)
    if user is not None and user.status in ('SUSPENDED', 'DELETED'):
        # YET-183: same Argon2 cost as the other rejection paths (result unused).
        verify_password(password, _DUMMY_PASSWORD_HASH)
        log_audit_event(
            session=session,
            actor_user_id=user.id,
            actor_ip=actor_ip,
            action="USER_LOGIN",
            subject_type="user",
            subject_id=user.id,
            result="DENIED",
        )
        session.commit()
        raise InvalidCredentials()

    # If lock has expired, reset the counter proactively before checking password.
    # (AC-4, AC-8)
    if user is not None and user.locked_until is not None:
        if user.locked_until <= datetime.now(timezone.utc):
            # Lock has expired; reset both counter and lock timestamp.
            user.failed_login_count = 0
            user.locked_until = None
            session.flush()
        elif user.locked_until > datetime.now(timezone.utc):
            # Account is still locked. Log DENIED audit before raising to
            # ensure it survives rollback in production (AC-3, AC-S1).
            log_audit_event(
                session=session,
                actor_user_id=user.id,
                actor_ip=actor_ip,
                action="USER_LOGIN",
                subject_type="user",
                subject_id=user.id,
                result="DENIED",
                metadata={"reason": "locked"},
            )
            # Commit this audit and lock state before raising, so the security
            # event (and the fact that the account is locked) persists even if
            # the caller's exception handler rolls back the request transaction.
            # See refresh_tokens()'s similar pattern (REUSE_DETECTED).
            session.commit()
            raise AccountLocked()

    # YET-183: unknown e-mail still pays for one Argon2 verification.
    password_ok = verify_password(
        password, user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    )
    if user is None or not password_ok:
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
        # Commit the failed login count, lock, and audit event before raising
        # the exception. Otherwise, if the caller's exception handler rolls back
        # the transaction (as get_session does), the brute-force protection state
        # is silently undone. (AC-1, AC-2, AC-3, AC-9)
        session.commit()
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

    L-03: Reject refresh if token owner's status is not ACTIVE or PENDING.
    (AC-7)
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

    # L-03 (AC-7): Check token owner's status after verifying token is valid
    # (not revoked or expired). If user is suspended or deleted, deny the refresh.
    user = session.execute(select(User).where(User.id == token.user_id)).scalars().first()
    if user is not None and user.status not in ('ACTIVE', 'PENDING'):
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
        # Only the caller's own family: a foreign token must not let one user
        # kill another user's session.
        if token is not None and token.user_id == actor_user_id:
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
