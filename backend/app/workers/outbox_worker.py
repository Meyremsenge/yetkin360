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
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

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


def _send_smtp_email(to_email: str, subject: str, body: str) -> None:
    """
    docs/ENV.md §6: SMTP_HOST/PORT/USER/PASSWORD, EMAIL_FROM/EMAIL_FROM_NAME.
    Blocking call — safe here because this runs in the worker process, never
    inside a request/transaction (that's the entire point of the outbox).
    """
    from app.core.config import settings

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def _resolve_user_email(user_id: str) -> str | None:
    """
    Opens its own short-lived session — the worker's main session is mid-batch
    (see process_batch), and this handler must not reuse it for an unrelated read.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as _Session

    from app.core.config import settings
    from app.models import User

    engine = create_engine(settings.database_url)
    try:
        with _Session(engine) as session:
            user = session.execute(select(User).where(User.id == user_id)).scalars().first()
            return user.email if user is not None else None
    finally:
        engine.dispose()


def email_verify_email_handler(payload: dict, outbox_id: int) -> None:
    """
    Handler for email.verify_email topic.

    Args:
      - payload: {"user_id": "...", "raw_token": "..."} — see
        app/services/outbox.py's PII guard exemption for why raw_token is here.
      - outbox_id: row ID in outbox table
    """
    from app.core.config import settings

    raw_token = payload["raw_token"]
    verify_url = f"{settings.frontend_origin}/verify-email?token={raw_token}"

    if settings.email_backend == "console":
        print(f"[EMAIL] Verify email link (outbox_id={outbox_id}): {verify_url}")
        return

    to_email = _resolve_user_email(payload["user_id"])
    if to_email is None:
        return

    _send_smtp_email(
        to_email=to_email,
        subject="Yetkin360 - E-posta adresini doğrula",
        body=f"E-posta adresini doğrulamak için: {verify_url}\n\nBu bağlantı 24 saat geçerlidir.",
    )


def email_password_reset_handler(payload: dict, outbox_id: int) -> None:
    """
    Handler for email.password_reset topic.

    Args:
      - payload: {"user_id": "...", "raw_token": "..."}
      - outbox_id: row ID in outbox table
    """
    from app.core.config import settings

    raw_token = payload["raw_token"]
    reset_url = f"{settings.frontend_origin}/reset-password?token={raw_token}"

    if settings.email_backend == "console":
        print(f"[EMAIL] Password reset link (outbox_id={outbox_id}): {reset_url}")
        return

    to_email = _resolve_user_email(payload["user_id"])
    if to_email is None:
        return

    _send_smtp_email(
        to_email=to_email,
        subject="Yetkin360 - Şifre sıfırlama",
        body=f"Şifreni sıfırlamak için: {reset_url}\n\nBu bağlantı 1 saat geçerlidir.",
    )


# Handler dispatch table (expanded as new topics are introduced)
DEFAULT_HANDLERS = {
    "email.duplicate_registration_attempt": email_duplicate_registration_handler,
    "email.verify_email": email_verify_email_handler,
    "email.password_reset": email_password_reset_handler,
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
