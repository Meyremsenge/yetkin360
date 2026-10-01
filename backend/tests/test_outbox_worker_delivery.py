"""
YET-209 (OPS-01): the outbox worker never ran as a loop, and handler-less rows
at the head of the queue were re-selected forever, starving everything behind
them (dev DB: verify_email rows were never delivered).

Every test here uses a genuinely committed session (the shared `session`
fixture never commits and would hide transaction-boundary bugs). Each test
owns a unique topic and deletes its rows afterwards, and passes its own
handlers dict, so it never touches rows from other tests.
"""

import logging
import smtplib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.outbox import Outbox
from app.workers.outbox_worker import process_batch, run_forever


@pytest.fixture
def db():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    topics: list[str] = []

    class Ctx:
        engine_ = engine
        session_factory = Session

        @staticmethod
        def topic() -> str:
            t = f"test.yet209.{uuid.uuid4()}"
            topics.append(t)
            return t

        @staticmethod
        def add(topic: str, payload: dict | None = None, **kwargs) -> int:
            s = Session()
            row = Outbox(topic=topic, payload=payload or {"k": "v"}, **kwargs)
            s.add(row)
            s.commit()
            row_id = row.id
            s.close()
            return row_id

        @staticmethod
        def get(row_id: int) -> Outbox:
            s = Session()
            try:
                row = s.execute(select(Outbox).where(Outbox.id == row_id)).scalar_one()
                s.expunge(row)
                return row
            finally:
                s.close()

    yield Ctx

    cleanup = Session()
    for t in topics:
        cleanup.execute(Outbox.__table__.delete().where(Outbox.topic == t))
    cleanup.commit()
    cleanup.close()
    engine.dispose()


def _run(db, handlers, **kwargs) -> int:
    s = db.session_factory()
    try:
        return process_batch(s, handlers, **kwargs)
    finally:
        s.close()


def test_handlerless_rows_at_queue_head_do_not_starve_deliverable_rows(db):
    orphan_topic = db.topic()
    live_topic = db.topic()
    orphan_ids = [db.add(orphan_topic) for _ in range(12)]  # older than the live row, > batch_size
    live_id = db.add(live_topic)

    delivered = _run(db, {live_topic: lambda payload, outbox_id: None}, batch_size=10)

    assert delivered == 1
    assert db.get(live_id).processed_at is not None
    # Handler-less rows are left exactly as they were: waiting, not burned.
    for orphan_id in orphan_ids:
        orphan = db.get(orphan_id)
        assert orphan.processed_at is None
        assert orphan.attempts == 0
        assert orphan.next_attempt_at is None


def test_success_redacts_payload_and_clears_lease(db):
    topic = db.topic()
    row_id = db.add(topic, {"raw_token": "secret-token-value"})

    assert _run(db, {topic: lambda payload, outbox_id: None}) == 1

    row = db.get(row_id)
    assert row.processed_at is not None
    assert row.payload == {}
    assert row.next_attempt_at is None


def test_failed_row_backs_off_and_is_not_retried_until_due(db):
    topic = db.topic()
    row_id = db.add(topic)
    calls: list[int] = []

    def failing(payload, outbox_id):
        calls.append(outbox_id)
        raise RuntimeError("boom")

    before = datetime.now(timezone.utc)
    assert _run(db, {topic: failing}, backoff_base_seconds=60) == 0
    row = db.get(row_id)
    assert row.attempts == 1
    assert row.processed_at is None
    assert row.next_attempt_at is not None
    assert row.next_attempt_at >= before + timedelta(seconds=59)

    # Not due yet: a second pass must not call the handler again.
    _run(db, {topic: failing}, backoff_base_seconds=60)
    assert calls == [row_id]
    assert db.get(row_id).attempts == 1

    # Make it due: now it is retried, and the delay doubles.
    s = db.session_factory()
    s.execute(
        text("UPDATE outbox SET next_attempt_at = now() - interval '1 second' WHERE id = :i"),
        {"i": row_id},
    )
    s.commit()
    s.close()
    before_second = datetime.now(timezone.utc)
    _run(db, {topic: failing}, backoff_base_seconds=60)
    assert calls == [row_id, row_id]
    row = db.get(row_id)
    assert row.attempts == 2
    assert row.next_attempt_at >= before_second + timedelta(seconds=119)


