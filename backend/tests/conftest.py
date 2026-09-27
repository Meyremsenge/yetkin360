"""Pytest fixtures and configuration for institution tests."""

import pytest
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import settings
from app.core.deps import get_current_user as core_get_current_user
from app.models import TalentProfile, User
from app.main import app


@pytest.fixture
def session():
    """Fixture: real Postgres transaction per test, rollback at end.

    Provides isolated test database session with savepoint support.
    """
    engine = create_engine(settings.database_url)
    connection = engine.connect()
    transaction = connection.begin()
    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
        yield s
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def client(request, session):
    """
    TestClient with dependency overrides for database session and authentication.

    Overrides:
    1. get_session to use test session (isolated transaction per test)
    2. get_current_user to read X-Debug-User-Id header for tests (no real JWT needed)

    Tests pass X-Debug-User-Id header explicitly to set auth context.
    """
    # Use injected session fixture to ensure proper fixture ordering
    test_session = session

    def override_get_session():
        """Override get_session to use test session."""
        return test_session

    def override_get_current_user(x_debug_user_id: str | None = Header(default=None)):
        """
        Test-only override: read X-Debug-User-Id header instead of JWT cookie.

        This allows tests to pass a user_id via header without needing real
        JWT auth. In production, get_current_user uses real JWT validation.
        """
        if not x_debug_user_id:
            raise HTTPException(status_code=401, detail="Missing X-Debug-User-Id header")

        try:
            # Query test session to find user by ID
            user = test_session.query(User).filter_by(id=x_debug_user_id).first()
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid X-Debug-User-Id")

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[core_get_current_user] = override_get_current_user

    test_client = TestClient(app)
    # require_csrf checks csrf_token cookie == X-CSRF-Token header (double-submit).
    # Set both by default so authorization tests don't need to wire CSRF per call —
    # a test that specifically exercises CSRF_FAILED overrides headers/cookies itself.
    test_client.cookies.set("csrf_token", "test-csrf-token")
    test_client.headers.update({"X-CSRF-Token": "test-csrf-token"})

    yield test_client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Talent profile fixtures (shared with authorization tests)
# ============================================================================


@pytest.fixture
def user_talent_a(session):
    """User who owns talent profile A."""
    user = User(email="talent-a@example.com", password_hash="hash_talent_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_b(session):
    """User who owns talent profile B."""
    user = User(email="talent-b@example.com", password_hash="hash_talent_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    """Talent profile A (belongs to user_talent_a)."""
    profile = TalentProfile(
        user_id=user_talent_a.id,
        full_name="Test Talent A",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, user_talent_b):
    """Talent profile B (belongs to user_talent_b)."""
    profile = TalentProfile(
        user_id=user_talent_b.id,
        full_name="Test Talent B",
        visibility="PRIVATE"
    )
    session.add(profile)
    session.flush()
    return profile
