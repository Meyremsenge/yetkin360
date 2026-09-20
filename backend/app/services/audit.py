"""
Audit event logging service with PII guard.

Implements AC-4, AC-S6 (PII protection).
"""

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def _check_pii_in_metadata(metadata: dict | None) -> None:
    """
    Recursively check for sensitive keys in metadata dictionary.

    Raises ValueError if any sensitive key is found (case-insensitive).
    Sensitive keys: password, password_hash, email, tc_kimlik_no

    Args:
      - metadata: dict or None to check

    Raises:
      - ValueError: if sensitive key is found
    """
    if metadata is None:
        return

    sensitive_keys = {"password", "password_hash", "email", "tc_kimlik_no"}

    def _check_dict(d: dict, path: str = "") -> None:
        """Recursively check dictionary for sensitive keys."""
        for key, value in d.items():
            key_lower = key.lower()
            if key_lower in sensitive_keys:
                raise ValueError(f"PII detected in metadata: {key_lower}")
            # Recursively check nested dictionaries
            if isinstance(value, dict):
                _check_dict(value, f"{path}.{key}" if path else key)

    _check_dict(metadata)


def log_audit_event(
    session: Session,
    actor_user_id: uuid.UUID | None,
    actor_ip: str | None,
    action: str,
    subject_type: str,
    subject_id: uuid.UUID | None,
    result: str,
    metadata: dict | None = None,
) -> None:
    """
    Log an audit event to the audit_events table.

    Performs PII guard check before insertion. Raises ValueError if sensitive
    keys are detected in metadata.

    Args:
      - session: SQLAlchemy Session
      - actor_user_id: UUID of the actor (None for anonymous)
      - actor_ip: IP address of the actor (None if not available)
      - action: Event action name (e.g., "USER_LOGIN", "RESOURCE_ACCESS")
      - subject_type: Type of affected resource (e.g., "user", "organization")
      - subject_id: UUID of affected resource (None if not applicable)
      - result: Outcome: "SUCCESS", "DENIED", or "ERROR"
      - metadata: Optional dict with event metadata (PII will be rejected)

    Raises:
      - ValueError: if metadata contains sensitive keys (password, email, etc.)
      - IntegrityError: if result is not in (SUCCESS, DENIED, ERROR)

    Implements AC-4, AC-S6.
    """
    # Check for PII in metadata
    _check_pii_in_metadata(metadata)

    # Create and insert audit event
    event = AuditEvent(
        actor_user_id=actor_user_id,
        actor_ip=actor_ip,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        result=result,
        event_metadata=metadata,
    )
    session.add(event)
    session.flush()
