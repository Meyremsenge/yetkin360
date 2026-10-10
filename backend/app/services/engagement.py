"""Engagement service: core business logic for work engagements."""

import uuid
from datetime import datetime, timezone, date
from typing import Any, Callable, Sequence, TypedDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Attestation,
    Deliverable,
    EngagementTask,
    Engagement,
    Organization,
    TalentProfile,
    Skill,
    SkillSignal,
)
from app.services.authorization import Principal, engagement_relation, get_scoped_or_404, scoped_engagements
from app.services.audit import log_audit_event
from app.services.outbox import enqueue


class TalentNotFoundError(Exception):
    """Raised when talent_id does not exist or is not accessible to principal."""

    pass


class OrganizationNotFoundError(Exception):
    """Raised when organization_id does not exist or is not accessible to principal."""

    pass


class InstitutionMismatchError(Exception):
    """Raised when institution_id does not match talent's institution."""

    pass


class EngagementNotFoundError(Exception):
    """Raised when engagement_id does not exist or is not accessible to principal."""

    pass


class IllegalTransitionError(Exception):
    """Raised when to_status is not a valid transition from current status."""

    pass


class PreconditionFailedError(Exception):
    """Raised when transition preconditions are not met (institution_id NULL, reason missing)."""

    pass


class ReasonTooLongError(Exception):
    """Raised when reason field exceeds maximum length (AC-3 — 400 VALIDATION_ERROR)."""

    pass


class DateValidationError(Exception):
    """Raised when date constraints violated (AC-2 — 400 VALIDATION_ERROR)."""

    pass


class TransitionForbiddenError(Exception):
    """Raised when principal is not authorized to perform this transition."""

    pass


class VersionConflictError(Exception):
    """Raised when version from request does not match DB version (optimistic locking)."""

    pass


class TaskNotFoundError(Exception):
    """Task not found in this engagement (→ 404)."""


class TaskAlreadyVerifiedError(Exception):
    """Task is already verified (→ 409)."""


class InvalidSkillError(Exception):
    """Raised when skill_id does not exist in skills table or is not ACTIVE."""

    pass


# Strength constants for SkillSignal generation (YET-71)
TASK_SIGNAL_STRENGTH = "WEAK"
# The talent may plan tasks as soon as the engagement exists; they stay
# unverified (no SkillSignal) until the organization side verifies them.
TALENT_TASK_STATUSES = ("DRAFT", "ACTIVE")
VERIFIER_TASK_STATUSES = ("ACTIVE",)
# Verifying needs an engagement the organization has accepted and not closed off.
TASK_VERIFICATION_BLOCKED_STATUSES = ("DRAFT", "PENDING_APPROVAL", "REJECTED", "CANCELLED")
DELIVERABLE_SIGNAL_STRENGTH = "MODERATE"


class TransitionSpec(TypedDict):
    """Type specification for transition table entries."""

    preconditions: list[str]
    can_transition: Callable[[], bool]


