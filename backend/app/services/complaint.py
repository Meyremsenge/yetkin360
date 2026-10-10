"""
Complaint (Şikayet) service — sikayet-backend, C1–C7. All complaint business logic lives here.

Flow: a talent complains about an approval that stayed unanswered → the platform
admin reviews, may ask the derived respondent for an explanation, may escalate to
the other deciding members of the target institution/organization, and decides.
Only an admin decision (UPHOLD) counts toward the public `upheld_complaint_count`
— no algorithm, no score (user-approved narrowing of the "no trust score" rule).

Rules kept here:
- Target and respondent are derived server-side from the subject, never taken from the body.
- Every status change writes complaint_events + audit_events (+ outbox when someone is
  notified) in the caller's single transaction. Texts never go to audit/outbox/logs.
- Network calls (object storage) only after the read transaction is committed
  (same pattern as evidence.get_download_url).
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.config import settings
from app.core.errors import ApiError
from app.models import (
    AuditEvent,
    CertificateCheck,
    Complaint,
    ComplaintAttachment,
    ComplaintEvent,
    Deliverable,
    Engagement,
    Evidence,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
)
from app.models.complaint import ATTACHMENT_MIME_TYPES, TERMINAL_STATUSES
from app.schemas.complaint import (
    AdminComplaintDetail,
    AdminComplaintListItem,
    AdminComplaintListResponse,
    AttachmentDownloadResponse,
    AttachmentResponse,
    AttachmentUploadUrlResponse,
    ComplaintCreatedResponse,
    ComplaintEventResponse,
    ComplaintRespondentListResponse,
    ComplaintRespondentView,
    ComplaintStudentListResponse,
    ComplaintStudentView,
)
from app.services.audit import log_audit_event
from app.services.authorization import (
    Principal,
    get_scoped_or_404,
    scoped_admin_complaints,
    scoped_complaints,
    scoped_engagements,
    scoped_evidence,
    scoped_owned_complaints,
    scoped_upheld_complaint_counts,
)
from app.services.evidence_scan import inspect_content
from app.services.outbox import enqueue
from app.services.storage import (
    CONTENT_TYPE_TO_EXT,
    fetch_object,
    generate_presigned_get_url,
    generate_presigned_post,
    head_object_etag,
)

DAILY_COMPLAINT_LIMIT = 3
MAX_ATTACHMENTS = 5
PENDING_ENGAGEMENT_STATES = ("PENDING_APPROVAL", "PENDING_EVALUATION")
CERTIFICATE_PENDING_STATE = "PENDING_DECISION"

_UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "Kaynak bulunamadı.")


def _invalid_transition() -> ApiError:
    return ApiError(409, "INVALID_TRANSITION", "Bu işlem şikayetin mevcut durumunda yapılamaz.")


def _closed() -> ApiError:
    return ApiError(409, "COMPLAINT_CLOSED", "Kapanmış şikayete belge eklenemez.")


def status_label(status: str) -> str:
    """The talent only ever sees 'in progress' or the final outcome (AC-19)."""
    return status if status in TERMINAL_STATUSES else "IN_PROGRESS"


# ============================================================================
# Subject / target / respondent derivation
# ============================================================================


@dataclass(frozen=True)
class _Subject:
    engagement_id: uuid.UUID | None
    certificate_check_id: uuid.UUID | None
    state: str
    pending_since: datetime
    target_type: str
    target_id: uuid.UUID
    engagement: Engagement


def _not_pending() -> ApiError:
    return ApiError(409, "NOT_PENDING", "Bu kayıt onay beklemiyor.")


def _engagement_pending_since(session: Session, engagement: Engagement) -> datetime:
    """When the engagement entered its current status: the latest transition audit row, else creation."""
    entered = session.execute(
        select(func.max(AuditEvent.created_at)).where(
            AuditEvent.action == "ENGAGEMENT_TRANSITIONED",
            AuditEvent.subject_id == engagement.id,
            AuditEvent.event_metadata["to_status"].astext == engagement.status,
        )
    ).scalar_one_or_none()
    return entered or engagement.created_at


def _resolve_subject(session: Session, principal: Principal, subject_type: str, subject_id: uuid.UUID) -> _Subject:
    if principal.talent_id is None:
        raise _not_found()

    if subject_type == "ENGAGEMENT":
        engagement = get_scoped_or_404(
            scoped_engagements(session, principal).where(
                Engagement.id == subject_id, Engagement.talent_id == principal.talent_id
            ),
            session,
        )
        if engagement is None:
            raise _not_found()
        if engagement.status not in PENDING_ENGAGEMENT_STATES:
            raise _not_pending()
        if engagement.status == "PENDING_APPROVAL":
            if engagement.institution_id is None:
                raise _not_pending()
            target_type, target_id = "INSTITUTION", engagement.institution_id
        else:
            target_type, target_id = "ORGANIZATION", engagement.organization_id
        return _Subject(
            engagement_id=engagement.id,
            certificate_check_id=None,
            state=engagement.status,
            pending_since=_engagement_pending_since(session, engagement),
            target_type=target_type,
            target_id=target_id,
            engagement=engagement,
        )

    # CERTIFICATE_CHECK: ownership goes through the talent's own evidence.
    row = session.execute(
        scoped_evidence(session, principal)
        .join(CertificateCheck, CertificateCheck.evidence_id == Evidence.id)
        .where(CertificateCheck.id == subject_id)
        .add_columns(CertificateCheck)
    ).first()
    if row is None:
        raise _not_found()
    evidence, check = row
    if check.decision != "PENDING" or evidence.deliverable_id is None:
        raise _not_pending()
    engagement = session.execute(
        select(Engagement)
        .join(Deliverable, Deliverable.engagement_id == Engagement.id)
        .where(Deliverable.id == evidence.deliverable_id, Engagement.talent_id == principal.talent_id)
    ).scalars().first()
    if engagement is None:
        raise _not_pending()
    if engagement.institution_id is not None:
        target_type, target_id = "INSTITUTION", engagement.institution_id
    else:
        target_type, target_id = "ORGANIZATION", engagement.organization_id
    return _Subject(
        engagement_id=None,
        certificate_check_id=check.id,
        state=CERTIFICATE_PENDING_STATE,
        pending_since=check.requested_by_talent_at,
        target_type=target_type,
        target_id=target_id,
        engagement=engagement,
    )


def _derive_respondent(session: Session, subject: _Subject) -> uuid.UUID | None:
    """
    (assumption, atdd.md) Institution → earliest COORDINATOR, else earliest ADMIN.
    Organization → the engagement's supervisor if they belong to the organization,
    else the earliest ACTIVE ADMIN. None when nobody can answer.
    """
    if subject.target_type == "INSTITUTION":
        for role in ("COORDINATOR", "ADMIN"):
            user_id = session.execute(
                select(InstitutionMember.user_id)
                .where(InstitutionMember.institution_id == subject.target_id, InstitutionMember.role == role)
                .order_by(InstitutionMember.created_at, InstitutionMember.id)
                .limit(1)
            ).scalar_one_or_none()
            if user_id is not None:
                return user_id
        return None

    supervisor = subject.engagement.supervisor_user_id
    if supervisor is not None:
        is_member = session.execute(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == subject.target_id,
                OrganizationMember.user_id == supervisor,
                OrganizationMember.status == "ACTIVE",
            )
        ).first()
        if is_member is not None:
            return supervisor
    return session.execute(
        select(OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == subject.target_id,
            OrganizationMember.role == "ADMIN",
            OrganizationMember.status == "ACTIVE",
        )
        .order_by(OrganizationMember.created_at, OrganizationMember.id)
        .limit(1)
    ).scalar_one_or_none()


def _subject_pending(session: Session, complaint: Complaint) -> bool:
    """AC-21: is the subject still waiting in the state it was in when the complaint was opened?"""
    if complaint.subject_type == "ENGAGEMENT":
        status = session.execute(
            select(Engagement.status).where(Engagement.id == complaint.engagement_id)
        ).scalar_one_or_none()
        return status == complaint.subject_state
    decision = session.execute(
        select(CertificateCheck.decision).where(CertificateCheck.id == complaint.certificate_check_id)
    ).scalar_one_or_none()
    return decision == "PENDING"


# ============================================================================
# Events / audit
# ============================================================================


def _record(
    session: Session,
    complaint: Complaint,
    principal: Principal,
    actor_role: str,
    event_type: str,
    from_status: str | None,
    note: str | None = None,
) -> None:
    session.add(
        ComplaintEvent(
            complaint_id=complaint.id,
            actor_user_id=principal.user_id,
            actor_role=actor_role,
            event_type=event_type,
            from_status=from_status,
            to_status=complaint.status,
            note=note,
        )
    )
    session.flush()


def _audit(
    session: Session, principal: Principal, action: str, subject_type: str, subject_id: uuid.UUID, meta: dict | None = None
) -> None:
    log_audit_event(
        session=session,
        actor_user_id=principal.user_id,
        actor_ip=None,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        result="SUCCESS",
        metadata=meta,
    )


# ============================================================================
# Talent: open + list + read
# ============================================================================


def create_complaint(
    session: Session, principal: Principal, subject_type: str, subject_id: uuid.UUID, description: str
) -> ComplaintCreatedResponse:
    """
    Raises ApiError: 404 subject not the caller's, 409 NOT_PENDING / TOO_EARLY / ALREADY_OPEN,
    429 RATE_LIMITED (more than DAILY_COMPLAINT_LIMIT complaints in 24 hours).
    """
    subject = _resolve_subject(session, principal, subject_type, subject_id)

    # Serialize this talent's complaint creation so the 24-hour count cannot be raced.
    session.execute(select(TalentProfile.id).where(TalentProfile.id == principal.talent_id).with_for_update())
    recent = session.execute(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.talent_id == principal.talent_id, Complaint.created_at > _now() - timedelta(hours=24))
    ).scalar_one()
    if recent >= DAILY_COMPLAINT_LIMIT:
        raise ApiError(429, "RATE_LIMITED", "24 saat içinde en fazla 3 şikayet açılabilir.")

    if subject.pending_since > _now() - timedelta(days=settings.complaint_min_wait_days):
        raise ApiError(
            409,
            "TOO_EARLY",
            f"Şikayet için onay talebinin en az {settings.complaint_min_wait_days} gün yanıtsız kalması gerekir.",
        )

    complaint = Complaint(
        talent_id=principal.talent_id,
        subject_type=subject_type,
        engagement_id=subject.engagement_id,
        certificate_check_id=subject.certificate_check_id,
        subject_state=subject.state,
        target_type=subject.target_type,
        target_institution_id=subject.target_id if subject.target_type == "INSTITUTION" else None,
        target_organization_id=subject.target_id if subject.target_type == "ORGANIZATION" else None,
        respondent_user_id=_derive_respondent(session, subject),
        description=description,
        status="OPEN",
        version=1,
    )
    session.add(complaint)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        if "uq_complaints_open_" not in str(exc.orig):
            raise
        raise ApiError(409, "ALREADY_OPEN", "Bu kayıt için zaten açık bir şikayetiniz var.") from exc

    _record(session, complaint, principal, "TALENT", "CREATED", None)
    _audit(session, principal, "complaint.created", "complaint", complaint.id, {"subject_type": subject_type})
    session.refresh(complaint)
    return ComplaintCreatedResponse(
        id=complaint.id,
        status="OPEN",
        status_label="IN_PROGRESS",
        subject_type=complaint.subject_type,  # type: ignore[arg-type]
        subject_id=complaint.subject_id,
        created_at=complaint.created_at,
    )


def _attachments_of(session: Session, complaint_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[AttachmentResponse]]:
    by_complaint: dict[uuid.UUID, list[AttachmentResponse]] = {cid: [] for cid in complaint_ids}
    if not complaint_ids:
        return by_complaint
    rows = session.execute(
        select(ComplaintAttachment)
        .where(ComplaintAttachment.complaint_id.in_(complaint_ids))
        .order_by(ComplaintAttachment.created_at, ComplaintAttachment.id)
    ).scalars().all()
    for a in rows:
        by_complaint[a.complaint_id].append(
            AttachmentResponse(id=a.id, mime_type=a.mime_type, size_bytes=a.size_bytes, created_at=a.created_at)
        )
    return by_complaint


def _student_view(complaint: Complaint, attachments: list[AttachmentResponse]) -> ComplaintStudentView:
    terminal = complaint.status in TERMINAL_STATUSES
    return ComplaintStudentView(
        id=complaint.id,
        subject_type=complaint.subject_type,  # type: ignore[arg-type]
        subject_id=complaint.subject_id,
        status_label=status_label(complaint.status),  # type: ignore[arg-type]
        description=complaint.description,
        resolution_reason=complaint.resolution_reason if terminal else None,
        created_at=complaint.created_at,
        closed_at=complaint.closed_at,
        attachments=attachments,
    )


def _respondent_view(complaint: Complaint) -> ComplaintRespondentView:
    return ComplaintRespondentView(
        id=complaint.id,
        subject_type=complaint.subject_type,  # type: ignore[arg-type]
        subject_id=complaint.subject_id,
        status=complaint.status,  # type: ignore[arg-type]
        request_note=complaint.request_note,
        explanation_due_at=complaint.explanation_due_at,
        explanation_text=complaint.explanation_text,
        created_at=complaint.created_at,
    )


def list_own_complaints(session: Session, principal: Principal, limit: int, offset: int) -> ComplaintStudentListResponse:
    rows = session.execute(
        scoped_owned_complaints(session, principal)
        .order_by(Complaint.created_at.desc(), Complaint.id.desc())
        .offset(offset)
        .limit(limit + 1)
    ).scalars().all()
    page = list(rows[:limit])
    attachments = _attachments_of(session, [c.id for c in page])
    return ComplaintStudentListResponse(
        items=[_student_view(c, attachments[c.id]) for c in page], limit=limit, offset=offset, has_more=len(rows) > limit
    )


def list_assigned_complaints(
    session: Session, principal: Principal, limit: int, offset: int
) -> ComplaintRespondentListResponse:
    """Complaints the caller must answer or was escalated to — never their own as a talent."""
    query = scoped_complaints(session, principal)
    if principal.talent_id is not None:
        query = query.where(Complaint.talent_id != principal.talent_id)
    rows = session.execute(
        query.order_by(Complaint.created_at.desc(), Complaint.id.desc()).offset(offset).limit(limit + 1)
    ).scalars().all()
    return ComplaintRespondentListResponse(
        items=[_respondent_view(c) for c in rows[:limit]], limit=limit, offset=offset, has_more=len(rows) > limit
    )


def get_complaint_view(
    session: Session, principal: Principal, complaint_id: uuid.UUID
) -> ComplaintStudentView | ComplaintRespondentView:
    complaint = get_scoped_or_404(scoped_complaints(session, principal).where(Complaint.id == complaint_id), session)
    if complaint is None:
        raise _not_found()
    if principal.talent_id is not None and complaint.talent_id == principal.talent_id:
        return _student_view(complaint, _attachments_of(session, [complaint.id])[complaint.id])
    return _respondent_view(complaint)


# ============================================================================
# Respondent: explanation (C5)
# ============================================================================


def submit_explanation(session: Session, principal: Principal, complaint_id: uuid.UUID, text: str) -> ComplaintRespondentView:
    """Only the derived respondent, only in EXPLANATION_REQUESTED, only once."""
    complaint = get_scoped_or_404(
        scoped_complaints(session, principal).where(Complaint.id == complaint_id).with_for_update(), session
    )
    if complaint is None:
        raise _not_found()
    is_owner = principal.talent_id is not None and complaint.talent_id == principal.talent_id
    if is_owner:
        raise _not_found()
    if complaint.respondent_user_id != principal.user_id or complaint.status != "EXPLANATION_REQUESTED":
        raise _invalid_transition()

    from_status = complaint.status
    complaint.status = "EXPLANATION_SUBMITTED"
    complaint.explanation_text = text
    complaint.explanation_submitted_at = _now()
    complaint.version += 1
    complaint.updated_at = _now()
    session.flush()
    _record(session, complaint, principal, "RESPONDENT", "EXPLANATION_SUBMITTED", from_status, note=text)
    _audit(
        session,
        principal,
        "complaint.transitioned",
        "complaint",
        complaint.id,
        {"from_status": from_status, "to_status": complaint.status},
    )
    return _respondent_view(complaint)


# ============================================================================
# Admin: queue, detail, transitions (C3, C4)
# ============================================================================


def _target_names(session: Session, complaints: list[Complaint]) -> dict[uuid.UUID, str]:
    inst_ids = [c.target_institution_id for c in complaints if c.target_institution_id is not None]
    org_ids = [c.target_organization_id for c in complaints if c.target_organization_id is not None]
    names: dict[uuid.UUID, str] = {}
    if inst_ids:
        names.update(session.execute(select(Institution.id, Institution.name).where(Institution.id.in_(inst_ids))).tuples().all())
    if org_ids:
        names.update(
            session.execute(select(Organization.id, Organization.name).where(Organization.id.in_(org_ids))).tuples().all()
        )
    return names


def _admin_item_fields(session: Session, complaint: Complaint, names: dict[uuid.UUID, str], attachment_count: int) -> dict:
    return dict(
        id=complaint.id,
        status=complaint.status,
        subject_type=complaint.subject_type,
        subject_id=complaint.subject_id,
        subject_pending=_subject_pending(session, complaint),
        target_type=complaint.target_type,
        target_id=complaint.target_id,
        target_name=names.get(complaint.target_id),
        attachment_count=attachment_count,
        explanation_due_at=complaint.explanation_due_at,
        created_at=complaint.created_at,
    )


def list_admin_complaints(
    session: Session, principal: Principal, status: str | None, limit: int, offset: int
) -> AdminComplaintListResponse:
    """Oldest first (fairness). Without a status filter: the open queue (non-terminal)."""
    query = scoped_admin_complaints(session, principal)
    if status is None:
        query = query.where(Complaint.status.not_in(TERMINAL_STATUSES))
    else:
        query = query.where(Complaint.status == status)
    rows = session.execute(
        query.order_by(Complaint.created_at.asc(), Complaint.id.asc()).offset(offset).limit(limit + 1)
    ).scalars().all()
    page = list(rows[:limit])
    names = _target_names(session, page)
    counts: dict[uuid.UUID, int] = {}
    if page:
        counts = dict(
            session.execute(
                select(ComplaintAttachment.complaint_id, func.count())
                .where(ComplaintAttachment.complaint_id.in_([c.id for c in page]))
                .group_by(ComplaintAttachment.complaint_id)
            ).tuples().all()
        )
    return AdminComplaintListResponse(
        items=[AdminComplaintListItem(**_admin_item_fields(session, c, names, counts.get(c.id, 0))) for c in page],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )


def _admin_get(session: Session, principal: Principal, complaint_id: uuid.UUID, lock: bool = False) -> Complaint:
    query = scoped_admin_complaints(session, principal).where(Complaint.id == complaint_id)
    if lock:
        query = query.with_for_update()
    complaint = get_scoped_or_404(query, session)
    if complaint is None:
        raise _not_found()
    return complaint


def _admin_detail(session: Session, complaint: Complaint) -> AdminComplaintDetail:
    attachments = _attachments_of(session, [complaint.id])[complaint.id]
    events = session.execute(
        select(ComplaintEvent)
        .where(ComplaintEvent.complaint_id == complaint.id)
        .order_by(ComplaintEvent.created_at, ComplaintEvent.id)
    ).scalars().all()
    talent_name = session.execute(
        select(TalentProfile.full_name).where(TalentProfile.id == complaint.talent_id)
    ).scalar_one_or_none()
    return AdminComplaintDetail(
        **_admin_item_fields(session, complaint, _target_names(session, [complaint]), len(attachments)),
        talent_id=complaint.talent_id,
        talent_name=talent_name,
        description=complaint.description,
        respondent_user_id=complaint.respondent_user_id,
        request_note=complaint.request_note,
        explanation_text=complaint.explanation_text,
        resolution_reason=complaint.resolution_reason,
        version=complaint.version,
        closed_at=complaint.closed_at,
        attachments=attachments,
        events=[
            ComplaintEventResponse(
                id=e.id,
                event_type=e.event_type,
                from_status=e.from_status,
                to_status=e.to_status,
                actor_role=e.actor_role,
                actor_user_id=e.actor_user_id,
                note=e.note,
                created_at=e.created_at,
            )
            for e in events
        ],
    )


def get_admin_complaint(session: Session, principal: Principal, complaint_id: uuid.UUID) -> AdminComplaintDetail:
    return _admin_detail(session, _admin_get(session, principal, complaint_id))


def _required(value: str | None, field: str) -> str:
    if not value or not value.strip():
        raise ApiError(422, "VALIDATION_ERROR", f"'{field}' alanı zorunludur.")
    return value


def _move(
    session: Session,
    principal: Principal,
    complaint: Complaint,
    to_status: str,
    event_type: str,
    note: str | None = None,
) -> None:
    from_status = complaint.status
    now = _now()
    complaint.status = to_status
    complaint.version += 1
    complaint.updated_at = now
    if to_status in TERMINAL_STATUSES:
        complaint.closed_at = now
    session.flush()
    _record(session, complaint, principal, "ADMIN", event_type, from_status, note=note)
    _audit(
        session,
        principal,
        "complaint.transitioned",
        "complaint",
        complaint.id,
        {"from_status": from_status, "to_status": to_status},
    )
    if to_status in TERMINAL_STATUSES:
        enqueue(
            session,
            "complaint.closed",
            {"complaint_id": str(complaint.id), "talent_id": str(complaint.talent_id), "outcome": to_status},
        )


def transition_complaint(
    session: Session,
    principal: Principal,
    complaint_id: uuid.UUID,
    action: str,
    note: str | None = None,
    reason: str | None = None,
    version: int | None = None,
) -> AdminComplaintDetail:
    """
    Admin decision (AC-16…AC-21). The row is locked (SELECT … FOR UPDATE) so two
    concurrent decisions serialize; the second sees the new status → 409.

    Raises ApiError: 404, 409 INVALID_TRANSITION / VERSION_CONFLICT / NO_RESPONDENT /
    DEADLINE_NOT_REACHED, 422 VALIDATION_ERROR (missing note/reason).
    """
    complaint = _admin_get(session, principal, complaint_id, lock=True)
    if version is not None and version != complaint.version:
        raise ApiError(409, "VERSION_CONFLICT", "Şikayet başka bir işlemle değişti; sayfayı yenileyin.")
    status = complaint.status
    if status in TERMINAL_STATUSES:
        raise _invalid_transition()

    if action == "START_REVIEW":
        if status != "OPEN":
            raise _invalid_transition()
        _move(session, principal, complaint, "UNDER_REVIEW", "REVIEW_STARTED")

    elif action in ("DISMISS", "REQUEST_EXPLANATION"):
        if status not in ("OPEN", "UNDER_REVIEW"):
            raise _invalid_transition()
        text = _required(reason if action == "DISMISS" else note, "reason" if action == "DISMISS" else "note")
        if action == "REQUEST_EXPLANATION" and complaint.respondent_user_id is None:
            raise ApiError(409, "NO_RESPONDENT", "Bu şikayet için gerekçe istenecek bir yetkili bulunamadı.")
        if status == "OPEN":
            _move(session, principal, complaint, "UNDER_REVIEW", "REVIEW_STARTED")
        if action == "DISMISS":
            complaint.resolution_reason = text
            _move(session, principal, complaint, "DISMISSED", "DISMISSED", note=text)
        else:
            now = _now()
            complaint.request_note = text
            complaint.explanation_requested_at = now
            complaint.explanation_due_at = now + timedelta(days=settings.complaint_explanation_days)
            _move(session, principal, complaint, "EXPLANATION_REQUESTED", "EXPLANATION_REQUESTED", note=text)
            enqueue(
                session,
                "complaint.explanation_requested",
                {"complaint_id": str(complaint.id), "respondent_user_id": str(complaint.respondent_user_id)},
            )

    elif action == "ACCEPT_EXPLANATION":
        if status != "EXPLANATION_SUBMITTED":
            raise _invalid_transition()
        complaint.resolution_reason = reason
        _move(session, principal, complaint, "RESOLVED", "EXPLANATION_ACCEPTED", note=reason)

    elif action == "REJECT_EXPLANATION":
        if status == "EXPLANATION_REQUESTED":
            due = complaint.explanation_due_at
            if due is None or due > _now():
                raise ApiError(409, "DEADLINE_NOT_REACHED", "Yetkilinin gerekçe süresi henüz dolmadı.")
        elif status != "EXPLANATION_SUBMITTED":
            raise _invalid_transition()
        complaint.escalated_at = _now()
        _move(session, principal, complaint, "ESCALATED", "EXPLANATION_REJECTED", note=reason)
        enqueue(
            session,
            "complaint.escalated",
            {
                "complaint_id": str(complaint.id),
                "target_type": complaint.target_type,
                "target_id": str(complaint.target_id),
                "excluded_user_id": str(complaint.respondent_user_id) if complaint.respondent_user_id else None,
            },
        )

    elif action == "RESOLVE":
        if status != "ESCALATED" and _subject_pending(session, complaint):
            raise _invalid_transition()
        complaint.resolution_reason = reason
        _move(session, principal, complaint, "RESOLVED", "RESOLVED", note=reason)

    elif action == "UPHOLD":
        if status != "ESCALATED":
            raise _invalid_transition()
        complaint.resolution_reason = reason
        _move(session, principal, complaint, "UPHELD", "UPHELD", note=reason)

    else:  # pragma: no cover — TransitionRequest restricts the literal
        raise _invalid_transition()

    return _admin_detail(session, complaint)


# ============================================================================
# Attachments (C2, C3)
# ============================================================================


def _owned_open_complaint(session: Session, principal: Principal, complaint_id: uuid.UUID, lock: bool = False) -> Complaint:
    query = scoped_owned_complaints(session, principal).where(Complaint.id == complaint_id)
    if lock:
        query = query.with_for_update()
    complaint = get_scoped_or_404(query, session)
    if complaint is None:
        raise _not_found()
    if complaint.status in TERMINAL_STATUSES:
        raise _closed()
    return complaint


def _validate_file(mime_type: str, size_bytes: int) -> str:
    if mime_type not in ATTACHMENT_MIME_TYPES:
        raise ApiError(422, "UNSUPPORTED_CONTENT_TYPE", "Desteklenmeyen dosya türü. İzin verilen türler: PDF, JPEG, PNG.")
    if size_bytes > settings.evidence_max_size_bytes:
        raise ApiError(422, "FILE_TOO_LARGE", "Dosya çok büyük. En fazla 10 MB yüklenebilir.")
    return CONTENT_TYPE_TO_EXT[mime_type]


def _storage_unavailable() -> ApiError:
    return ApiError(
        503, "STORAGE_UNAVAILABLE", "Dosya depolama servisi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin."
    )


def create_attachment_upload_url(
    session: Session, principal: Principal, complaint_id: uuid.UUID, content_type: str, size_bytes: int
) -> AttachmentUploadUrlResponse:
    """Presigned POST bound to type and exact size; the key never contains the client file name."""
    complaint = _owned_open_complaint(session, principal, complaint_id)
    ext = _validate_file(content_type, size_bytes)
    object_key = f"complaints/{complaint.id}/{uuid7()}.{ext}"
    session.commit()  # signing is local, but keep the rule: nothing outward with a transaction open
    try:
        presigned = generate_presigned_post(
            bucket=settings.s3_bucket,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            ttl=settings.s3_presigned_url_ttl_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        raise _storage_unavailable() from exc
    return AttachmentUploadUrlResponse(
        upload_url=presigned["url"],
        upload_fields=presigned["fields"],
        object_key=object_key,
        expires_in=settings.s3_presigned_url_ttl_seconds,
    )


def register_attachment(
    session: Session, principal: Principal, complaint_id: uuid.UUID, storage_key: str, mime_type: str, size_bytes: int
) -> AttachmentResponse:
    """
    Read the uploaded object (outside any transaction), check magic bytes + exact size
    (evidence_scan.inspect_content), then record it. Max MAX_ATTACHMENTS per complaint,
    counted under a row lock.
    """
    complaint = _owned_open_complaint(session, principal, complaint_id)
    if not storage_key.startswith(f"complaints/{complaint.id}/"):
        raise _not_found()
    ext = _validate_file(mime_type, size_bytes)
    if not re.fullmatch(rf"complaints/{complaint.id}/{_UUID_RE}\.{re.escape(ext)}", storage_key):
        raise ApiError(422, "INVALID_STORAGE_KEY", "Belge referansı geçersiz.")

    session.commit()  # end the read transaction before the network read
    try:
        stored = fetch_object(settings.s3_bucket, storage_key, settings.evidence_max_size_bytes)
    except (BotoCoreError, ClientError) as exc:
        raise _storage_unavailable() from exc
    if stored is None:
        raise ApiError(422, "UPLOAD_NOT_FOUND", "Yüklenen dosya bulunamadı; dosyayı yeniden yükleyin.")
    verdict = inspect_content(stored.data, mime_type, size_bytes)
    if verdict.status != "CLEAN" or verdict.content_hash is None:
        raise ApiError(422, "INVALID_FILE_CONTENT", "Dosya içeriği beyan edilen türle uyuşmuyor.")

    complaint = _owned_open_complaint(session, principal, complaint_id, lock=True)
    count = session.execute(
        select(func.count()).select_from(ComplaintAttachment).where(ComplaintAttachment.complaint_id == complaint.id)
    ).scalar_one()
    if count >= MAX_ATTACHMENTS:
        raise ApiError(409, "ATTACHMENT_LIMIT_REACHED", "Bir şikayete en fazla 5 belge eklenebilir.")

    attachment = ComplaintAttachment(
        complaint_id=complaint.id,
        uploaded_by_user_id=principal.user_id,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
        content_hash=verdict.content_hash,
        storage_etag=stored.etag,
    )
    session.add(attachment)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        if "uq_complaint_attachments_storage_key" not in str(exc.orig):
            raise
        raise ApiError(409, "ATTACHMENT_ALREADY_REGISTERED", "Bu dosya zaten eklenmiş.") from exc
    _record(session, complaint, principal, "TALENT", "ATTACHMENT_ADDED", complaint.status)
    _audit(session, principal, "complaint.attachment_added", "complaint_attachment", attachment.id)
    session.refresh(attachment)
    return AttachmentResponse(
        id=attachment.id, mime_type=attachment.mime_type, size_bytes=attachment.size_bytes, created_at=attachment.created_at
    )


def _download(
    session: Session, principal: Principal, complaint: Complaint | None, attachment_id: uuid.UUID
) -> AttachmentDownloadResponse:
    if complaint is None:
        raise _not_found()
    attachment = session.execute(
        select(ComplaintAttachment).where(
            ComplaintAttachment.id == attachment_id, ComplaintAttachment.complaint_id == complaint.id
        )
    ).scalars().first()
    if attachment is None:
        raise _not_found()

    attachment_pk, storage_key, recorded_etag = attachment.id, attachment.storage_key, attachment.storage_etag
    session.commit()  # HEAD is a network call
    current_etag = head_object_etag(settings.s3_bucket, storage_key)
    if recorded_etag is None or current_etag != recorded_etag:
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="complaint.attachment_download_blocked",
            subject_type="complaint_attachment",
            subject_id=attachment_pk,
            result="DENIED",
            metadata={"reason": "content_changed_since_upload"},
        )
        session.commit()  # the 409 below would otherwise roll the audit row back
        raise ApiError(409, "ATTACHMENT_CONTENT_CHANGED", "Belge içeriği yüklendikten sonra değişmiş.")

    url = generate_presigned_get_url(
        bucket=settings.s3_bucket, object_key=storage_key, ttl=settings.evidence_download_url_ttl_seconds
    )
    _audit(session, principal, "complaint.attachment_downloaded", "complaint_attachment", attachment_pk)
    return AttachmentDownloadResponse(download_url=url, expires_in=settings.evidence_download_url_ttl_seconds)


def download_own_attachment(
    session: Session, principal: Principal, complaint_id: uuid.UUID, attachment_id: uuid.UUID
) -> AttachmentDownloadResponse:
    """Owner only — the respondent and escalated members never get the file (AC-S9)."""
    complaint = get_scoped_or_404(
        scoped_owned_complaints(session, principal).where(Complaint.id == complaint_id), session
    )
    return _download(session, principal, complaint, attachment_id)


def download_admin_attachment(
    session: Session, principal: Principal, complaint_id: uuid.UUID, attachment_id: uuid.UUID
) -> AttachmentDownloadResponse:
    """Platform admin; every download is audited (AC-S10). Evidence access is untouched."""
    complaint = get_scoped_or_404(
        scoped_admin_complaints(session, principal).where(Complaint.id == complaint_id), session
    )
    return _download(session, principal, complaint, attachment_id)


# ============================================================================
# Public counter (C7)
# ============================================================================


def upheld_complaint_counts(session: Session, target_type: str, target_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Number of UPHELD complaints per target; targets without any are absent (callers use .get(id, 0))."""
    if not target_ids:
        return {}
    rows = session.execute(scoped_upheld_complaint_counts(session, target_type, target_ids)).tuples().all()
    return {target_id: count for target_id, count in rows}


def upheld_complaint_count(session: Session, target_type: str, target_id: uuid.UUID) -> int:
    return upheld_complaint_counts(session, target_type, [target_id]).get(target_id, 0)
