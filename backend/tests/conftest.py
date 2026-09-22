"""Pytest fixtures and configuration for institution tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import settings
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
    TestClient with dependency overrides for database session.

    Override get_session to use test session. Tests must pass X-Debug-User-Id
    header explicitly to set auth context (app.api.deps.get_current_principal
    reads it from the request).
    """
    # Use injected session fixture to ensure proper fixture ordering
    test_session = session

    def override_get_session():
        """Override get_session to use test session."""
        return test_session

    app.dependency_overrides[get_session] = override_get_session

    test_client = TestClient(app)

    yield test_client

    # Cleanup
    app.dependency_overrides.clear()