def create_engagement(
    session: Session,
    principal: Principal,
    talent_id: str,
    organization_id: str,
    kind: str,
    title: str,
    institution_id: str | None = None,
    confidential: bool = False,
) -> Engagement:
    """
    Create a new engagement record for a talent.

    AC-1: POST /engagements logic.
    - Validates talent exists and is accessible to principal
    - Validates organization exists and is accessible to principal
    - Validates institution_id (if provided) matches talent's institution
    - Creates engagement with status=DRAFT, version=1
    - Logs audit event in same transaction

    Args:
        session: Database session
        principal: Authorization context
        talent_id: UUID of talent (string format)
        organization_id: UUID of organization (string format)
        kind: Engagement kind (INTERNSHIP|CAPSTONE|SHORT_PROJECT|PART_TIME)
        title: Engagement title
        institution_id: Optional UUID of institution (string format)
        confidential: Whether engagement is confidential

    Returns:
        Created Engagement object

    Raises:
        TalentNotFoundError: If talent does not exist or is not accessible
        OrganizationNotFoundError: If organization does not exist or is not accessible
        InstitutionMismatchError: If institution_id doesn't match talent's institution
    """
    # Parse UUIDs
    try:
        talent_uuid = uuid.UUID(talent_id)
    except ValueError:
        raise TalentNotFoundError(f"Invalid talent_id format: {talent_id}")

    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        raise OrganizationNotFoundError(f"Invalid organization_id format: {organization_id}")

    try:
        inst_uuid = uuid.UUID(institution_id) if institution_id else None
    except ValueError:
        raise InstitutionMismatchError(f"Invalid institution_id format: {institution_id}")

    # Default-deny: check authorization via membership lists, not kind
    # own_talent: principal can create for their own talent_id
    own_talent = (
        principal.talent_id is not None
        and principal.talent_id == talent_uuid
    )
    # has_org_membership: principal is member or admin of the organization
    has_org_membership = org_uuid in principal.org_ids

    if not (own_talent or has_org_membership):
        # Authorization check failed: determine which error to raise
        if principal.org_ids:
            # Principal has organization memberships but not this one
            raise OrganizationNotFoundError(
                f"Organization {organization_id} not found or not accessible"
            )
        else:
            # Principal has no organization memberships
            raise TalentNotFoundError("Not authorized to create engagements")

    # Verify talent exists
    talent = session.execute(
        select(TalentProfile).where(TalentProfile.id == talent_uuid)
    ).scalar_one_or_none()

    if not talent:
        raise TalentNotFoundError(f"Talent {talent_id} not found")

    org = session.execute(
        select(Organization).where(Organization.id == org_uuid)
    ).scalar_one_or_none()

    if not org:
        raise OrganizationNotFoundError(f"Organization {organization_id} not found")

    # Validate institution_id if provided (AC-5, AC-S3)
    # institution_id must match talent's institution_id
    if inst_uuid is not None:
        if talent.institution_id != inst_uuid:
            # Generic error message that doesn't reveal whether institution exists
            raise InstitutionMismatchError("institution_id does not match talent's institution")

    # Create new engagement (AC-1)
    engagement = Engagement(
        talent_id=talent_uuid,
        organization_id=org_uuid,
        institution_id=inst_uuid,
        kind=kind,
        title=title,
        status="DRAFT",
        version=1,
        confidential=confidential,
    )
    session.add(engagement)
    try:
        session.flush()
    except IntegrityError as e:
        # Check if it's a FK constraint violation
        if "fk_" in str(e).lower() or "foreign key" in str(e).lower():
            raise TalentNotFoundError("Referenced resource not found")
        raise

    # Log audit event in same transaction (AC-1)
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ENGAGEMENT_CREATED",
        subject_type="engagement",
        subject_id=engagement.id,
        result="SUCCESS",
        metadata={
            "kind": kind,
            "talent_id": str(talent_uuid),
            "organization_id": str(org_uuid),
        },
    )

    return engagement


