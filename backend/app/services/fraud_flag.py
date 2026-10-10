"""
Fraud flag service: admin review queue for AI-generated fraud/suspicious-content
flags (PLAN 3.54 — faz 1, attestation.statement). AI never decides; it only
inserts a PENDING row (app/workers/outbox_worker.py's attestation_fraud_check_handler).
Admin confirms (CONFIRMED) or dismisses (DISMISSED) — this module is where that
decision is recorded.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fraud_flag import FraudFlag


class NotPendingError(Exception):
    """Raised when resolving a flag that isn't PENDING (already reviewed)."""

    pass


def list_fraud_queue(session: Session, limit: int = 50, offset: int = 0) -> list[FraudFlag]:
    """PENDING flags, oldest first (fairness — same ordering as list_verification_queue)."""
    stmt = (
        select(FraudFlag)
        .where(FraudFlag.status == "PENDING")
        .order_by(FraudFlag.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())


def resolve_fraud_flag(
    session: Session,
    flag_id: uuid.UUID,
    outcome: str,
    admin_user_id: Optional[uuid.UUID],
) -> Optional[FraudFlag]:
    """
    Record the admin's decision. outcome must be CONFIRMED or DISMISSED.

    Returns None if the flag does not exist; raises NotPendingError if it was
    already reviewed (no re-review — the first decision stands).
    """
    flag = session.get(FraudFlag, flag_id)
    if flag is None:
        return None
    if flag.status != "PENDING":
        raise NotPendingError(str(flag_id))

    flag.status = outcome
    flag.reviewed_by_user_id = admin_user_id
    flag.reviewed_at = datetime.now(timezone.utc)
    session.flush()
    return flag
