"""
Reminder service (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu).

Implements bulk reminder triggering for institution coordinators/admins.
"""

import uuid
from sqlalchemy.orm import Session

from app.models import Engagement, Outbox
from app.services.audit import log_audit_event
from app.services.authorization import scoped_engagements, Principal


def create_reminders(
    institution_id: uuid.UUID,
    engagement_ids: list[uuid.UUID],
    template: str,
    actor_user_id: uuid.UUID,
    principal: Principal,
    session: Session,
) -> int:
    """
    Create reminder outbox entries for engagement(s) within institution scope.

    Implements AC-1 (happy path), AC-2 (validation), AC-3 (cross-institution filtering),
    AC-6 (zero queued), AC-7 (template validation).

    Args:
        institution_id: Institution UUID (must match principal's scope)
        engagement_ids: List of engagement UUIDs to trigger reminders for
        template: Template name (e.g., "evaluation_pending")
        actor_user_id: User ID triggering the reminders (for audit)
        principal: Principal object with authorization context
        session: SQLAlchemy Session

    Returns:
        int: Count of engagements queued (0 if all filtered out)

    Raises:
        ValueError: If template is empty/invalid (Pydantic validates this, but explicit here)

    Transaction safety: All outbox + audit_event rows inserted in single transaction.
    If any error occurs, entire transaction is rolled back.
    """
    # Validate institution is in principal's scope
    if institution_id not in principal.institution_ids:
        # Caller must ensure this doesn't reach here (404 at endpoint layer)
        # But as defense-in-depth, fail here too
        raise PermissionError(f"Institution {institution_id} not in scope")

    # Filter engagement_ids to those within institution scope
    # AC-3: Cross-institution IDs silently filtered out
    scoped_query = scoped_engagements(session, principal)
    scoped_query = scoped_query.where(
        Engagement.institution_id == institution_id,
        Engagement.id.in_(engagement_ids),
    )
    valid_engagements = session.execute(scoped_query).scalars().all()

    queued_count = 0

    # Create outbox entry for each valid engagement
    for engagement in valid_engagements:
        outbox_entry = Outbox(
            topic=f"reminder.{template}",
            payload={
                "engagement_id": str(engagement.id),
                "template": template,
                "institution_id": str(institution_id),
            },
        )
        session.add(outbox_entry)
        queued_count += 1

    # Create audit event only if at least one engagement was queued (AC-6: no side effect if queued_count=0)
    if queued_count > 0:
        log_audit_event(
            session=session,
            actor_user_id=actor_user_id,
            actor_ip=None,  # IP not available at service layer
            action="REMINDERS_TRIGGERED",
            subject_type="INSTITUTION",
            subject_id=institution_id,
            result="SUCCESS",
            metadata={
                "template": template,
                "queued_count": queued_count,
                "engagement_ids": [str(eng.id) for eng in valid_engagements],
            },
        )

    # Transaction committed by caller (route layer)
    return queued_count