def transition_engagement(
    session: Session,
    principal: Principal,
    engagement_id: str,
    to_status: str,
    version: int | None = None,
    reason: str | None = None,
    started_on: str | None = None,
    ended_on: str | None = None,
) -> Engagement:
    """
    Transition engagement status with optimistic locking and authorization checks.

    PLAN 2.2 — engagement-durum-makinesi-transitions-ucu.

    Implements Acceptance Criteria AC-1 through AC-14, AC-S1 through AC-S4, AC-2 (started_on/ended_on),
    AC-3 (T4 kurumsuz DRAFT→ACTIVE), AC-7 (T8 SUPERVISOR-only).

    Transition table (7 transitions):
    - T1: DRAFT → PENDING_APPROVAL (TALENT/ORG_MEMBER/ORG_ADMIN with matching talent/org)
    - T2: PENDING_APPROVAL → ACTIVE (COORDINATOR with matching institution)
    - T3: PENDING_APPROVAL → REJECTED (COORDINATOR with matching institution, requires reason)
    - T4: DRAFT → ACTIVE (no institution required; kurumsuz engagement)
    - T5: ACTIVE → PENDING_EVALUATION (has deliverable)
    - T6: ACTIVE → CANCELLED (ORG_ADMIN/COORDINATOR with matching org/institution, requires reason)
    - T8: EVALUATED → VERIFIED (SUPERVISOR only, ORG_ADMIN returns 404)

    Args:
        session: Database session (must be transactional)
        principal: Authorization context
        engagement_id: UUID of engagement (string format)
        to_status: Target status (must be valid transition from current)
        version: Optimistic locking version from request
        reason: Optional reason for REJECTED/CANCELLED transitions
        started_on: Optional start date (ISO format string) for engagement
        ended_on: Optional end date (ISO format string) for engagement

    Returns:
        Updated Engagement object

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible (404)
        IllegalTransitionError: to_status not valid from current status (422)
        PreconditionFailedError: Preconditions not met (institution_id NULL, reason missing, date validation) (422)
        TransitionForbiddenError: Principal not authorized for this transition (403 or 404)
        VersionConflictError: Version mismatch (optimistic locking) (409)
    """
    # Parse UUID
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal (AC-10, AC-11 unified by get_scoped_or_404)
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid), session
    )
    if engagement is None:
        # Both "engagement doesn't exist" and "no access" return 404 per AC-11
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    current_status = engagement.status

    # Check: version mismatch (optimistic locking) EARLY — before other checks (AC-9, AC-S1, AC-S4)
    # This ensures version conflict is reported before illegal transition or authorization errors
    # If version is None, skip the check (for backward compatibility with tests)
    if version is not None and engagement.version != version:
        raise VersionConflictError("Version conflict: engagement has been modified since retrieval")

    # AC-S1: relation is masked for the subject (self-dealing prevention)
    rel = engagement_relation(principal, engagement)

    # Transition table (7 valid transitions)
    # Each entry: from_status -> to_status -> (allowed_roles, preconditions, authorization check)
    transition_table: dict[tuple[str, str], TransitionSpec] = {
        ("DRAFT", "PENDING_APPROVAL"): {
            "preconditions": ["institution_id_not_null"],
            "can_transition": lambda: (
                rel.is_subject or rel.is_org_member
            ),
        },
        ("DRAFT", "ACTIVE"): {
            "preconditions": ["date_validation"],
            "can_transition": lambda: (
                (rel.is_coordinator and engagement.institution_id is not None)
                or (rel.is_subject and engagement.institution_id is None)
            ),
        },
        ("PENDING_APPROVAL", "ACTIVE"): {
            "preconditions": [],
            "can_transition": lambda: (
                rel.is_coordinator
            ),
        },
        ("PENDING_APPROVAL", "REJECTED"): {
            "preconditions": ["reason_not_empty"],
            "can_transition": lambda: (
                rel.is_coordinator
            ),
        },
        ("ACTIVE", "CANCELLED"): {
            "preconditions": ["reason_not_empty"],
            "can_transition": lambda: (
                rel.is_org_admin or rel.is_coordinator
            ),
        },
        ("ACTIVE", "PENDING_EVALUATION"): {
            "preconditions": ["has_deliverable"],
            "can_transition": lambda: (
                rel.is_org_member or rel.is_coordinator
            ),
        },
        ("EVALUATED", "VERIFIED"): {
            "preconditions": [],
            "can_transition": lambda: (
                engagement.institution_id is not None
                and engagement.institution_id in principal.supervisor_institution_ids
            ),
        },
    }

    # Check: is this transition defined? (AC-5)
    if (current_status, to_status) not in transition_table:
        raise IllegalTransitionError(
            f"Transition from {current_status} to {to_status} is not allowed"
        )

    transition_spec = transition_table[(current_status, to_status)]

    # Check: preconditions (AC-6, AC-7, AC-2, AC-3)
    for precondition in transition_spec["preconditions"]:
        if precondition == "institution_id_not_null":
            if engagement.institution_id is None:
                raise PreconditionFailedError("institution_id is required for this transition")
        elif precondition == "reason_not_empty":
            if not reason or reason.strip() == "":
                raise PreconditionFailedError("reason is required for this transition")
        elif precondition == "has_deliverable":
            # Real database query to verify at least one Deliverable exists (AC-S4: client input ignored)
            count = session.execute(
                select(func.count())
                .select_from(Deliverable)
                .where(Deliverable.engagement_id == engagement.id)
            ).scalar()
            if count == 0:
                raise PreconditionFailedError("En az bir deliverable gerekli.")
        elif precondition == "date_validation":
            # AC-2: Validate date ordering if both dates provided
            if started_on is not None and ended_on is not None:
                try:
                    start_date = date.fromisoformat(started_on)
                    end_date = date.fromisoformat(ended_on)
                    if start_date > end_date:
                        raise DateValidationError("started_on must be <= ended_on")
                except ValueError:
                    raise DateValidationError("Invalid date format (expected ISO format)")

    # Check: authorization (AC-8, AC-S3, AC-7)
    # AC-7: T8 (EVALUATED→VERIFIED) requires SUPERVISOR of this institution; 404 for unauthorized (not 403)
    if (current_status, to_status) == ("EVALUATED", "VERIFIED") and (
        engagement.institution_id is None
        or engagement.institution_id not in principal.supervisor_institution_ids
    ):
        raise EngagementNotFoundError("Engagement not found")

    if not transition_spec["can_transition"]():
        raise TransitionForbiddenError("Not authorized to perform this transition")

    # Optimistic locking: UPDATE with status and version check (defense-in-depth paranoia check)
    # Version was already checked above, but UPDATE includes it for atomic consistency
    from sqlalchemy import update

    values_dict: dict[str, Any] = {"status": to_status, "version": Engagement.version + 1}

    # AC-2: Set started_on/ended_on if provided
    if started_on is not None:
        values_dict["started_on"] = date.fromisoformat(started_on)
    if ended_on is not None:
        values_dict["ended_on"] = date.fromisoformat(ended_on)

    # AC-3: Handle reason field (append-only with length control)
    if reason is not None:
        max_reason_length = 1000
        new_reason = reason
        if engagement.reason:
            # Append: concatenate with newline separator
            new_reason = engagement.reason + "\n" + reason

        if len(new_reason) > max_reason_length:
            raise ReasonTooLongError(
                f"reason field exceeds maximum length of {max_reason_length} characters"
            )
        values_dict["reason"] = new_reason

    # Build WHERE clause: include version only if it was provided
    from sqlalchemy import and_
    where_clauses = [
        Engagement.id == engagement_uuid,
        Engagement.status == current_status,
    ]
    if version is not None:
        where_clauses.append(Engagement.version == version)

    result = session.execute(
        update(Engagement)
        .where(and_(*where_clauses))
        .values(**values_dict)
    )

    # Paranoia check: if rowcount==0, either status changed or version mismatch (when version provided)
    if result.rowcount == 0:
        if version is not None:
            raise VersionConflictError("Update failed: engagement state changed unexpectedly")
        else:
            # No version check, so if UPDATE returns 0 rows, something else went wrong
            raise EngagementNotFoundError("Update failed: engagement not found or status changed")

    # Refresh engagement from DB to get updated version
    session.refresh(engagement)

    # Log audit event (istisnasız her geçişte) — reason KONULMAMALI audit payload'ına
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="ENGAGEMENT_TRANSITIONED",
        subject_type="engagement",
        subject_id=engagement.id,
        result="SUCCESS",
        metadata={
            "from_status": current_status,
            "to_status": to_status,
        },
    )

    # Enqueue outbox for notification (T1: PENDING_APPROVAL → koordinatör bildirimi)
    # T2, T3, T6 için de benzer bildirimler olabilir ama bu görevde T1'e fokus
    # reason KONULMAMALI outbox payload'ına (PII riski)
    if to_status == "PENDING_APPROVAL":
        # Notify coordinators of the institution
        enqueue(
            session=session,
            topic="engagement.pending_approval",
            payload={
                "engagement_id": str(engagement.id),
                "talent_id": str(engagement.talent_id),
                "organization_id": str(engagement.organization_id),
                "institution_id": str(engagement.institution_id),
            },
        )

    # PLAN 3.56: coordinator approval (T2) is the main defence against fake
    # internships — check the approval itself for conflict-of-interest/bulk patterns.
    if current_status == "PENDING_APPROVAL" and to_status == "ACTIVE":
        enqueue(
            session=session,
            topic="fraud.approval_risk_scan_requested",
            payload={"engagement_id": str(engagement.id), "approver_user_id": str(principal.user_id)},
        )

    return engagement


