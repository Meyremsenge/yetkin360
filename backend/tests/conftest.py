"""Pytest fixtures and test-database bootstrap for the backend test suite."""

# ruff: noqa: E402
import os
from pathlib import Path

# CRITICAL: Initialize test database URL BEFORE importing any app.* modules.
# This ensures all engines (app, alembic, workers) use the test DB, not dev DB.
from tests._testdb import resolve_test_database_url, assert_safe_test_url, maintenance_url
from app.core.config import settings

# Derive or override test database URL.
dev_url = settings.database_url
test_url = resolve_test_database_url(dev_url, os.environ.get("TEST_DATABASE_URL"))
assert_safe_test_url(test_url)

# Safety check: refuse to run against a dev DB whose name ends with 'test'.
# This guards against running tests on mytest, prodtest, etc. in local development.
# CI is exempted (os.environ.get("CI") is set).
if dev_url == test_url and dev_url.endswith("test") and not os.environ.get("CI"):
    raise RuntimeError(
        "refusing to run against a dev DB whose name ends with 'test'; "
        "set TEST_DATABASE_URL or rename your dev database"
    )

# Switch all connections to test DB (settings is a singleton; alembic/env.py reads it).
settings.database_url = test_url
os.environ["DATABASE_URL"] = test_url

# Imports must follow the test-DB URL switch, otherwise app engines bind to dev DB.
import pytest
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from alembic.config import Config as AlembicConfig
from alembic import command

from app.api.deps import get_session
from app.core.deps import get_current_user as core_get_current_user
from app.models import TalentProfile, User
from app.main import app


# ============================================================================
# Test database lifecycle: create/upgrade at session start, drop and recreate on the next local run
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    """
    Session-scope fixture: initialize test database.

    For local development (dev_url != test_url):
    - Connect to "postgres" maintenance database
    - Drop test DB if it exists (with FORCE to disconnect stale sessions)
    - Create test DB
    - Apply all migrations via alembic upgrade head

    For CI (dev_url == test_url, already "test"):
    - Skip drop/create (DB name is already "test")
    - Just apply migrations (idempotent)

    Raises:
        RuntimeError: if cannot connect to the test database server.
    """
    # Determine if we need to drop/create (local) or skip (CI)
    is_local = dev_url != test_url

    if is_local:
        # Local: use maintenance database to drop/create test DB
        maint_url = maintenance_url(test_url)
        maint_engine = create_engine(maint_url)
        try:
            with maint_engine.connect() as conn:
                # Use AUTOCOMMIT mode to execute DDL (CREATE/DROP DATABASE)
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                # Extract DB name safely (already verified by assert_safe_test_url)
                test_db_name = make_url(test_url).database
                # Drop if exists (WITH FORCE disconnects stale sessions, PG ≥ 13)
                conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
                conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
        except OperationalError:
            pytest.exit(
                f"Cannot connect to test database server at {make_url(maint_url).host}:{make_url(maint_url).port}; "
                f"start it with: docker compose up -d",
                returncode=2
            )
        finally:
            maint_engine.dispose()

    # Apply migrations (idempotent)
    backend_path = Path(__file__).resolve().parent.parent
    alembic_ini = backend_path / "alembic.ini"
    cfg = AlembicConfig(str(alembic_ini))
    # Ensure script_location is absolute (cwd-independent)
    cfg.set_main_option("sqlalchemy.url", test_url)
    cfg.set_main_option("script_location", str(backend_path / "alembic"))
    command.upgrade(cfg, "head")


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
