"""
Complaint service: a student's complaint about an engagement and the admin's decision.

Flow: the engagement's talent opens a complaint (the organization side is not
approving a task/certificate, or a personal problem) → the organization's
members are notified → the platform admin upholds or dismisses it.

An organization's "deliberate non-verification" mark is the number of its
UPHELD complaints (upheld_counts); nothing is stored on the organization.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Complaint, Deliverable, Engagement, Evidence, Organization, TalentProfile
from app.services.audit import log_audit_event
from app.services.authorization import Principal, engagement_relation, get_scoped_or_404, scoped_engagements
from app.services.outbox import enqueue

# A draft has not reached the organization yet, so there is nothing to complain about.
COMPLAINT_BLOCKED_STATUSES = ("DRAFT",)
OPEN = "OPEN"
UPHELD = "UPHELD"
DISMISSED = "DISMISSED"


class ComplaintEngagementNotFoundError(Exception):
    """Engagement does not exist or is outside the principal's scope (→ 404)."""


class ComplaintForbiddenError(Exception):
    """Principal sees the engagement but is not its talent (→ 403)."""


class ComplaintPreconditionError(Exception):
    """Engagement is in a status a complaint cannot be opened for (→ 422)."""


class ComplaintEvidenceInvalidError(Exception):
    """evidence_id is not a clean evidence of the student on this engagement (→ 422)."""


class ComplaintAlreadyOpenError(Exception):
    """The engagement already has an open complaint (→ 409)."""


class ComplaintNotOpenError(Exception):
    """The complaint was already decided (→ 409)."""


@dataclass(frozen=True)
class ComplaintQueueRow:
    """A complaint with the labels the admin screen shows next to it."""

    complaint: Complaint
    talent_name: str
    organization_name: str
    engagement_title: str
    engagement_status: str
    # UPHELD complaints of the organization: its "deliberate non-verification" count.
    organization_upheld_count: int


def _own_engagement(session: Session, principal: Principal, engagement_id: uuid.UUID) -> Engagement:
    """The engagement, only for its talent: 404 outside the scope, 403 for another in-scope role."""
    engagement = get_scoped_or_404(
        scoped_engagements(session, principal).where(Engagement.id == engagement_id), session
    )
    if engagement is None:
        raise ComplaintEngagementNotFoundError(str(engagement_id))
    if not engagement_relation(principal, engagement).is_subject:
        raise ComplaintForbiddenError(str(engagement_id))
    return engagement


def create_complaint(
    session: Session,
    principal: Principal,
    engagement_id: uuid.UUID,
    category: str,
    description: str,
    evidence_id: uuid.UUID | None = None,
) -> Complaint:
    """
    Open a complaint on the principal's own engagement and notify the organization.

    Raises ComplaintEngagementNotFoundError, ComplaintForbiddenError,
    ComplaintPreconditionError, ComplaintEvidenceInvalidError, ComplaintAlreadyOpenError.
    """
    engagement = _own_engagement(session, principal, engagement_id)
    if engagement.status in COMPLAINT_BLOCKED_STATUSES:
        raise ComplaintPreconditionError(engagement.status)

    if evidence_id is not None:
        # Only the student's own, scanned file uploaded for this engagement: attaching
        # it is what lets the admin see it.
        attachable = session.execute(
            select(Evidence.id)
            .join(Deliverable, Evidence.deliverable_id == Deliverable.id)
            .where(
                Evidence.id == evidence_id,
                Evidence.owner_talent_id == engagement.talent_id,
                Evidence.deleted_at.is_(None),
                Evidence.scan_status == "CLEAN",
                Deliverable.engagement_id == engagement.id,
            )
        ).scalar_one_or_none()
        if attachable is None:
            raise ComplaintEvidenceInvalidError(str(evidence_id))

    already_open = session.execute(
        select(Complaint.id).where(Complaint.engagement_id == engagement.id, Complaint.status == OPEN)
    ).scalar_one_or_none()
    if already_open is not None:
        raise ComplaintAlreadyOpenError(str(engagement.id))

    complaint = Complaint(
        engagement_id=engagement.id,
        organization_id=engagement.organization_id,
        talent_id=engagement.talent_id,
        created_by_user_id=principal.user_id,
        category=category,
        description=description.strip(),
        evidence_id=evidence_id,
    )
    session.add(complaint)
    try:
        # A concurrent request can pass the check above; the partial unique index decides.
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ComplaintAlreadyOpenError(str(engagement.id))

    # The statement is the student's personal account: neither audit nor outbox carries it.
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action="COMPLAINT_OPENED",
        subject_type="complaint",
        subject_id=complaint.id,
        result="SUCCESS",
        metadata={"engagement_id": str(engagement.id), "category": category},
    )
    enqueue(
        session=session,
        topic="complaint.opened",
        payload={
            "complaint_id": str(complaint.id),
            "engagement_id": str(engagement.id),
            "organization_id": str(engagement.organization_id),
        },
    )
    return complaint