def create_engagement_task(
    session: Session,
    principal: Principal,
    engagement_id: str,
    title: str,
    description: str | None = None,
    due_at: datetime | None = None,
    skill_id: str | None = None,
) -> EngagementTask:
    """
    Create a new task within an engagement.

    PLAN 2.4 (AC-1): POST /engagements/{id}/tasks.
    PLAN 2.9 (YET-71): Optional skill_id triggers SkillSignal generation (AC-1, AC-6, AC-7).

    Who may create, and what it produces:
      - organization member / coordinator: ACTIVE engagements only; the task is
        verified on creation and a skill_id produces a SkillSignal (unchanged).
      - the talent, on their own engagement: DRAFT or ACTIVE; the task is
        unverified and produces no SkillSignal until verify_engagement_task().

    Args:
        session: Database session
        principal: Authorization context
        engagement_id: UUID of engagement (string format)
        title: Task title
        description: Optional task description
        due_at: Optional due date
        skill_id: Optional UUID of skill (string format) for SkillSignal generation

    Returns:
        Created EngagementTask object

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible
        PreconditionFailedError: Engagement status does not accept tasks from this principal
        TransitionForbiddenError: Principal can see the engagement but may not create tasks
        InvalidSkillError: skill_id provided but does not exist or is not ACTIVE (AC-7)
    """
    # Parse UUID
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid), session
    )
    if engagement is None:
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    # AC-S1: relation is masked for the subject (self-dealing prevention), so a
    # talent who is also a member of the organization is treated as the talent.
    rel = engagement_relation(principal, engagement)
    is_verifier = rel.is_org_member or rel.is_coordinator
    as_talent = rel.is_subject and not is_verifier

    # AC-5: status gate (checked before the role, as before)
    allowed_statuses = TALENT_TASK_STATUSES if as_talent else VERIFIER_TASK_STATUSES
    if engagement.status not in allowed_statuses:
        raise PreconditionFailedError("Task cannot be created in this engagement status")

    if not (is_verifier or as_talent):
        raise TransitionForbiddenError("Not authorized to create tasks")

    # AC-7: Validate skill_id BEFORE writing anything
    skill_id_uuid = None
    if skill_id:
        try:
            skill_id_uuid = uuid.UUID(skill_id)
        except ValueError:
            raise InvalidSkillError(f"Invalid skill_id format: {skill_id}")

        # Verify skill exists and is ACTIVE in database (AC-7)
        skill = session.execute(
            select(Skill).where(Skill.id == skill_id_uuid, Skill.status == "ACTIVE")
        ).scalar_one_or_none()

        if skill is None:
            raise InvalidSkillError(f"Skill {skill_id} not found or is not ACTIVE")

    # Create task
    task = EngagementTask(
        engagement_id=engagement_uuid,
        skill_id=skill_id_uuid,
        title=title,
        description=description,
        status="PLANNED",
        due_at=due_at,
        created_by_user_id=principal.user_id,
        verified_at=datetime.now(timezone.utc) if is_verifier else None,
        verified_by_user_id=principal.user_id if is_verifier else None,
    )
    session.add(task)
    try:
        session.flush()
    except IntegrityError as e:
        if "fk_" in str(e).lower() or "foreign key" in str(e).lower():
            raise EngagementNotFoundError("Engagement not found")
        raise

    # AC-1, AC-6: a verified task with a skill produces a SkillSignal. A task
    # the talent added is unverified, so its signal waits for verification.
    if is_verifier:
        _add_task_signal(session, engagement, task, occurred_at=task.created_at)

    # Log audit event
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="TASK_CREATED",
        subject_type="task",
        subject_id=task.id,
        result="SUCCESS",
        metadata={
            "engagement_id": str(engagement_uuid),
            "title": title,
            "verified": is_verifier,
        },
    )

    return task


