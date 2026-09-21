"""
Test suite for audit events (yet-2-yetkilendirme-cekirdegi).

Tests the AuditEvent model, log_audit_event() helper, and immutability trigger.
Implements AC-4 and AC-S3, AC-S6 from atdd.md.

Strategy: Integration tests using real Postgres.
Fixture pattern copied from test_migration.py.
"""

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditEvent
from app.services.audit import log_audit_event

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
# AC-4: audit_events table — INSERT row with correct fields
# ============================================================================


def test_log_audit_event_inserts_row(session):
    """AC-4: log_audit_event() inserts a row with correct fields."""
    actor_user_id = "550e8400-e29b-41d4-a716-446655440000"
    action = "USER_LOGIN"
    subject_type = "user"
    subject_id = "550e8400-e29b-41d4-a716-446655440001"
    result = "SUCCESS"

    # Call log_audit_event
    log_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        actor_ip=None,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        result=result,
        metadata={"login_method": "password"},
    )

    # Query audit_events table. Filtered by subject_id too, not just action:
    # action="USER_LOGIN" is also emitted by the real app/services/auth.py
    # login flow, so other tests/integration runs against this same
    # database can add further USER_LOGIN rows (audit_events is append-only,
    # they are never cleaned up). This test's fixed subject_id is specific
    # enough to stay unique.
    audit_row = session.execute(
        select(AuditEvent).filter_by(action=action, subject_id=subject_id)
    ).scalar_one_or_none()

    assert audit_row is not None
    assert str(audit_row.actor_user_id) == actor_user_id
    assert audit_row.action == action
    assert audit_row.subject_type == subject_type
    assert str(audit_row.subject_id) == subject_id
    assert audit_row.result == result
    assert audit_row.event_metadata == {"login_method": "password"}


def test_log_audit_event_with_ip_address(session):
    """AC-4: log_audit_event() stores actor_ip when provided."""
    actor_ip = "192.168.1.1"
    action = "RESOURCE_ACCESS"

    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=actor_ip,
        action=action,
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata={},
    )

    audit_row = session.execute(
        select(AuditEvent).filter_by(action=action)
    ).scalar_one_or_none()

    assert audit_row is not None
    assert str(audit_row.actor_ip) == actor_ip


def test_log_audit_event_result_denied(session):
    """AC-4: log_audit_event() accepts 'DENIED' as result."""
    action = "UNAUTHORIZED_ACCESS"
    result = "DENIED"

    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action=action,
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result=result,
        metadata={"reason": "insufficient_permissions"},
    )

    audit_row = session.execute(
        select(AuditEvent).filter_by(action=action)
    ).scalar_one_or_none()

    assert audit_row is not None
    assert audit_row.result == "DENIED"


def test_log_audit_event_result_error(session):
    """AC-4: log_audit_event() accepts 'ERROR' as result."""
    action = "SYSTEM_ERROR"
    result = "ERROR"

    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action=action,
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result=result,
        metadata={"error": "database_connection_failed"},
    )

    audit_row = session.execute(
        select(AuditEvent).filter_by(action=action)
    ).scalar_one_or_none()

    assert audit_row is not None
    assert audit_row.result == "ERROR"


def test_log_audit_event_invalid_result_raises_integrity_error(session):
    """AC-4: log_audit_event() with invalid result value fails (DB CHECK constraint)."""
    with pytest.raises(IntegrityError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_ACTION",
            subject_type="resource",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="INVALID_RESULT",  # Not in (SUCCESS, DENIED, ERROR)
            metadata={},
        )
        session.commit()


def test_log_audit_event_with_metadata(session):
    """AC-4: log_audit_event() stores metadata JSON."""
    metadata = {
        "user_agent": "Mozilla/5.0",
        "request_id": "req-123",
        "duration_ms": 150,
    }

    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="API_CALL",
        subject_type="api_endpoint",
        subject_id="550e8400-e29b-41d4-a716-446655440099",
        result="SUCCESS",
        metadata=metadata,
    )

    audit_row = session.execute(
        select(AuditEvent).filter_by(action="API_CALL")
    ).scalar_one_or_none()

    assert audit_row is not None
    assert audit_row.event_metadata == metadata


# ============================================================================
# AC-S3: audit_events immutability — BEFORE UPDATE OR DELETE trigger
# ============================================================================


def test_audit_event_update_blocked_by_trigger_orm(session):
    """AC-S3: UPDATE via SQLAlchemy ORM is blocked by database trigger."""
    # Insert an audit event
    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="TEST_IMMUTABLE",
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata={"original": True},
    )
    session.commit()

    # Retrieve the audit event
    audit_row = session.execute(
        select(AuditEvent).filter_by(action="TEST_IMMUTABLE")
    ).scalar_one()

    # Try to update it via ORM
    audit_row.event_metadata = {"modified": True}
    with pytest.raises(IntegrityError):
        session.commit()


def test_audit_event_delete_blocked_by_trigger_orm(session):
    """AC-S3: DELETE via SQLAlchemy ORM is blocked by database trigger."""
    # Insert an audit event
    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="TEST_DELETE_PROTECTED",
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata={},
    )
    session.commit()

    # Retrieve the audit event
    audit_row = session.execute(
        select(AuditEvent).filter_by(action="TEST_DELETE_PROTECTED")
    ).scalar_one()

    # Try to delete it via ORM
    session.delete(audit_row)
    with pytest.raises(IntegrityError):
        session.commit()


