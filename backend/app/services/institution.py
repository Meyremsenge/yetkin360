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


class DuplicateDomainError(Exception):
    """Raised when creating institution with duplicate domain."""

    pass


class DuplicateLinkRequestError(Exception):
    """Raised when student tries to create duplicate PENDING link request."""

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
    Invite user to institution (create/update InstitutionMember).

    AC-2: POST /institutions/{id}/members → 201, member created.

    Args:
        institution_id: Target institution
        email: Email of user to invite
        role: "ADMIN" or "COORDINATOR"
        session: Database session

    Returns:
        InstitutionMember object (newly created or updated)

    Raises:
        ValueError: If user not found
    """
    # Find user by email
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise ValueError(f"User {email} not found")

    # Create or update member (UPSERT)
    member = session.execute(
        select(InstitutionMember).where(
            and_(
                InstitutionMember.institution_id == institution_id,
                InstitutionMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    if member:
        # Update role
        member.role = role
    else:
        # Create new
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
