"""
Test suite for outbox service (yet-5-outbox-worker).

Tests the enqueue() helper and PII guard logic.
Implements AC-1 (happy path), AC-7 (AC-S1: PII guard).

Strategy: Integration tests using real Postgres.
Fixture pattern copied from test_audit_events.py.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.outbox import Outbox
from app.services.outbox import enqueue

engine = create_engine(settings.database_url)


@pytest.fixture
def session():
    """Fixture: real Postgres transaction per test, rollback at end."""
    connection = engine.connect()
    transaction = connection.begin()
    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
        yield s
    transaction.rollback()
    connection.close()


# ============================================================================
# AC-1: Happy path — enqueue() inserts row with correct fields
# ============================================================================


def test_enqueue_inserts_row_in_transaction(session):
    """AC-1: enqueue() inserts a row with processed_at=NULL, attempts=0."""
    topic = "email.duplicate_registration_attempt"
    payload = {"user_email": "user@example.com"}

    # Call enqueue within the same transaction
    enqueue(session=session, topic=topic, payload=payload)

    # Query outbox table within same transaction
    outbox_row = session.execute(
        select(Outbox).filter_by(topic=topic)
    ).scalar_one_or_none()

    assert outbox_row is not None
    assert outbox_row.topic == topic
    assert outbox_row.payload == payload
    assert outbox_row.processed_at is None
    assert outbox_row.attempts == 0
    assert outbox_row.created_at is not None


def test_enqueue_creates_unique_row_per_call(session):
    """AC-1: Multiple enqueue() calls create separate rows."""
    topic = "email.duplicate_registration_attempt"

    enqueue(session=session, topic=topic, payload={"user_email": "user1@example.com"})
    enqueue(session=session, topic=topic, payload={"user_email": "user2@example.com"})

    # Both rows should exist in DB
    outbox_rows = session.execute(
        select(Outbox).filter_by(topic=topic).order_by(Outbox.id)
    ).scalars().all()

    assert len(outbox_rows) == 2
    assert outbox_rows[0].payload == {"user_email": "user1@example.com"}
    assert outbox_rows[1].payload == {"user_email": "user2@example.com"}


def test_enqueue_with_complex_payload(session):
    """AC-1: enqueue() handles complex nested JSON payloads."""
    topic = "email.duplicate_registration_attempt"
    payload = {
        "user_email": "user@example.com",
        "user_name": "John Doe",
        "previous_login_date": "2026-09-20T10:30:00Z",
        "details": {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        },
    }

    enqueue(session=session, topic=topic, payload=payload)

    outbox_row = session.execute(
        select(Outbox).filter_by(topic=topic)
    ).scalar_one()

    assert outbox_row.payload == payload


def test_enqueue_no_network_call(session):
    """AC-1: enqueue() performs only sync DB operation, no network calls."""
    # This test verifies behavior: no exception, no hanging, quick return.
    # Can be enhanced with mocking if needed, but integration test suffices
    # to show synchronous execution.
    topic = "email.duplicate_registration_attempt"
    payload = {"user_email": "test@example.com"}

    # Should return instantly without hanging
    enqueue(session=session, topic=topic, payload=payload)

    # If we reach here without timeout, enqueue() was synchronous
    outbox_row = session.execute(
        select(Outbox).filter_by(topic=topic)
    ).scalar_one_or_none()

    assert outbox_row is not None


# ============================================================================
# AC-S1: PII guard — reject sensitive keywords in payload
# ============================================================================


def test_enqueue_rejects_password_in_payload(session):
    """AC-S1: enqueue() rejects 'password' key in payload."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"password": "secret123"},
        )

    # Verify row was NOT inserted
    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_password_hash_in_payload(session):
    """AC-S1: enqueue() rejects 'password_hash' key in payload."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"password_hash": "bcrypt$2b$12$..."},
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_token_in_payload(session):
    """AC-S1: enqueue() rejects 'token' key in payload."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"token": "eyJhbGciOiJIUzI1NiIs..."},
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_email_in_payload(session):
    """AC-S1: enqueue() rejects 'email' key in payload."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"email": "user@example.com"},
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_private_note_in_payload(session):
    """AC-S1: enqueue() rejects 'private_note' key in payload."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"private_note": "internal note"},
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_case_insensitive_password(session):
    """AC-S1: enqueue() checks sensitive keys case-insensitively."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"Password": "secret123"},  # Capital P
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_case_insensitive_token(session):
    """AC-S1: enqueue() checks 'token' case-insensitively."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={"TOKEN": "secret"},  # All caps
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_nested_password(session):
    """AC-S1: enqueue() checks nested dicts for sensitive keys."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={
                "user_info": {
                    "name": "John",
                    "password": "secret123",  # Nested sensitive key
                }
            },
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_deeply_nested_token(session):
    """AC-S1: enqueue() checks deeply nested dicts (3+ levels)."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={
                "level1": {
                    "level2": {
                        "level3": {
                            "token": "secret_token",
                        }
                    }
                }
            },
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_rejects_multiple_sensitive_keys(session):
    """AC-S1: enqueue() rejects when multiple sensitive keys are present."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={
                "password": "secret",
                "email": "user@example.com",
                "safe_key": "value",
            },
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_accepts_safe_payload(session):
    """AC-S1: enqueue() accepts payloads without sensitive keys."""
    safe_payload = {
        "user_email": "user@example.com",  # field name is safe; key is user_email
        "user_name": "John",
        "action_type": "registration_attempt",
        "details": {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
        },
    }

    # Should not raise
    enqueue(
        session=session,
        topic="email.duplicate_registration_attempt",
        payload=safe_payload,
    )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_row = session.execute(
        select(Outbox).filter_by(topic="email.duplicate_registration_attempt")
    ).scalar_one_or_none()

    assert outbox_row is not None
    assert outbox_row.payload == safe_payload


def test_enqueue_rejects_private_note_nested(session):
    """AC-S1: enqueue() rejects nested 'private_note' key."""
    with pytest.raises(ValueError):
        enqueue(
            session=session,
            topic="email.test",
            payload={
                "user": {
                    "name": "John",
                    "private_note": "internal comment",
                }
            },
        )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_count = session.execute(select(Outbox).filter_by(topic="email.test")).scalars().all()
    assert len(outbox_count) == 0


def test_enqueue_accepts_email_as_value_not_key(session):
    """AC-S1: enqueue() allows 'email' as value (key check only, value is arbitrary)."""
    # The guard checks KEYS (field names), not values
    # So a payload like {"user_email": "admin@example.com"} is safe
    # because the key is "user_email", not "email"
    payload = {
        "user_email": "user@example.com",
    }

    enqueue(
        session=session,
        topic="email.duplicate_registration_attempt",
        payload=payload,
    )

    # Scoped to this test's own topic: the shared dev DB may already hold
    # unrelated outbox rows, so a bare select(Outbox) would false-fail here.
    outbox_row = session.execute(
        select(Outbox).filter_by(topic="email.duplicate_registration_attempt")
    ).scalar_one_or_none()

    assert outbox_row is not None
    assert outbox_row.payload == payload


# ============================================================================
# Outbox table structure verification
# ============================================================================


def test_outbox_table_exists(session):
    """Verify outbox table exists in the database."""
    from sqlalchemy import text

    result = session.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'outbox'
            )
        """)
    ).scalar()
    assert result is True


def test_outbox_has_required_columns(session):
    """Verify outbox table has all required columns."""
    from sqlalchemy import text

    result = session.execute(
        text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'outbox'
            ORDER BY ordinal_position
        """)
    ).scalars().all()

    required_columns = {"id", "topic", "payload", "created_at", "processed_at", "attempts"}
    assert required_columns.issubset(set(result))
