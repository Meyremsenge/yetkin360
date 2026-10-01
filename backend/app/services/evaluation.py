"""Evaluation service: core business logic for creating evaluations."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Engagement, Skill, Evaluation, EvaluationItem, SkillSignal
from app.services.authorization import Principal, get_scoped_or_404, scoped_engagements
from app.services.audit import log_audit_event


class EngagementNotFoundError(Exception):
    """Raised when engagement_id does not exist or is not accessible to principal."""
    pass


class IllegalTransitionError(Exception):
    """Raised when engagement is not in PENDING_EVALUATION status."""
    pass


class TransitionForbiddenError(Exception):
    """Raised when principal is not authorized to perform this evaluation (direction/role mismatch)."""
    pass


class DuplicateEvaluationError(Exception):
    """Raised when evaluation for same engagement+evaluator+direction already exists (UNIQUE violation)."""
    pass


class InvalidSkillError(Exception):
    """Raised when skill_id does not exist in skills table."""
    pass


# Strength mapping for rating → strength (YET-71 AC-4)
EVALUATION_RATING_TO_STRENGTH = {
    "BELOW": "WEAK",
    "MEETS": "MODERATE",
    "EXCEEDS": "STRONG",
    # NOT_OBSERVED: no signal generated (key omitted)
}


def create_evaluation(
    session: Session,
    principal: Principal,
    engagement_id: str,
    direction: str,
    items: list[dict],
    private_note: str | None = None,
) -> Evaluation:
    """
    Create a new evaluation record for an engagement.

    PLAN 2.7 (AC-1 through AC-9, AC-S1 through AC-S3):
    - Validates engagement exists and is in PENDING_EVALUATION status.
    - Validates direction matches principal's role (talent can only POST TALENT_TO_ORG,
      org members can only POST ORG_TO_TALENT).
    - Validates skill_id's exist (if provided) before writing.
    - Creates Evaluation + EvaluationItem records in single transaction (all-or-nothing).
    - Triggers engagement.status → EVALUATED transition ONLY for ORG_TO_TALENT (AC-2).
    - Logs audit event.

    Args:
        session: Database session (transactional).
        principal: Authorization context.
        engagement_id: UUID of engagement (string format).
        direction: ORG_TO_TALENT or TALENT_TO_ORG.
        items: List of {criterion, skill_id, rating, comment}.
        private_note: Optional private note (not returned in response).

    Returns:
        Created Evaluation object.

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible (404).
        IllegalTransitionError: Engagement not in PENDING_EVALUATION status (409).
        TransitionForbiddenError: direction/role mismatch (403).
        DuplicateEvaluationError: UNIQUE constraint violation — already evaluated by this evaluator/direction (409).
        InvalidSkillError: skill_id does not exist (422).
    """
    # Parse engagement_id
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal (404 for out-of-scope)
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid),
        session
    )
    if engagement is None:
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    # AC-6/AC-9: Check engagement status depends on direction
    if direction == "ORG_TO_TALENT":
        if engagement.status != "PENDING_EVALUATION":
            raise IllegalTransitionError(
                f"Engagement must be PENDING_EVALUATION for ORG_TO_TALENT, got {engagement.status}"
            )
    elif direction == "TALENT_TO_ORG":
        if engagement.status not in ("PENDING_EVALUATION", "EVALUATED"):
            raise IllegalTransitionError(
                f"Engagement must be PENDING_EVALUATION or EVALUATED for TALENT_TO_ORG, got {engagement.status}"
            )

    # Compute engagement relation (AC-S1: masking rule for self-dealing prevention)
    from app.services.authorization import engagement_relation
    rel = engagement_relation(principal, engagement)

    # AC-S3: Direction/role consistency check
    # TALENT can only POST TALENT_TO_ORG; ORG_MEMBER can only POST ORG_TO_TALENT
    if rel.is_subject:
        if direction != "TALENT_TO_ORG":
            raise TransitionForbiddenError(
                "Talent can only submit TALENT_TO_ORG evaluations"
            )
    elif rel.is_org_member:
        if direction != "ORG_TO_TALENT":
            raise TransitionForbiddenError(
                "Organization members can only submit ORG_TO_TALENT evaluations"
            )
    elif rel.is_coordinator:
        # Coordinators have no evaluation permission
        raise TransitionForbiddenError(
            "Coordinators cannot submit evaluations"
        )
    else:
        # Not authorized
        raise TransitionForbiddenError(
            "Not authorized to submit evaluations"
        )

    # AC-8: Validate all skill_id's exist and are ACTIVE before writing anything
    for item in items:
        if item.get("skill_id"):
            try:
                skill_uuid = uuid.UUID(item["skill_id"])
            except (ValueError, TypeError):
                raise InvalidSkillError(f"Invalid skill_id format: {item['skill_id']}")

            skill = session.execute(
                select(Skill).where(Skill.id == skill_uuid, Skill.status == "ACTIVE")
            ).scalar_one_or_none()

            if skill is None:
                raise InvalidSkillError(f"Skill {item['skill_id']} not found or is not ACTIVE")

    # Create Evaluation record
    # AC-S2: evaluator_user_id from principal, not from request body
    now = datetime.now(timezone.utc)
    evaluation = Evaluation(
        engagement_id=engagement_uuid,
        evaluator_user_id=principal.user_id,
        direction=direction,
        submitted_at=now,
        private_note=private_note,
    )
    session.add(evaluation)
    try:
        session.flush()
    except IntegrityError as e:
        # Check for UNIQUE constraint violation (engagement_id, evaluator_user_id, direction)
        if "uq_evaluations_engagement_evaluator_direction" in str(e).lower():
            raise DuplicateEvaluationError(
                "Evaluation for this engagement and direction already exists"
            )
        raise

    # Create EvaluationItem records (all-or-nothing with Evaluation)
    # YET-71 AC-3, AC-4, AC-5: Generate SkillSignal for each item (if skill_id and rating != NOT_OBSERVED)
    for item in items:
        skill_id = None
        if item.get("skill_id"):
            try:
                skill_id = uuid.UUID(item["skill_id"])
            except (ValueError, TypeError):
                pass  # Already validated above

        evaluation_item = EvaluationItem(
            evaluation_id=evaluation.id,
            skill_id=skill_id,
            criterion=item["criterion"],
            rating=item["rating"],
            comment=item.get("comment"),
        )
        session.add(evaluation_item)

        # YET-71 AC-3/AC-4/AC-5: Create SkillSignal if skill_id present AND rating != NOT_OBSERVED
        if skill_id is not None and item["rating"] in EVALUATION_RATING_TO_STRENGTH:
            strength = EVALUATION_RATING_TO_STRENGTH[item["rating"]]
            skill_signal = SkillSignal(
                talent_id=engagement.talent_id,
                skill_id=skill_id,
                source_type="EVALUATION",
                source_id=evaluation.id,
                strength=strength,
                attested_by_org_id=engagement.organization_id if rel.is_org_member else None,
                occurred_at=now,
                superseded_by_id=None,
            )
            session.add(skill_signal)

    session.flush()

    # AC-2: Trigger engagement.status → EVALUATED transition ONLY for ORG_TO_TALENT
    if direction == "ORG_TO_TALENT":
        # Read current version and update in same transaction
        result = session.execute(
            update(Engagement)
            .where(
                Engagement.id == engagement_uuid,
                Engagement.status == "PENDING_EVALUATION",
            )
            .values(
                status="EVALUATED",
                version=Engagement.version + 1,
            )
        )

        if result.rowcount == 0:
            raise IllegalTransitionError("Failed to transition engagement status")

        # Refresh engagement to get updated version
        session.refresh(engagement)

        # Log audit event for status transition
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="ENGAGEMENT_TRANSITIONED",
            subject_type="engagement",
            subject_id=engagement.id,
            result="SUCCESS",
            metadata={
                "from_status": "PENDING_EVALUATION",
                "to_status": "EVALUATED",
            },
        )

    # Log audit event for evaluation submission
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="EVALUATION_SUBMITTED",
        subject_type="evaluation",
        subject_id=evaluation.id,
        result="SUCCESS",
        metadata={
            "direction": direction,
            "engagement_id": str(engagement_uuid),
            "items_count": len(items),
            # private_note NOT included (PII protection)
        },
    )

    return evaluation