def test_audit_event_update_blocked_by_trigger_raw_sql(session):
    """AC-S3: UPDATE via raw SQL is blocked by database trigger."""
    # Insert an audit event
    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="TEST_RAW_UPDATE",
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata={},
    )
    session.commit()

    # Get the audit event ID
    audit_row = session.execute(
        select(AuditEvent).filter_by(action="TEST_RAW_UPDATE")
    ).scalar_one()

    # Try to update via raw SQL
    with pytest.raises(IntegrityError):
        session.execute(
            text("UPDATE audit_events SET metadata = :metadata WHERE id = :id"),
            {"metadata": '{"hacked": true}', "id": str(audit_row.id)},
        )
        session.commit()


def test_audit_event_delete_blocked_by_trigger_raw_sql(session):
    """AC-S3: DELETE via raw SQL is blocked by database trigger."""
    # Insert an audit event
    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="TEST_RAW_DELETE",
        subject_type="resource",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata={},
    )
    session.commit()

    # Get the audit event ID
    audit_row = session.execute(
        select(AuditEvent).filter_by(action="TEST_RAW_DELETE")
    ).scalar_one()

    # Try to delete via raw SQL
    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": str(audit_row.id)},
        )
        session.commit()


# ============================================================================
# AC-S6: log_audit_event() PII guard — reject sensitive keywords
# ============================================================================


def test_log_audit_event_rejects_password_in_metadata(session):
    """AC-S6: log_audit_event() rejects 'password' key in metadata."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_PASSWORD",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={"password": "secret123"},
        )


def test_log_audit_event_rejects_password_hash_in_metadata(session):
    """AC-S6: log_audit_event() rejects 'password_hash' key in metadata."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_PASSWORD_HASH",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={"password_hash": "bcrypt$2b$12$..."},
        )


def test_log_audit_event_rejects_email_in_metadata(session):
    """AC-S6: log_audit_event() rejects 'email' key in metadata."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_EMAIL",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={"email": "user@example.com"},
        )


def test_log_audit_event_rejects_tc_kimlik_no_in_metadata(session):
    """AC-S6: log_audit_event() rejects 'tc_kimlik_no' key in metadata."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_TC",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={"tc_kimlik_no": "12345678901"},
        )


def test_log_audit_event_accepts_safe_metadata(session):
    """AC-S6: log_audit_event() accepts safe metadata keys."""
    safe_metadata = {
        "user_agent": "Mozilla/5.0",
        "ip_address": "192.168.1.1",
        "action_details": "Updated profile",
        "result_code": 200,
    }

    log_audit_event(
        session=session,
        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
        actor_ip=None,
        action="TEST_SAFE",
        subject_type="user",
        subject_id="550e8400-e29b-41d4-a716-446655440001",
        result="SUCCESS",
        metadata=safe_metadata,
    )

    audit_row = session.execute(
        select(AuditEvent).filter_by(action="TEST_SAFE")
    ).scalar_one_or_none()

    assert audit_row is not None
    assert audit_row.event_metadata == safe_metadata


def test_log_audit_event_rejects_multiple_sensitive_keys(session):
    """AC-S6: log_audit_event() rejects when multiple sensitive keys are present."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_MULTIPLE_SENSITIVE",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={
                "password": "secret",
                "email": "user@example.com",
                "safe_key": "value",
            },
        )


def test_log_audit_event_nested_metadata_with_sensitive_keys(session):
    """AC-S6: log_audit_event() checks nested metadata for sensitive keys."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_NESTED",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={
                "user_info": {
                    "name": "John",
                    "password": "secret123",  # Sensitive key in nested dict
                }
            },
        )


def test_log_audit_event_case_insensitive_pii_check(session):
    """AC-S6: log_audit_event() checks for sensitive keys case-insensitively."""
    with pytest.raises(ValueError):
        log_audit_event(
            session=session,
            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
            actor_ip=None,
            action="TEST_CASE",
            subject_type="user",
            subject_id="550e8400-e29b-41d4-a716-446655440001",
            result="SUCCESS",
            metadata={"Password": "secret123"},  # Capital P
        )


# ============================================================================
# Additional: audit_events table existence and structure
# ============================================================================


def test_audit_events_table_exists(session):
    """Verify audit_events table exists in the database."""
    result = session.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'audit_events'
            )
        """)
    ).scalar()
    assert result is True


def test_audit_events_has_required_columns(session):
    """Verify audit_events table has all required columns."""
    result = session.execute(
        text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'audit_events'
            ORDER BY ordinal_position
        """)
    ).scalars().all()

    required_columns = {
        "id",
        "actor_user_id",
        "actor_ip",
        "action",
        "subject_type",
        "subject_id",
        "result",
        "metadata",
        "created_at",
    }

    assert required_columns.issubset(set(result))


def test_audit_events_result_check_constraint(session):
    """Verify audit_events result CHECK constraint rejects invalid values."""
    with pytest.raises(IntegrityError):
        session.execute(
            text("""
                INSERT INTO audit_events
                (actor_user_id, action, subject_type, subject_id, result)
                VALUES (:uid, :action, :stype, :sid, :result)
            """),
            {
                "uid": "550e8400-e29b-41d4-a716-446655440000",
                "action": "TEST",
                "stype": "resource",
                "sid": "550e8400-e29b-41d4-a716-446655440001",
                "result": "INVALID",
            },
        )
        session.commit()