def _add_task_signal(
    session: Session, engagement: Engagement, task: EngagementTask, occurred_at: datetime
) -> None:
    if task.skill_id is None:
        return
    session.add(
        SkillSignal(
            talent_id=engagement.talent_id,
            skill_id=task.skill_id,
            source_type="TASK",
            source_id=task.id,
            strength=TASK_SIGNAL_STRENGTH,
            attested_by_org_id=None,
            occurred_at=occurred_at,
            superseded_by_id=None,
        )
    )
    session.flush()


def verify_engagement_task(
    session: Session,
    principal: Principal,
    engagement_id: str,
    task_id: str,
) -> EngagementTask:
    """
    Verify a task the talent added: POST /engagements/{id}/tasks/{task_id}/verify.

    Only an organization member of the engagement or the institution's
    coordinator may verify; the talent can never verify their own task
    (engagement_relation masks org/coordinator flags for the subject). The
    task's SkillSignal, if it has a skill, is written here.

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible (→ 404)
        TaskNotFoundError: No such task in this engagement (→ 404)
        TransitionForbiddenError: Principal can see the engagement but may not verify (→ 403)
        PreconditionFailedError: Engagement status does not allow verification (→ 422)
        TaskAlreadyVerifiedError: Task is already verified (→ 409)
    """
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid), session
    )
    if engagement is None:
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise TaskNotFoundError(f"Invalid task_id format: {task_id}")

    # Locked: two verifiers at once must not write the signal twice.
    task = session.execute(
        select(EngagementTask)
        .where(EngagementTask.id == task_uuid, EngagementTask.engagement_id == engagement.id)
        .with_for_update()
    ).scalar_one_or_none()
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")

    rel = engagement_relation(principal, engagement)
    if not (rel.is_org_member or rel.is_coordinator):
        raise TransitionForbiddenError("Not authorized to verify tasks")

    if engagement.status in TASK_VERIFICATION_BLOCKED_STATUSES:
        raise PreconditionFailedError("Task cannot be verified in this engagement status")

    if task.verified_at is not None:
        raise TaskAlreadyVerifiedError(f"Task {task_id} is already verified")

    now = datetime.now(timezone.utc)
    task.verified_at = now
    task.verified_by_user_id = principal.user_id
    session.flush()

    _add_task_signal(session, engagement, task, occurred_at=now)

    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="TASK_VERIFIED",
        subject_type="task",
        subject_id=task.id,
        result="SUCCESS",
        metadata={"engagement_id": str(engagement.id)},
    )

    return task


