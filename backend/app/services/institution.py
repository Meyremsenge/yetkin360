"""Institution service: core business logic for institution management."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import (
    Institution,
    InstitutionLinkRequest,
    InstitutionMember,
    TalentProfile,
    User,
)
from app.services.authorization import Principal, scoped_own_institution_link_requests


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
