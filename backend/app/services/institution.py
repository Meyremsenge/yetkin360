"""Institution service: core business logic for institution management."""

import csv
import io
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import (
    Engagement,
    Institution,
    InstitutionLinkRequest,
    InstitutionMember,
    Organization,
    TalentProfile,
    User,
    VerifiedExperience,
)
from app.services.authorization import (
    Principal,
    scoped_engagements,
    scoped_institution_students,
    scoped_own_institution_link_requests,
)


class DuplicateDomainError(Exception):
    """Raised when creating institution with duplicate domain."""

    pass


class DuplicateLinkRequestError(Exception):
    """Raised when student tries to create duplicate PENDING link request."""

    pass


class AlreadyMemberError(Exception):
    """Raised when inviting user who is already an institution member."""

    pass


def create_institution(
    name: str, domain: str | None, caller_user_id: uuid.UUID, session: Session
) -> Institution:
    """
    Create new institution. Caller becomes ADMIN member.

    AC-1: POST /institutions → 201, T1, caller becomes ADMIN.

    Args:
        name: Institution name (required, non-empty validated in API layer)
        domain: Institution domain (optional, unique if provided)
        caller_user_id: User creating the institution
        session: Database session

    Returns:
        Institution object (T1 verification level, ACTIVE status)

    Raises:
        DuplicateDomainError: If domain already exists
    """
    # Check domain uniqueness (if provided)
    if domain:
        existing = session.execute(
            select(Institution).where(Institution.domain == domain)
        ).scalar_one_or_none()
        if existing:
            raise DuplicateDomainError(f"Domain {domain} already taken")

    # Create institution
    institution = Institution(
        name=name,
        domain=domain,
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(institution)
    session.flush()  # Get institution.id before creating member

    # Add caller as ADMIN member
    admin_member = InstitutionMember(
        institution_id=institution.id,
        user_id=caller_user_id,
        role="ADMIN",
    )
    session.add(admin_member)
    session.flush()

    return institution


def invite_member(
    institution_id: uuid.UUID,
    email: str,
    role: str,
    session: Session,
) -> InstitutionMember:
    """
    Invite user to institution (create InstitutionMember, no UPSERT).

    AC-1/AC-4: POST /institutions/{id}/members → 202 (always).
    AC-1: Bilinen e-posta → member oluştur.
    AC-4: Zaten üye → exception fırlat, router 202 döner.

    Args:
        institution_id: Target institution
        email: Email of user to invite
        role: "ADMIN" or "COORDINATOR"
        session: Database session

    Returns:
        InstitutionMember object (newly created)

    Raises:
        ValueError: If invalid role or user not found
        AlreadyMemberError: If user is already a member (no UPSERT)
    """
    # Validate role (defense-in-depth; router also validates)
    if role not in ("ADMIN", "COORDINATOR"):
        raise ValueError(f"Invalid role: {role}")

    # Find user by email
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise ValueError(f"User {email} not found")

    # Check if already a member
    existing_member = session.execute(
        select(InstitutionMember).where(
            and_(
                InstitutionMember.institution_id == institution_id,
                InstitutionMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    if existing_member:
        # AC-4: Zaten üye → exception, rol değiştirilmez
        raise AlreadyMemberError(f"User {email} is already a member of this institution")

    # Create new member (no UPSERT)
    member = InstitutionMember(
        institution_id=institution_id,
        user_id=user.id,
        role=role,
    )
    session.add(member)
    session.flush()

    return member


def get_institution(session: Session, institution_id: uuid.UUID) -> Institution | None:
    """
    Look up an institution by ID (no scoping — institution existence is not
    tenant-private info; any authenticated student may target any institution
    with a link request, per AC-3 in app/api/institutions.py).
    """
    return session.execute(
        select(Institution).where(Institution.id == institution_id)
    ).scalar_one_or_none()


def request_institution_link(
    institution_id: uuid.UUID,
    talent_profile_id: uuid.UUID,
    session: Session,
) -> InstitutionLinkRequest:
    """
    Create PENDING link request for student to join institution.

    AC-3: POST /institutions/{id}/link-requests → PENDING record.
    AC-8: Duplicate PENDING request → raise error (not silent success).

    Args:
        institution_id: Target institution
        talent_profile_id: Student's talent profile
        session: Database session

    Returns:
        InstitutionLinkRequest (status=PENDING)

    Raises:
        DuplicateLinkRequestError: If PENDING request already exists
    """
    # Check for existing PENDING request
    existing = session.execute(
        select(InstitutionLinkRequest).where(
            and_(
                InstitutionLinkRequest.talent_profile_id == talent_profile_id,
                InstitutionLinkRequest.institution_id == institution_id,
                InstitutionLinkRequest.status == "PENDING",
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise DuplicateLinkRequestError(
            f"Pending link request already exists for talent {talent_profile_id} to institution {institution_id}"
        )

    # Create PENDING request
    link_request = InstitutionLinkRequest(
        talent_profile_id=talent_profile_id,
        institution_id=institution_id,
        status="PENDING",
    )
    session.add(link_request)
    session.flush()

    return link_request


def approve_institution_link(
    request_id: uuid.UUID,
    institution_id: uuid.UUID,
    approver_user_id: uuid.UUID,
    session: Session,
) -> InstitutionLinkRequest:
    """
    Approve link request: mark APPROVED and set TalentProfile.institution_id.

    AC-3b: POST /institutions/{id}/link-requests/{request_id}/approve → APPROVED + link.
    Single transaction: request status + TalentProfile.institution_id both updated.

    Args:
        request_id: InstitutionLinkRequest ID
        institution_id: Institution the caller is authorized for (AC-5/AC-S2 —
            the request must belong to THIS institution; a match on request_id
            alone would let an admin of institution A approve institution B's
            link request)
        approver_user_id: User approving (for audit)
        session: Database session

    Returns:
        InstitutionLinkRequest (status=APPROVED, decided_at/decided_by set)

    Raises:
        ValueError: If request not found, not in this institution, or not PENDING
    """
    link_request = session.execute(
        select(InstitutionLinkRequest).where(
            InstitutionLinkRequest.id == request_id,
            InstitutionLinkRequest.institution_id == institution_id,
        )
    ).scalar_one_or_none()

    if not link_request:
        raise ValueError(f"Link request {request_id} not found")

    if link_request.status != "PENDING":
        raise ValueError(
            f"Link request {request_id} is not PENDING (current status: {link_request.status})"
        )

    # Update request
    link_request.status = "APPROVED"
    link_request.decided_at = datetime.now(timezone.utc)
    link_request.decided_by_user_id = approver_user_id

    # Update talent profile
    talent = session.execute(
        select(TalentProfile).where(TalentProfile.id == link_request.talent_profile_id)
    ).scalar_one_or_none()

    if talent:
        talent.institution_id = link_request.institution_id

    session.flush()
    return link_request


def reject_institution_link(
    request_id: uuid.UUID,
    institution_id: uuid.UUID,
    rejecter_user_id: uuid.UUID,
    session: Session,
) -> InstitutionLinkRequest:
    """
    Reject link request: mark REJECTED. Does NOT touch TalentProfile.institution_id
    (symmetric to approve_institution_link, minus the talent-linking side effect).

    AC (YET-197/IS-10): POST /institutions/{id}/link-requests/{request_id}/reject.

    Args:
        request_id: InstitutionLinkRequest ID
        institution_id: Institution the caller is authorized for (AC-5/AC-S2 —
            the request must belong to THIS institution)
        rejecter_user_id: User rejecting (for audit)
        session: Database session

    Returns:
        InstitutionLinkRequest (status=REJECTED, decided_at/decided_by set)

    Raises:
        ValueError: If request not found, not in this institution, or not PENDING
    """
    link_request = session.execute(
        select(InstitutionLinkRequest).where(
            InstitutionLinkRequest.id == request_id,
            InstitutionLinkRequest.institution_id == institution_id,
        )
    ).scalar_one_or_none()

    if not link_request:
        raise ValueError(f"Link request {request_id} not found")

    if link_request.status != "PENDING":
        raise ValueError(
            f"Link request {request_id} is not PENDING (current status: {link_request.status})"
        )

    link_request.status = "REJECTED"
    link_request.decided_at = datetime.now(timezone.utc)
    link_request.decided_by_user_id = rejecter_user_id

    session.flush()
    return link_request


def list_pending_link_requests(institution_id: uuid.UUID, session: Session) -> list[dict]:
    """
    List PENDING link requests for an institution, with the requesting talent's name.

    AC (YET-197/IS-10): GET /institutions/{id}/link-requests. Authorization (institution_id
    belongs to the caller) is enforced by the caller (API layer) — this function trusts
    institution_id as given, same convention as approve_institution_link/reject_institution_link.

    Args:
        institution_id: Target institution
        session: Database session

    Returns:
        List of dicts: id, talent_profile_id, talent_full_name, status, requested_at
        (oldest first — coordinators triage in request order)
    """
    rows = session.execute(
        select(InstitutionLinkRequest, TalentProfile)
        .join(TalentProfile, InstitutionLinkRequest.talent_profile_id == TalentProfile.id)
        .where(
            InstitutionLinkRequest.institution_id == institution_id,
            InstitutionLinkRequest.status == "PENDING",
        )
        .order_by(InstitutionLinkRequest.requested_at.asc())
    ).all()
    return [
        {
            "id": str(req.id),
            "talent_profile_id": str(req.talent_profile_id),
            "talent_full_name": talent.full_name,
            "status": req.status,
            "requested_at": req.requested_at.isoformat(),
        }
        for req, talent in rows
    ]


def list_my_link_requests(session: Session, principal: Principal) -> list[dict]:
    """
    List the authenticated talent's own link requests (all statuses), newest first.

    AC (YET-197/IS-10): GET /talents/me/institution-link-requests. Uses
    scoped_own_institution_link_requests for the BOLA-safe base query (talent
    can only ever see their own talent_profile_id's requests).

    Args:
        session: Database session
        principal: Authenticated Principal (must have talent_id — caller's responsibility)

    Returns:
        List of dicts: id, institution_id, institution_name, status, requested_at, decided_at
    """
    requests = session.execute(
        scoped_own_institution_link_requests(session, principal).order_by(
            InstitutionLinkRequest.requested_at.desc()
        )
    ).scalars().all()

    institution_ids = {r.institution_id for r in requests}
    name_by_id = {
        inst.id: inst.name
        for inst in session.execute(
            select(Institution).where(Institution.id.in_(institution_ids))
        ).scalars().all()
    }

    return [
        {
            "id": str(r.id),
            "institution_id": str(r.institution_id),
            "institution_name": name_by_id.get(r.institution_id, ""),
            "status": r.status,
            "requested_at": r.requested_at.isoformat(),
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        }
        for r in requests
    ]


# Engagement statuses grouped for the coordinator's per-student counts.
_VERIFIED_STATUSES = ("VERIFIED", "RESOLVED")
_IN_PROGRESS_STATUSES = ("PENDING_APPROVAL", "ACTIVE", "PENDING_EVALUATION", "EVALUATED")


def list_institution_students(
    session: Session, principal: Principal, institution_id: uuid.UUID
) -> list[dict]:
    """
    Students linked to the institution with their engagement counts (coordinator panel).

    Students come from scoped_institution_students (approved link, not PRIVATE). Counts
    are computed only over engagements the principal already sees through
    scoped_engagements AND that belong to this institution, so a student's work with
    another institution, or on their own, is never counted or revealed here.
    Email is deliberately not returned; public_slug only when the profile is PUBLIC.

    Returns:
        List of dicts ordered by full_name: talent_profile_id, full_name, department,
        study_year, public_slug, verified_count, in_progress_count, total_count.
    """
    students = (
        session.execute(
            scoped_institution_students(session, principal, institution_id).order_by(
                TalentProfile.full_name.asc()
            )
        )
        .scalars()
        .all()
    )
    if not students:
        return []

    engagements = (
        scoped_engagements(session, principal)
        .where(
            Engagement.institution_id == institution_id,
            Engagement.talent_id.in_([s.id for s in students]),
        )
        .subquery()
    )
    counts = {
        row.talent_id: row
        for row in session.execute(
            select(
                engagements.c.talent_id,
                func.count().label("total"),
                func.count().filter(engagements.c.status.in_(_VERIFIED_STATUSES)).label("verified"),
                func.count().filter(engagements.c.status.in_(_IN_PROGRESS_STATUSES)).label("in_progress"),
            ).group_by(engagements.c.talent_id)
        ).all()
    }

    result = []
    for student in students:
        row = counts.get(student.id)
        result.append(
            {
                "talent_profile_id": str(student.id),
                "full_name": student.full_name,
                "department": student.department,
                "study_year": student.study_year,
                "public_slug": student.public_slug if student.visibility == "PUBLIC" else None,
                "verified_count": row.verified if row else 0,
                "in_progress_count": row.in_progress if row else 0,
                "total_count": row.total if row else 0,
            }
        )
    return result


def list_institution_partners(
    session: Session, principal: Principal, institution_id: uuid.UUID
) -> list[dict]:
    """
    Organizations the institution's students work with (coordinator "iş birlikleri").

    Counts are computed only over engagements of THIS institution that belong to
    students in scoped_institution_students (approved link, not PRIVATE), so a PRIVATE
    student never contributes to a count. Non-members get an empty result (the
    endpoint answers 404 before calling this).

    Returns:
        List of dicts ordered by engagement_count desc, then name: organization_id,
        organization_name, verification_level, student_count, engagement_count,
        verified_count.
    """
    students = scoped_institution_students(session, principal, institution_id).with_only_columns(
        TalentProfile.id
    )
    engagements = (
        scoped_engagements(session, principal)
        .where(
            Engagement.institution_id == institution_id,
            Engagement.talent_id.in_(students),
        )
        .subquery()
    )
    rows = session.execute(
        select(
            Organization.id,
            Organization.name,
            Organization.verification_level,
            func.count(func.distinct(engagements.c.talent_id)).label("student_count"),
            func.count().label("engagement_count"),
            func.count().filter(engagements.c.status.in_(_VERIFIED_STATUSES)).label("verified_count"),
        )
        .join(engagements, engagements.c.organization_id == Organization.id)
        .group_by(Organization.id, Organization.name, Organization.verification_level)
        .order_by(func.count().desc(), Organization.name.asc())
    ).all()
    return [
        {
            "organization_id": str(row.id),
            "organization_name": row.name,
            "verification_level": row.verification_level,
            "student_count": row.student_count,
            "engagement_count": row.engagement_count,
            "verified_count": row.verified_count,
        }
        for row in rows
    ]


REPORT_HEADERS = (
    "Ad Soyad",
    "Bölüm",
    "Sınıf",
    "Kuruluş",
    "Çalışma",
    "Tür",
    "Durum",
    "Başlangıç",
    "Bitiş",
    "Doğrulama tarihi",
    "Doğrulama bağlantısı",
)

# Report-only Turkish labels (the CSV header set itself is fixed by the product spec).
_KIND_LABELS = {
    "INTERNSHIP": "Staj",
    "CAPSTONE": "Bitirme projesi",
    "SHORT_PROJECT": "Kısa proje",
    "PART_TIME": "Yarı zamanlı",
}
_STATUS_LABELS = {
    "DRAFT": "Taslak",
    "PENDING_APPROVAL": "Onay bekliyor",
    "REJECTED": "Reddedildi",
    "ACTIVE": "Devam ediyor",
    "CANCELLED": "İptal edildi",
    "PENDING_EVALUATION": "Değerlendirme bekliyor",
    "EVALUATED": "Değerlendirildi",
    "VERIFIED": "Doğrulandı",
    "DISPUTED": "İtiraz var",
    "RESOLVED": "İtiraz çözüldü",
}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: object) -> str:
    """Render a cell; neutralise spreadsheet formulas by prefixing a single quote."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def build_institution_report(
    session: Session,
    principal: Principal,
    institution_id: uuid.UUID,
    frontend_origin: str,
) -> tuple[bytes, int]:
    """
    CSV report (UTF-8 with BOM, ';' delimiter — opens correctly in Turkish Excel).

    Scope is the same as list_institution_students: students from
    scoped_institution_students (approved link, not PRIVATE) and only this
    institution's engagements seen through scoped_engagements. The verification link
    is emitted only for PUBLIC verified experiences. Every cell goes through csv_safe.

    Returns:
        (csv bytes, number of data rows)
    """
    students = scoped_institution_students(session, principal, institution_id).with_only_columns(
        TalentProfile.id
    )
    rows = session.execute(
        scoped_engagements(session, principal)
        .join(TalentProfile, TalentProfile.id == Engagement.talent_id)
        .join(Organization, Organization.id == Engagement.organization_id)
        .outerjoin(VerifiedExperience, VerifiedExperience.engagement_id == Engagement.id)
        .where(
            Engagement.institution_id == institution_id,
            Engagement.talent_id.in_(students),
        )
        .with_only_columns(
            Engagement,
            TalentProfile.full_name,
            TalentProfile.department,
            TalentProfile.study_year,
            Organization.name,
            VerifiedExperience.created_at,
            VerifiedExperience.visibility,
            VerifiedExperience.public_token,
        )
        .order_by(
            TalentProfile.full_name.asc(),
            Engagement.created_at.asc(),
            VerifiedExperience.created_at.desc(),
        )
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(REPORT_HEADERS)
    seen: set[uuid.UUID] = set()
    count = 0
    origin = frontend_origin.rstrip("/")
    for eng, name, department, study_year, org_name, verified_at, visibility, token in rows:
        if eng.id in seen:  # several verified experiences per engagement: keep the latest
            continue
        seen.add(eng.id)
        link = f"{origin}/v/{token}" if visibility == "PUBLIC" and token else ""
        writer.writerow(
            [
                csv_safe(cell)
                for cell in (
                    name,
                    department,
                    study_year,
                    org_name,
                    eng.title,
                    _KIND_LABELS.get(eng.kind, eng.kind),
                    _STATUS_LABELS.get(eng.status, eng.status),
                    eng.started_on.isoformat() if isinstance(eng.started_on, date) else None,
                    eng.ended_on.isoformat() if isinstance(eng.ended_on, date) else None,
                    verified_at.date().isoformat() if verified_at else None,
                    link,
                )
            ]
        )
        count += 1
    return ("\ufeff" + buffer.getvalue()).encode("utf-8"), count