def create_deliverable(
    session: Session,
    principal: Principal,
    engagement_id: str,
    title: str,
    description: str | None = None,
    skill_id: str | None = None,
) -> Deliverable:
    """
    Create a new deliverable (evidence submission) within an engagement.

    PLAN 2.4 (AC-2): POST /engagements/{id}/deliverables.
    PLAN 2.9 (YET-71): Optional skill_id triggers SkillSignal generation (AC-2, AC-6, AC-7).

    Args:
        session: Database session
        principal: Authorization context
        engagement_id: UUID of engagement (string format)
        title: Deliverable title
        description: Optional deliverable description
        skill_id: Optional UUID of skill (string format) for SkillSignal generation

    Returns:
        Created Deliverable object

    Raises:
        EngagementNotFoundError: Engagement not found or not accessible
        PreconditionFailedError: Engagement not ACTIVE
        TransitionForbiddenError: Principal not authorized (e.g., ORG_MEMBER trying to submit)
        InvalidSkillError: skill_id provided but does not exist or is not ACTIVE (AC-7)
    """
    # Parse UUID
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid), session
    )
    if engagement is None:
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    # AC-5: Only ACTIVE engagements can receive deliverables
    if engagement.status != "ACTIVE":
        raise PreconditionFailedError("Deliverable can only be submitted on ACTIVE engagements")

    # AC-S1: relation is masked for the subject (self-dealing prevention)
    rel = engagement_relation(principal, engagement)

    # AC-S2: Only TALENT can submit deliverables
    if not rel.is_subject:
        raise TransitionForbiddenError("Only talent can submit deliverables")

    # AC-7: Validate skill_id BEFORE writing anything
    skill_id_uuid = None
    if skill_id:
        try:
            skill_id_uuid = uuid.UUID(skill_id)
        except ValueError:
            raise InvalidSkillError(f"Invalid skill_id format: {skill_id}")

        # Verify skill exists and is ACTIVE in database (AC-7)
        skill = session.execute(
            select(Skill).where(Skill.id == skill_id_uuid, Skill.status == "ACTIVE")
        ).scalar_one_or_none()

        if skill is None:
            raise InvalidSkillError(f"Skill {skill_id} not found or is not ACTIVE")

    # Create deliverable with principal's user_id (AC-S3: never from request body)
    submitted_at = datetime.now(timezone.utc)
    deliverable = Deliverable(
        engagement_id=engagement_uuid,
        skill_id=skill_id_uuid,
        title=title,
        description=description,
        submitted_by_user_id=principal.user_id,
        submitted_at=submitted_at,
    )
    session.add(deliverable)
    try:
        session.flush()
    except IntegrityError as e:
        if "fk_" in str(e).lower() or "foreign key" in str(e).lower():
            raise EngagementNotFoundError("Engagement not found")
        raise

    # AC-2, AC-6: Generate SkillSignal if skill_id provided
    if skill_id_uuid is not None:
        signal = SkillSignal(
            talent_id=engagement.talent_id,
            skill_id=skill_id_uuid,
            source_type="DELIVERABLE",
            source_id=deliverable.id,
            strength=DELIVERABLE_SIGNAL_STRENGTH,
            attested_by_org_id=None,
            occurred_at=deliverable.submitted_at,
            superseded_by_id=None,
        )
        session.add(signal)
        session.flush()

    # Log audit event
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="DELIVERABLE_SUBMITTED",
        subject_type="deliverable",
        subject_id=deliverable.id,
        result="SUCCESS",
        metadata={
            "engagement_id": str(engagement_uuid),
            "title": title,
        },
    )

    return deliverable