def list_engagement_complaints(
    session: Session, principal: Principal, engagement_id: uuid.UUID
) -> list[Complaint]:
    """The student's own complaints on the engagement, newest first."""
    engagement = _own_engagement(session, principal, engagement_id)
    return list(
        session.execute(
            select(Complaint)
            .where(Complaint.engagement_id == engagement.id)
            .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        ).scalars()
    )


def upheld_counts(session: Session, organization_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    """UPHELD complaint count per organization (missing key = 0)."""
    if not organization_ids:
        return {}
    rows = session.execute(
        select(Complaint.organization_id, func.count())
        .where(Complaint.organization_id.in_(organization_ids), Complaint.status == UPHELD)
        .group_by(Complaint.organization_id)
    ).all()
    return {organization_id: count for organization_id, count in rows}


def list_complaint_queue(
    session: Session, status: str = OPEN, limit: int = 50, offset: int = 0
) -> list[ComplaintQueueRow]:
    """
    Admin queue. Open complaints oldest first (the longest wait on top); decided
    ones newest decision first.
    """
    order = Complaint.created_at.asc() if status == OPEN else Complaint.decided_at.desc()
    return _labelled(
        session,
        _labelled_select().where(Complaint.status == status).order_by(order, Complaint.id).offset(offset).limit(limit),
    )


def get_complaint_queue_row(session: Session, complaint_id: uuid.UUID) -> ComplaintQueueRow | None:
    """One complaint with its labels, whatever its status."""
    rows = _labelled(session, _labelled_select().where(Complaint.id == complaint_id))
    return rows[0] if rows else None


def _labelled_select() -> Select:
    return (
        select(Complaint, TalentProfile.full_name, Organization.name, Engagement.title, Engagement.status)
        .join(TalentProfile, TalentProfile.id == Complaint.talent_id)
        .join(Organization, Organization.id == Complaint.organization_id)
        .join(Engagement, Engagement.id == Complaint.engagement_id)
    )


def _labelled(session: Session, stmt: Select) -> list[ComplaintQueueRow]:
    rows = session.execute(stmt).all()
    counts = upheld_counts(session, {complaint.organization_id for complaint, *_ in rows})
    return [
        ComplaintQueueRow(
            complaint=complaint,
            talent_name=talent_name,
            organization_name=organization_name,
            engagement_title=engagement_title,
            engagement_status=engagement_status,
            organization_upheld_count=counts.get(complaint.organization_id, 0),
        )
        for complaint, talent_name, organization_name, engagement_title, engagement_status in rows
    ]


def resolve_complaint(
    session: Session,
    complaint_id: uuid.UUID,
    outcome: str,
    note: str | None,
    admin_user_id: uuid.UUID,
) -> Complaint | None:
    """
    Record the admin's decision (UPHELD or DISMISSED) and notify the student.

    Returns None if the complaint does not exist; raises ComplaintNotOpenError
    if it was already decided — the first decision stands.
    """
    complaint = session.execute(
        select(Complaint).where(Complaint.id == complaint_id).with_for_update()
    ).scalar_one_or_none()
    if complaint is None:
        return None
    if complaint.status != OPEN:
        raise ComplaintNotOpenError(str(complaint_id))

    complaint.status = outcome
    complaint.decision_note = (note or "").strip() or None
    complaint.decided_by_user_id = admin_user_id
    complaint.decided_at = datetime.now(timezone.utc)
    session.flush()

    enqueue(
        session=session,
        topic="complaint.resolved",
        payload={
            "complaint_id": str(complaint.id),
            "engagement_id": str(complaint.engagement_id),
            "talent_id": str(complaint.talent_id),
            "outcome": outcome,
        },
    )
    return complaint


def get_complaint_evidence(session: Session, complaint_id: uuid.UUID) -> Evidence | None:
    """
    The document the student attached to the complaint, for the admin deciding it.

    This is the one path on which the admin reads a PRIVATE evidence: the student
    attached it to the complaint for that review. Nothing else of the student's
    files is reachable from here. Returns None if the complaint does not exist,
    has no document, or the document was deleted since.
    """
    return session.execute(
        select(Evidence)
        .join(Complaint, Complaint.evidence_id == Evidence.id)
        .where(Complaint.id == complaint_id, Evidence.deleted_at.is_(None))
    ).scalar_one_or_none()
