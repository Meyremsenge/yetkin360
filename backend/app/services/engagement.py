"""Engagement service: core business logic for work engagements."""

import uuid
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Engagement, Organization, TalentProfile
from app.services.authorization import Principal
from app.services.audit import log_audit_event


class TalentNotFoundError(Exception):
    """Raised when talent_id does not exist or is not accessible to principal."""
    pass


class OrganizationNotFoundError(Exception):
    """Raised when organization_id does not exist or is not accessible to principal."""
    pass


class InstitutionMismatchError(Exception):
    """Raised when institution_id does not match talent's institution."""
    pass


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

    # Default-deny: only TALENT, ORG_MEMBER, ORG_ADMIN can create engagements
    if principal.kind not in ("TALENT", "ORG_MEMBER", "ORG_ADMIN"):
        raise TalentNotFoundError("Not authorized to create engagements")

    # Validate talent exists and is accessible to principal
    # AC-S1: TALENT can only create for their own talent_id
    # AC-S1: ORG_MEMBER can create for any talent_id, but must check tenant isolation
    if principal.kind == "TALENT":
        # TALENT can only create engagement for themselves
        if principal.talent_id != talent_uuid:
            raise TalentNotFoundError(f"Talent {talent_id} not found or not accessible")

    # Verify talent exists
    talent = session.execute(
        select(TalentProfile).where(TalentProfile.id == talent_uuid)
    ).scalar_one_or_none()

    if not talent:
        raise TalentNotFoundError(f"Talent {talent_id} not found")

    # Validate organization exists and is accessible to principal
    # AC-S2: ORG_MEMBER can only create for their own organizations
    if principal.kind in ("ORG_MEMBER", "ORG_ADMIN"):
        if org_uuid not in principal.org_ids:
            raise OrganizationNotFoundError(f"Organization {organization_id} not found or not accessible")

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