def get_coordinator_dashboard(
    session: Session,
    principal: Principal,
    institution_id: str,
) -> dict:
    """
    Retrieve coordinator dashboard for an institution (PLAN 3.3 — koordinator-dashboard-ucu).

    Returns summary counts and lists of PENDING_APPROVAL and PENDING_EVALUATION engagements
    for the specified institution, filtered by principal's authorization scope.

    Args:
        session: Database session
        principal: Authorization context (must be COORDINATOR or INST_ADMIN)
        institution_id: UUID of institution (string format)

    Returns:
        dict with keys: institution_id, summary, pending_approval, pending_evaluation

    Raises:
        ValueError: If institution_id is not in principal's scope or institution doesn't exist
    """
    # Parse UUID
    try:
        inst_uuid = uuid.UUID(institution_id)
    except ValueError:
        # Savunma amaçlı: normalde FastAPI path validasyonu (uuid.UUID tip) bu hatayı zaten yakalar
        raise ValueError(f"Invalid institution_id format: {institution_id}")

    # Authorization: Only COORDINATOR and INST_ADMIN can access dashboard
    # Per-institution check: institution_id must be in principal.institution_ids
    if principal.user_id is None:
        raise ValueError("Not authorized to access dashboard")

    if inst_uuid not in principal.institution_ids:
        raise ValueError("Institution not found")

    # Defense-in-depth: verify institution exists in scope
    from app.models import Institution, InstitutionMember, User
    from app.services.authorization import scoped_institutions

    scoped = scoped_institutions(session, principal).where(Institution.id == inst_uuid)
    institution = get_scoped_or_404(scoped, session)

    if institution is None:
        raise ValueError("Institution not found")

    # Query PENDING_APPROVAL engagements for this institution
    pending_approval = (
        session.execute(
            scoped_engagements(session, principal)
            .where(
                Engagement.institution_id == inst_uuid,
                Engagement.status == "PENDING_APPROVAL",
            )
            .order_by(Engagement.created_at.desc())
        )
        .scalars()
        .all()
    )

    # Query PENDING_EVALUATION engagements for this institution
    pending_evaluation = (
        session.execute(
            scoped_engagements(session, principal)
            .where(
                Engagement.institution_id == inst_uuid,
                Engagement.status == "PENDING_EVALUATION",
            )
            .order_by(Engagement.created_at.desc())
        )
        .scalars()
        .all()
    )

    # Query institution members (PLAN 3.5 — üye listesi)
    # AC-S1: Critical security filter — institution_id must be in WHERE clause
    members_query = session.execute(
        select(InstitutionMember, User)
        .join(User, InstitutionMember.user_id == User.id)
        .where(InstitutionMember.institution_id == inst_uuid, User.status == "ACTIVE")
        .order_by(InstitutionMember.created_at.desc())
    ).all()

    # Build response data
    return {
        "institution_id": str(inst_uuid),
        "summary": {
            "pending_approval": len(pending_approval),
            "pending_evaluation": len(pending_evaluation),
        },
        "pending_approval": [
            {
                "id": str(eng.id),
                "talent_id": str(eng.talent_id),
                "organization_id": str(eng.organization_id),
                "title": eng.title,
                "started_on": eng.started_on.isoformat() if eng.started_on else None,
            }
            for eng in pending_approval
        ],
        "pending_evaluation": [
            {
                "id": str(eng.id),
                "talent_id": str(eng.talent_id),
                "organization_id": str(eng.organization_id),
                "title": eng.title,
                "ended_on": eng.ended_on.isoformat() if eng.ended_on else None,
            }
            for eng in pending_evaluation
        ],
        "members": [
            {
                "user_id": str(member.user_id),
                "email": user.email,
                "role": member.role,
                "joined_at": member.created_at.isoformat(),
            }
            for member, user in members_query
        ],
    }


