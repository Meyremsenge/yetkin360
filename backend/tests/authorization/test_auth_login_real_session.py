"""
Integration test for POST /auth/login using the REAL get_session dependency
(no override) — i.e. real per-request commit/rollback, not the test
savepoint fixture used by test_auth_endpoints.py.

Why this file exists separately: every test in test_auth_endpoints.py
overrides get_session with the shared `session` fixture from
tests/authorization/conftest.py, which never commits — it only rolls back
the whole transaction at the end of the test. That hides a real class of
bug: any change made inside a request handler that gets flushed but not
committed before an exception is raised will be silently undone by
get_session's `except Exception: session.rollback()` in production, while
looking correct under the overridden fixture (flushed rows are visible
within the same uncommitted transaction all test long).

This exact bug was found here: app/services/auth.py's authenticate()
increments failed_login_count and sets locked_until on invalid credentials,
then raises InvalidCredentials. The API layer turns that into an
HTTPException, which made the real get_session roll back the counter and
lock along with it — the brute-force protection was silently defeated.
Fixed by committing before raising in those branches (see the comment in
auth.py).
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models import AuditEvent, User


def test_login_wrong_password_persists_failed_login_count_through_real_commit_rollback():
    """
    AC-1 / AC-9: Uses the real get_session (no dependency_overrides) so the
    request that increments the counter actually commits and persists in the
    real database, even though the handler's exception makes the request's
    transaction roll back at the HTTP level.

    Deliberately does NOT use the shared `session` fixture from
    tests/authorization/conftest.py: that fixture holds its own connection
    with an outer transaction and a savepoint-mode ORM session, so a
    `commit()` on it only releases the savepoint — it never reaches
    PostgreSQL in a way that app/core/deps.py's separately-pooled engine
    (used by the real get_session) could see. This test needs a genuinely
    separate, really-committed connection to set up and inspect state.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    setup_session = Session()

    email = f"real-session-login-{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("Str0ngPassw0rd!"))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()

    try:
        client = TestClient(app)

        # First attempt: wrong password
        response = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

        # Check in a fresh session (using the real database, not the test
        # savepoint fixture) that the counter was truly persisted
        check_session = Session()
        user_row = check_session.execute(select(User).where(User.id == user_id)).scalars().first()
        assert user_row is not None
        assert user_row.failed_login_count == 1, (
            "failed_login_count should be persisted in the real database "
            "(committed before raising InvalidCredentials), not rolled back "
            "with the HTTP exception."
        )
        check_session.close()

    finally:
        cleanup_session = Session()
        cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
        cleanup_session.commit()
        cleanup_session.close()
        engine.dispose()


def test_login_wrong_password_logs_audit_event_that_survives_rollback():
    """
    AC-3 / AC-9: audit_events entry for DENIED login is committed and
    persisted in the real database, surviving the HTTP exception's rollback.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    setup_session = Session()

    email = f"real-session-audit-{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("Str0ngPassw0rd!"))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()

    try:
        client = TestClient(app)

        # Attempt wrong password
        response = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert response.status_code == 401

        # Check in a fresh session that the DENIED audit was persisted
        check_session = Session()
        audit = check_session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "USER_LOGIN",
                AuditEvent.result == "DENIED",
                AuditEvent.subject_id == user_id,
            )
            .order_by(AuditEvent.created_at.desc())
        ).scalars().first()
        assert audit is not None, (
            "DENIED audit event should be committed and persisted in the real database, "
            "not rolled back with the HTTP exception."
        )
        check_session.close()

    finally:
        cleanup_session = Session()
        cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
        cleanup_session.commit()
        cleanup_session.close()
        engine.dispose()


def test_login_tenth_wrong_password_locks_account_persisted_in_real_db():
    """
    AC-2 / AC-9: 10. wrong password sets locked_until in the real database,
    committed before InvalidCredentials is raised. The lock persists even
    though the HTTP exception rolls back the request transaction.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    setup_session = Session()

    email = f"real-session-lock-{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("Str0ngPassw0rd!"))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()

    try:
        client = TestClient(app)

        # 10 wrong attempts
        for _ in range(10):
            response = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
            assert response.status_code == 401

        # Check in a fresh session that locked_until was set and persisted
        check_session = Session()
        user_row = check_session.execute(select(User).where(User.id == user_id)).scalars().first()
        assert user_row is not None
        assert user_row.locked_until is not None, (
            "locked_until should be persisted in the real database after 10 failed attempts, "
            "not rolled back with the HTTP exception."
        )
        now = datetime.now(timezone.utc)
        assert user_row.locked_until > now, "lock should not already be expired"
        assert user_row.locked_until <= now + timedelta(minutes=20), "lock duration should be ~15 minutes"
        check_session.close()

        # 11. attempt (even with correct password) should return 423
        response = client.post("/auth/login", json={"email": email, "password": "Str0ngPassw0rd!"})
        assert response.status_code == 423
        assert response.json()["code"] == "ACCOUNT_LOCKED"

    finally:
        cleanup_session = Session()
        cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
        cleanup_session.commit()
        cleanup_session.close()
        engine.dispose()


def test_login_locked_account_audit_metadata_clean_no_pii():
    """
    AC-S1 / AC-9: When a locked account attempt is logged, its audit metadata
    is {"reason": "locked"} exactly — no email, password, or other PII.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    setup_session = Session()

    email = f"real-session-pii-{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("Str0ngPassw0rd!"))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()

    try:
        client = TestClient(app)

        # 10 wrong attempts to lock
        for _ in range(10):
            client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})

        # Attempt on locked account
        response = client.post("/auth/login", json={"email": email, "password": "Str0ngPassw0rd!"})
        assert response.status_code == 423

        # Check the DENIED audit for the locked attempt
        check_session = Session()
        audit = check_session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "USER_LOGIN",
                AuditEvent.result == "DENIED",
                AuditEvent.subject_id == user_id,
            )
            .order_by(AuditEvent.created_at.desc())
        ).scalars().first()
        assert audit is not None
        assert audit.event_metadata == {"reason": "locked"}, (
            f"Audit metadata for locked account attempt should be exactly {{'reason': 'locked'}}, "
            f"got {audit.event_metadata}"
        )
        # Double-check: no PII keys in metadata
        if audit.event_metadata:
            for key in ["email", "password", "password_hash", "tc_kimlik_no"]:
                assert key not in audit.event_metadata, f"PII key '{key}' should not be in audit metadata"
        check_session.close()

    finally:
        cleanup_session = Session()
        cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
        cleanup_session.commit()
        cleanup_session.close()
        engine.dispose()
