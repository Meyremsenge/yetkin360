"""
Outbox worker: polling and processing transactional outbox.

Implements AC-2 (select & process), AC-4 (failure handling), AC-5 (max_attempts),
AC-6 (SKIP LOCKED), AC-S2 (logging without payload).

The worker polls the outbox table for unprocessed rows (processed_at IS NULL),
dispatches each to a registered handler based on topic, and marks them as
processed (processed_at = now()) on success. On handler failure, increments
attempts and retries later. Rows exceeding max_attempts are silently skipped.

Uses FOR UPDATE SKIP LOCKED to prevent double-processing in multi-instance
deployments.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outbox import Outbox

logger = logging.getLogger(__name__)


def process_batch(
    session: Session,
    handlers: dict,
    max_attempts: int = 5,
    batch_size: int = 10,
) -> int:
    """
    Process a batch of unprocessed outbox rows.

    Selects up to batch_size rows where processed_at IS NULL and attempts < max_attempts,
    ordered by created_at (FIFO), using FOR UPDATE SKIP LOCKED to prevent double-processing
    in concurrent worker instances.

    For each row, looks up the handler by topic in the handlers dict. If no handler is found,
    the row is skipped silently (remains unprocessed, not counted). If a handler is found and
    succeeds, sets processed_at = now(). If a handler raises an exception, increments attempts
    and logs the error (without payload). Each row is processed and committed independently;
    a handler failure does not affect other rows in the batch.

    Args:
      - session: SQLAlchemy Session (within transaction)
      - handlers: dict mapping topic -> handler callable (args: payload dict, outbox_id int)
      - max_attempts: retry limit; rows with attempts >= max_attempts are not selected
      - batch_size: max rows to process in one batch

    Returns:
      - int: number of rows successfully processed (processed_at set to now())

    Implements AC-2, AC-4, AC-5, AC-6, AC-S2.
    """
    # Select unprocessed rows with FOR UPDATE SKIP LOCKED
    rows = session.execute(
        select(Outbox)
        .where(Outbox.processed_at.is_(None))
        .where(Outbox.attempts < max_attempts)
        .order_by(Outbox.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    processed_count = 0

    for row in rows:
        # Look up handler for this row's topic
        handler = handlers.get(row.topic)
        if handler is None:
            # No handler registered — skip silently (row remains unprocessed)
            continue

        try:
            # Call handler
            handler(row.payload, row.id)
            # On success, mark as processed
            row.processed_at = datetime.now(timezone.utc)
            session.flush()
            session.commit()
            processed_count += 1
        except Exception as e:
            # On failure, increment attempts and log (without payload)
            row.attempts += 1
            session.flush()
            session.commit()
            logger.error(
                f"Outbox handler failed: outbox_id={row.id}, topic={row.topic}, "
                f"error_type={type(e).__name__}, error_message={str(e)}"
            )

    return processed_count


# ============================================================================
# Handler functions (sample implementation for MVP)
# ============================================================================


def email_duplicate_registration_handler(payload: dict, outbox_id: int) -> None:
    """
    Handler for email.duplicate_registration_attempt topic.

    Simulates sending an email to notify the user that someone tried to register
    their email address. MVP implementation: logs to console if EMAIL_BACKEND=console.

    Args:
      - payload: dict with keys like {"user_email": "..."}
      - outbox_id: row ID in outbox table
    """
    from app.core.config import settings

    # For MVP, EMAIL_BACKEND=console means print to console (simulated delivery)
    if settings.email_backend == "console":
        print(
            f"[EMAIL] Duplicate registration attempt email "
            f"(outbox_id={outbox_id})"
        )
        # In production, SMTP backend would actually send email here
        # For now, just succeed (no exception raised)
    elif settings.email_backend == "smtp":
        # TODO: real SMTP delivery (PLAN 1.6)
        pass


# Handler dispatch table (expanded as new topics are introduced)
DEFAULT_HANDLERS = {
    "email.duplicate_registration_attempt": email_duplicate_registration_handler,
}


if __name__ == "__main__":
    """
    Standalone worker entry point for testing.

    Usage:
      python -m app.workers.outbox_worker

    In production, this would be run under systemd/supervisor.
    See final analiz §39 (architecture).
    """
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(settings.database_url)

    with Session(engine) as session:
        count = process_batch(session, DEFAULT_HANDLERS)
        print(f"Processed {count} rows")