def test_row_reaching_max_attempts_is_dead_lettered(db, caplog):
    topic = db.topic()
    row_id = db.add(topic, attempts=2)
    calls: list[int] = []

    def failing(payload, outbox_id):
        calls.append(outbox_id)
        raise RuntimeError("boom")

    with caplog.at_level(logging.WARNING, logger="app.workers.outbox_worker"):
        _run(db, {topic: failing}, max_attempts=3, backoff_base_seconds=0)
    assert db.get(row_id).attempts == 3
    assert "dead-lettered" in caplog.text

    _run(db, {topic: failing}, max_attempts=3, backoff_base_seconds=0)
    assert calls == [row_id]
    row = db.get(row_id)
    assert row.attempts == 3
    assert row.processed_at is None  # kept for inspection, never silently dropped


def test_handler_runs_outside_any_transaction_with_claim_committed(db):
    """No network call inside an open transaction: while the handler runs, the
    claim must already be committed (visible to another connection) and the row
    lock released."""
    topic = db.topic()
    row_id = db.add(topic)
    observed: dict = {}

    def handler(payload, outbox_id):
        other = db.session_factory()
        try:
            # NOWAIT raises immediately if the worker still holds the row lock.
            observed["locked_row"] = other.execute(
                text("SELECT id FROM outbox WHERE id = :i FOR UPDATE NOWAIT"), {"i": outbox_id}
            ).scalar_one()
            observed["lease"] = other.execute(
                text("SELECT next_attempt_at FROM outbox WHERE id = :i"), {"i": outbox_id}
            ).scalar_one()
        finally:
            other.rollback()
            other.close()

    assert _run(db, {topic: handler}, lease_seconds=300) == 1
    assert observed["locked_row"] == row_id
    assert observed["lease"] is not None
    assert observed["lease"] > datetime.now(timezone.utc) + timedelta(seconds=250)


def test_second_worker_does_not_take_a_row_leased_by_a_running_handler(db):
    topic = db.topic()
    row_id = db.add(topic)
    second_worker_results: list[int] = []
    second_calls: list[int] = []

    def slow_handler(payload, outbox_id):
        second_worker_results.append(
            _run(db, {topic: lambda p, i: second_calls.append(i)})
        )

    assert _run(db, {topic: slow_handler}) == 1
    assert second_worker_results == [0]
    assert second_calls == []
    assert db.get(row_id).processed_at is not None


def test_failure_log_never_contains_exception_message_or_payload(db, caplog):
    topic = db.topic()
    db.add(topic, {"raw_token": "tok-should-not-leak"})

    def failing(payload, outbox_id):
        raise smtplib.SMTPRecipientsRefused({"victim@example.com": (550, b"no such user")})

    with caplog.at_level(logging.INFO):
        _run(db, {topic: failing})

    assert "SMTPRecipientsRefused" in caplog.text
    assert "victim@example.com" not in caplog.text
    assert "tok-should-not-leak" not in caplog.text


def test_run_forever_loops_and_drains_backlog_across_passes(db):
    topic = db.topic()
    ids = [db.add(topic) for _ in range(3)]
    seen: list[int] = []

    run_forever(
        db.engine_,
        {topic: lambda payload, outbox_id: seen.append(outbox_id)},
        poll_interval_seconds=0,
        max_attempts=5,
        backoff_base_seconds=0,
        max_iterations=3,
    )

    assert sorted(seen) == sorted(ids)
    assert all(db.get(i).processed_at is not None for i in ids)


def test_run_forever_survives_database_errors_without_leaking_connection_details(caplog):
    bad_engine = create_engine("postgresql+psycopg://leaky_user:leaky_pw@127.0.0.1:1/nodb?connect_timeout=1")

    with caplog.at_level(logging.ERROR, logger="app.workers.outbox_worker"):
        run_forever(
            bad_engine,
            {"x": lambda p, i: None},
            poll_interval_seconds=0,
            max_attempts=5,
            backoff_base_seconds=0,
            max_iterations=2,
        )

    assert caplog.text.count("Outbox worker pass failed") == 2
    assert "OperationalError" in caplog.text
    assert "leaky_pw" not in caplog.text
    assert "leaky_user" not in caplog.text
    bad_engine.dispose()
