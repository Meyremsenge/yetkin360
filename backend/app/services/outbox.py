"""
Outbox service: enqueue() helper for transactional outbox pattern.

Implements AC-1 (happy path), AC-S1 (PII guard).

The enqueue() function allows services to safely queue side effects (email, SMS, webhooks)
within a transaction without making blocking network calls. The payload is checked for
sensitive keys before insertion, preventing PII from leaking into the outbox log.

Design: PII guard is duplicated (not imported from audit.py) to keep outbox independent
of audit's internal implementation. See CLAUDE.md modularity rules.
"""

from sqlalchemy.orm import Session

from app.models.outbox import Outbox


def _check_pii_in_payload(payload: dict | None) -> None:
    """
    Recursively check for sensitive keys in payload dictionary.

    Raises ValueError if any sensitive key is found (case-insensitive).
    Sensitive keys: password, password_hash, email, token, private_note

    Args:
      - payload: dict or None to check

    Raises:
      - ValueError: if sensitive key is found
    """
    if payload is None:
        return

    sensitive_keys = {"password", "password_hash", "email", "token", "private_note"}

    def _check_dict(d: dict, path: str = "") -> None:
        """Recursively check dictionary for sensitive keys."""
        for key, value in d.items():
            key_lower = key.lower()
            if key_lower in sensitive_keys:
                raise ValueError(f"PII detected in payload: {key_lower}")
            # Recursively check nested dictionaries
            if isinstance(value, dict):
                _check_dict(value, f"{path}.{key}" if path else key)

    _check_dict(payload)


def enqueue(session: Session, topic: str, payload: dict) -> None:
    """
    Enqueue a side effect (email, SMS, webhook) to be processed asynchronously.

    Synchronously inserts a row into the outbox table with processed_at=NULL
    and attempts=0. The row is inserted within the caller's transaction, ensuring
    atomicity: if the transaction rolls back, the outbox row is rolled back too.

    Performs PII guard check before insertion. Raises ValueError if sensitive
    keys (password, email, token, private_note, password_hash) are detected in payload.

    Args:
      - session: SQLAlchemy Session (must be within a transaction)
      - topic: Event topic (e.g., "email.duplicate_registration_attempt")
      - payload: Context dict for the handler (checked for PII)

    Raises:
      - ValueError: if payload contains sensitive keys

    Implements AC-1, AC-S1.
    """
    # Check for PII in payload
    _check_pii_in_payload(payload)

    # Insert outbox row (within the same transaction)
    row = Outbox(topic=topic, payload=payload)
    session.add(row)
    session.flush()