def list_engagements(
    session: Session,
    principal: Principal,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[Engagement, str]]:
    """
    List engagements scoped to principal with organization name (AC-1, AC-2, AC-3, AC-8).

    Returns engagements accessible to principal (by scoped_engagements), sorted by
    updated_at descending, with organization name joined in single query (N+1-free).

    Args:
        session: Database session
        principal: Authorization context
        limit: Number of results per page (default 50)
        offset: Pagination offset (default 0)

    Returns:
        List of (Engagement, organization_name) tuples, sorted by updated_at DESC

    Implements: AC-1 (TALENT), AC-2 (ORG_MEMBER/ORG_ADMIN), AC-3 (COORDINATOR/INST_ADMIN),
                AC-8 (limit/offset pagination)
    """
    # Build scoped query and extend with Organization JOIN, order by, and pagination
    # scoped_engagements() returns a Select[Engagement] filtered by principal's scope
    scoped = scoped_engagements(session, principal)

    # Fetch Engagement objects scoped to principal
    stmt = scoped.order_by(Engagement.updated_at.desc()).limit(limit).offset(offset)
    engagements = session.execute(stmt).scalars().all()

    # Fetch all Organization names in a single batch query (not N+1: exactly 2 SQL queries)
    # Query 1: Engagements above, Query 2: Organizations below via WHERE id IN (...)
    org_ids = set(e.organization_id for e in engagements)
    if org_ids:
        orgs = (
            session.execute(select(Organization).where(Organization.id.in_(org_ids)))
            .scalars()
            .all()
        )
        org_map = {o.id: o.name for o in orgs}
    else:
        org_map = {}

    # Return list of (Engagement, organization_name) tuples
    return [(eng, org_map.get(eng.organization_id, "")) for eng in engagements]


def get_engagement_detail(
    session: Session,
    principal: Principal,
    engagement_id: str,
) -> tuple[Engagement, str, Sequence[EngagementTask], Sequence[Deliverable], Sequence[Attestation]]:
    """
    Get engagement detail with tasks, deliverables, and attestations (AC-4, AC-5, AC-6).

    Fetches engagement from principal's scope, retrieves organization name, and
    fetches associated tasks, deliverables, and attestations in separate queries.

    Args:
        session: Database session
        principal: Authorization context
        engagement_id: UUID of engagement (string format)

    Returns:
        Tuple of (Engagement, organization_name, tasks[], deliverables[], attestations[])

    Raises:
        EngagementNotFoundError: Engagement not in principal's scope or doesn't exist (404)

    Implements: AC-4 (detail response), AC-5 (out-of-scope 404), AC-6 (nonexistent 404)
    """
    # Parse UUID
    try:
        engagement_uuid = uuid.UUID(engagement_id)
    except ValueError:
        raise EngagementNotFoundError(f"Invalid engagement_id format: {engagement_id}")

    # Fetch engagement scoped to principal — uses exact same pattern as transition_engagement
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_uuid), session
    )
    if engagement is None:
        # Both "out-of-scope" and "doesn't exist" return 404 per AC-5/AC-6
        raise EngagementNotFoundError(f"Engagement {engagement_id} not found")

    # Fetch organization_name via JOIN (single query, not N+1)
    # FK constraint guarantees organization exists, so scalar_one() is safe
    org_query = session.execute(
        select(Organization.name).where(Organization.id == engagement.organization_id)
    )
    organization_name = org_query.scalar_one()

    # Fetch tasks (WHERE engagement_id = :id, single query)
    tasks_query = session.execute(
        select(EngagementTask).where(EngagementTask.engagement_id == engagement.id)
    )
    tasks = tasks_query.scalars().all()

    # Fetch deliverables (WHERE engagement_id = :id, single query)
    deliverables_query = session.execute(
        select(Deliverable).where(Deliverable.engagement_id == engagement.id)
    )
    deliverables = deliverables_query.scalars().all()

    # Fetch attestations (WHERE engagement_id = :id, single query) — YET-202/ENT-01:
    # frontend needs this list to show a "Geri Çek" (revoke) action per attestation.
    # engagement_id is already proven in-scope above (scoped_engagements), so this
    # follows the exact same already-established pattern as tasks/deliverables.
    attestations_query = session.execute(
        select(Attestation).where(Attestation.engagement_id == engagement.id)
    )
    attestations = attestations_query.scalars().all()

    return engagement, organization_name, tasks, deliverables, attestations
