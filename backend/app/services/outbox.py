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

# PLAN 1.6: email.verify_email and email.password_reset must deliver a raw,
# single-use, short-lived bearer token in the email body — the token itself
# is stored in the DB only as a SHA-256 hash (one-way), so there is no way to
# hand the worker the raw value except by carrying it through the outbox row.
# The outbox table never leaves the backend DB and the worker's failure log
# already omits the payload (app/workers/outbox_worker.py) — the PII guard's
# actual purpose (keep secrets out of logs/errors) isn't weakened by this;
# only these two topics are exempted, and only for the "raw_token" key.
_PII_GUARD_EXEMPT_TOPICS: dict[str, frozenset[str]] = {
    "email.verify_email": frozenset({"raw_token"}),
    "email.password_reset": frozenset({"raw_token"}),
}


def _check_pii_in_payload(payload: dict | None, exempt_keys: frozenset[str] = frozenset()) -> None:
    """
    Recursively check for sensitive keys in payload dictionary.

    Raises ValueError if any sensitive key is found (case-insensitive), unless
    the key is listed in exempt_keys for this topic.

    Args:
      - payload: dict or None to check
      - exempt_keys: keys allowed to bypass the guard for this call

    Raises:
      - ValueError: if a non-exempt sensitive key is found
    """
    if payload is None:
        return

    sensitive_keys = {"password", "password_hash", "email", "token", "private_note"}

    def _check_dict(d: dict, path: str = "") -> None:
        """Recursively check dictionary for sensitive keys."""
        for key, value in d.items():
            key_lower = key.lower()
            if key_lower in sensitive_keys and key not in exempt_keys:
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
    keys (password, email, token, private_note, password_hash) are detected in
    payload — except "raw_token" on the two topics listed in
    _PII_GUARD_EXEMPT_TOPICS (see module docstring above enqueue).

    Args:
      - session: SQLAlchemy Session (must be within a transaction)
      - topic: Event topic (e.g., "email.duplicate_registration_attempt")
      - payload: Context dict for the handler (checked for PII)

    Raises:
      - ValueError: if payload contains sensitive keys

    Implements AC-1, AC-S1.
    """
    # Check for PII in payload
    _check_pii_in_payload(payload, exempt_keys=_PII_GUARD_EXEMPT_TOPICS.get(topic, frozenset()))

    # Insert outbox row (within the same transaction)
    row = Outbox(topic=topic, payload=payload)
    session.add(row)
    session.flush()
