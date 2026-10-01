"""
Outbox worker: polling and processing transactional outbox.

Implements AC-2 (select & process), AC-4 (failure handling), AC-5 (max_attempts),
AC-6 (SKIP LOCKED), AC-S2 (logging without payload).

The worker polls the outbox table for due rows (processed_at IS NULL) whose
topic has a registered handler, dispatches each to its handler outside any
transaction, and records the result in a separate transaction. Failures are
retried with exponential backoff; rows exceeding max_attempts are dead-lettered.

Run it with: python -m app.workers.outbox_worker (loops until interrupted).
"""

import logging
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.outbox import Outbox

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 3600


def _backoff_seconds(attempts: int, base_seconds: int) -> int:
    """Delay before the next try after the Nth failed attempt: base, 2*base, 4*base, ..."""
    return min(base_seconds * 2 ** (attempts - 1), MAX_BACKOFF_SECONDS)


def process_batch(
    session: Session,
    handlers: dict,
    max_attempts: int = 5,
    batch_size: int = 10,
    backoff_base_seconds: int = 30,
    lease_seconds: int = 300,
) -> int:
    """
    Process a batch of due outbox rows. No network call ever runs inside an
    open transaction (CLAUDE.md / docs: outbox rule), so a batch is three
    phases:

      1. CLAIM (short transaction): select due rows with FOR UPDATE SKIP LOCKED
         and push their next_attempt_at forward by lease_seconds, then commit.
         The lease, not a held row lock, keeps other workers off the rows while
         the handlers run; if this worker dies, the lease simply expires and
         the row is retried (at-least-once delivery).
      2. HANDLE (no transaction): call the handler for each claimed row.
      3. RECORD (one short transaction per row): success sets processed_at and
         redacts the payload; failure increments attempts and schedules the
         next try with exponential backoff. A row reaching max_attempts is
         dead-lettered (never selected again) and a warning is logged.

    Only rows whose topic has a registered handler are selected. Rows for
    topics without a handler stay untouched in the table, so they can never
    occupy the head of the queue and starve deliverable rows, and a handler
    added later picks them up.

    Returns the number of rows successfully processed.
    """
    if not handlers:
        return 0

    now = datetime.now(timezone.utc)
    rows = session.execute(
        select(Outbox)
        .where(Outbox.processed_at.is_(None))
        .where(Outbox.attempts < max_attempts)
        .where(Outbox.topic.in_(list(handlers)))
        .where(or_(Outbox.next_attempt_at.is_(None), Outbox.next_attempt_at <= now))
        .order_by(Outbox.created_at, Outbox.id)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    claimed = [(row.id, row.topic, row.payload, row.attempts) for row in rows]
    lease_until = now + timedelta(seconds=lease_seconds)
    for row in rows:
        row.next_attempt_at = lease_until
    session.commit()

    processed_count = 0
    for outbox_id, topic, payload, attempts in claimed:
        try:
            handlers[topic](payload, outbox_id)
        except Exception as e:
            new_attempts = attempts + 1
            session.execute(
                update(Outbox)
                .where(Outbox.id == outbox_id)
                .values(
                    attempts=new_attempts,
                    next_attempt_at=datetime.now(timezone.utc)
                    + timedelta(seconds=_backoff_seconds(new_attempts, backoff_base_seconds)),
                )
            )
            session.commit()
            # Never log the exception message: SMTP errors embed recipient
            # addresses, and payloads carry tokens (docs/SECURITY.md log rule).
            logger.error(
                "Outbox handler failed: outbox_id=%s, topic=%s, error_type=%s, attempts=%s",
                outbox_id, topic, type(e).__name__, new_attempts,
            )
            if new_attempts >= max_attempts:
                logger.warning(
                    "Outbox row dead-lettered: outbox_id=%s, topic=%s", outbox_id, topic
                )
            continue

        # Rows exempted from the PII guard (email.verify_email,
        # email.password_reset) carry a raw bearer token that must not remain
        # in the DB/backups once it has been delivered.
        session.execute(
            update(Outbox)
            .where(Outbox.id == outbox_id)
            .values(processed_at=datetime.now(timezone.utc), payload={}, next_attempt_at=None)
        )
        session.commit()
        processed_count += 1

    return processed_count


def run_forever(
    engine: Engine,
    handlers: dict,
    poll_interval_seconds: int,
    max_attempts: int,
    backoff_base_seconds: int,
    max_iterations: int | None = None,
) -> None:
    """
    Poll loop. Sleeps poll_interval_seconds only when a pass made no progress;
    a pass that delivered rows loops again immediately to drain the backlog.
    A loop-level error (e.g. the database restarting) is logged by type and
    retried after the poll interval instead of killing the worker.
    max_iterations exists for tests; production runs until interrupted.
    """
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        iteration += 1
        processed = 0
        try:
            with Session(engine) as session:
                processed = process_batch(
                    session,
                    handlers,
                    max_attempts=max_attempts,
                    backoff_base_seconds=backoff_base_seconds,
                )
        except Exception as e:
            logger.error("Outbox worker pass failed: error_type=%s", type(e).__name__)
        if processed == 0:
            time.sleep(poll_interval_seconds)


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
    Worker entry point: python -m app.workers.outbox_worker (run from backend/).

    Loops until interrupted (Ctrl+C). baslat.bat starts it in its own window;
    in production run the same command under systemd/supervisor.
    """
    from sqlalchemy import create_engine

    from app.core.config import settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = create_engine(settings.database_url)
    logger.info(
        "Outbox worker started: poll_interval=%ss, max_attempts=%s, backend=%s",
        settings.outbox_poll_interval_seconds,
        settings.outbox_max_attempts,
        settings.email_backend,
    )
    try:
        run_forever(
            engine,
            DEFAULT_HANDLERS,
            poll_interval_seconds=settings.outbox_poll_interval_seconds,
            max_attempts=settings.outbox_max_attempts,
            backoff_base_seconds=settings.outbox_backoff_base_seconds,
        )
    except KeyboardInterrupt:
        logger.info("Outbox worker stopped.")
    finally:
        engine.dispose()
