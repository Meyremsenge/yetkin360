"""
Test suite for verifying that the test client's session handling mirrors
production get_session semantics: commit on success, rollback on exception.

These tests ensure that "write then raise" patterns are caught by the test
suite, preventing silent failures in production where uncommitted writes
are discarded.

References:
- YET-218: fixture must replicate production commit/rollback
- app/core/deps.py:20-29: production get_session behavior
- backend/tests/_testdb.py: session_override (test get_session override)
"""

import uuid

import pytest
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.main import app
from app.models import User


class EmailBody(BaseModel):
    """Request body containing email."""
    email: str


# ============================================================================
# Test-only API router with write-then-raise scenarios
# ============================================================================

probe_router = APIRouter(prefix="/__test__")


@probe_router.post("/write-then-raise")
def write_then_raise(body: EmailBody, session: Session = Depends(get_session)):
    """
    Write a User, flush it, then raise HTTPException.
    Exception is raised BEFORE any commit, so the write should rollback
    in production and in the test client.
    """
    user = User(email=body.email, password_hash="x")
    session.add(user)
    session.flush()
    raise HTTPException(status_code=409, detail="Conflict")


@probe_router.post("/commit-then-raise")
def commit_then_raise(body: EmailBody, session: Session = Depends(get_session)):
    """
    Write a User, flush it, then explicitly commit before raising.
    The commit() should persist the write; the exception is raised after.
    """
    user = User(email=body.email, password_hash="x")
    session.add(user)
    session.flush()
    session.commit()
    raise HTTPException(status_code=409, detail="Conflict")


@probe_router.post("/write-ok")
def write_ok(body: EmailBody, session: Session = Depends(get_session)):
    """
    Write a User without raising. The write should commit normally.
    """
    user = User(email=body.email, password_hash="x")
    session.add(user)
    session.flush()
    return {"ok": True}


# ============================================================================
# Fixtures: setup and teardown of test-only routes
# ============================================================================

@pytest.fixture(scope="module")
def setup_test_routes():
    """
    Module-scope fixture: attach test router to app before tests run,
    remove it after all tests complete.

    Records the number of routes before attachment, then restores
    app.router.routes to that count.
    """
    initial_route_count = len(app.router.routes)
    app.include_router(probe_router)
    yield
    # Restore: trim routes to initial count
    app.router.routes = app.router.routes[:initial_route_count]


# ============================================================================
# Tests: rollback semantics
# ============================================================================

def test_uncommitted_write_is_rolled_back_when_request_raises(client, session, setup_test_routes):
    """
    AC-1: When an endpoint raises an exception, uncommitted writes rollback.

    POST /__test__/write-then-raise returns 409; the User written inside
    the request handler is NOT committed. Test session query should find
    no such user, matching production behavior.
    """
    email = f"test-{uuid.uuid4()}@example.com"

    # Make request: should get 409
    response = client.post("/__test__/write-then-raise", json={"email": email})
    assert response.status_code == 409

    # Query test session: user should not exist (write was rolled back)
    stmt = select(User).where(User.email == email)
    result = session.execute(stmt).scalars().first()
    assert result is None, "Uncommitted write should be rolled back"


def test_write_committed_before_raise_survives_rollback(client, session, setup_test_routes):
    """
    AC-1: Writes that are explicitly committed before the exception survive.

    POST /__test__/commit-then-raise commits the User inside the handler,
    then raises. The User should persist despite the exception.
    """
    email = f"test-{uuid.uuid4()}@example.com"

    # Make request: should get 409
    response = client.post("/__test__/commit-then-raise", json={"email": email})
    assert response.status_code == 409

    # Query test session: user should exist (was committed before exception)
    stmt = select(User).where(User.email == email)
    result = session.execute(stmt).scalars().first()
    assert result is not None, "Committed write should survive exception"
    assert result.email == email


def test_successful_request_commits(client, session, setup_test_routes):
    """
    AC-2: When a request succeeds, writes are committed.

    POST /__test__/write-ok succeeds without exception. The User should
    be visible in the test session afterward.
    """
    email = f"test-{uuid.uuid4()}@example.com"

    # Make request: should get 200
    response = client.post("/__test__/write-ok", json={"email": email})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Query test session: user should exist (write was committed)
    stmt = select(User).where(User.email == email)
    result = session.execute(stmt).scalars().first()
    assert result is not None, "Successful request should commit writes"
    assert result.email == email


def test_fixture_data_survives_request_rollback(client, session, user_talent_a, setup_test_routes):
    """
    AC-5: Test fixture data (flush-only, no commit) survives request rollback.

    When a request raises and causes rollback, only the request's writes
    are rolled back. Fixture data from test setup persists because it was
    established within the same transaction before the request.

    This validates that rollback is request-scoped, not fixture-scoped.
    """
    # user_talent_a is set up by fixture (flush only, no commit)
    fixture_user_id = user_talent_a.id

    # Make failing request (will cause rollback of request's writes)
    email = f"test-{uuid.uuid4()}@example.com"
    response = client.post("/__test__/write-then-raise", json={"email": email})
    assert response.status_code == 409

    # Query for fixture user: should still exist
    fixture_user = session.get(User, fixture_user_id)
    assert fixture_user is not None, "Fixture data should survive request rollback"
    assert fixture_user.email == "talent-a@example.com"


def test_nothing_changed_on_failure_is_not_silent_success(client, session, setup_test_routes):
    """
    AC-3: Failed requests return error status, not silent success.

    When /__test__/write-then-raise raises, the response must be 409,
    not 200. This prevents silently accepting a write failure as success.
    """
    email = f"test-{uuid.uuid4()}@example.com"

    response = client.post("/__test__/write-then-raise", json={"email": email})

    # Must be failure status, not 200
    assert response.status_code == 409, "Failed request must return error status"

    # Response body must not contain success flag
    body = response.json()
    assert body.get("ok") is not True, "Failed response must not contain success marker"

    # Verify user does not exist in database (write was rolled back)
    stmt = select(User).where(User.email == email)
    result = session.execute(stmt).scalars().first()
    assert result is None, "User should not exist in database after failed request"
