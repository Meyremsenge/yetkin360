"""Institution endpoints (AC-1 through AC-8)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.models import Institution, InstitutionLinkRequest
from app.services.authorization import Principal, get_scoped_or_404, scoped_institutions
from app.services.institution import (
    DuplicateDomainError,
    DuplicateLinkRequestError,
    approve_institution_link,
    create_institution,
    invite_member,
    request_institution_link,
)

router = APIRouter(prefix="/institutions", tags=["institutions"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class InstitutionCreate(BaseModel):
    """Request schema for POST /institutions."""

    name: str = Field(..., min_length=1)
    domain: str | None = None


class InstitutionResponse(BaseModel):
    """Response schema for Institution."""

    id: uuid.UUID
    name: str
    domain: str | None
    verification_level: str
    status: str

    class Config:
        from_attributes = True


class InstitutionMemberInvite(BaseModel):
    """Request schema for POST /institutions/{id}/members."""

    email: str
    role: str  # ADMIN or COORDINATOR


class InstitutionMemberResponse(BaseModel):
    """Response schema for InstitutionMember."""

    id: uuid.UUID
    institution_id: uuid.UUID
    user_id: uuid.UUID
    role: str

    class Config:
        from_attributes = True


class InstitutionLinkRequestResponse(BaseModel):
    """Response schema for InstitutionLinkRequest."""

    id: uuid.UUID
    talent_profile_id: uuid.UUID
    institution_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True


# ============================================================================
# AC-1: Create Institution
# ============================================================================


@router.post("/", status_code=201, response_model=InstitutionResponse)
def create_institution_endpoint(
    payload: InstitutionCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> Institution:
    """
    AC-1: Create institution. Caller becomes ADMIN.

    Args:
        payload: name (required), domain (optional)
        principal: Authenticated principal
        session: Database session

    Returns:
        Institution (T1, ACTIVE)

    Status codes:
        201: Institution created
        409: Duplicate domain
        422: Invalid input
        401: Unauthenticated
    """
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Validate name
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")

    try:
        institution = create_institution(
            name=payload.name,
            domain=payload.domain,
            caller_user_id=principal.user_id,
            session=session,
        )
        session.flush()  # Persist changes within transaction
        return institution
    except DuplicateDomainError:
        raise HTTPException(status_code=409, detail="DOMAIN_TAKEN")


# ============================================================================
# AC-2: Invite Member to Institution
# ============================================================================


@router.post("/{institution_id}/members", status_code=201, response_model=InstitutionMemberResponse)
def invite_member_endpoint(
    institution_id: uuid.UUID,
    payload: InstitutionMemberInvite,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    """
    AC-2: Invite user to institution (ADMIN-only action, AC-4/AC-S1).
    AC-5/AC-S2: Tenant isolation — COORDINATOR or out-of-scope ADMIN gets 404.

    Args:
        institution_id: Target institution
        payload: email, role
        principal: Authenticated principal
        session: Database session

    Returns:
        InstitutionMember (created or updated)

    Status codes:
        201: Member invited
        404: Institution not found or user not authorized (no distinction)
        422: Invalid input
    """
    # Authorization: Principal must be ADMIN of THIS institution (not just any admin).
    # Per-kurum check: institution_id must be in principal.institution_admin_ids.
    if institution_id not in principal.institution_admin_ids:
        # Not admin of this institution. Return 404 (not 403, to hide resource existence).
        raise HTTPException(status_code=404, detail="Institution not found")

    # Verify institution exists and is in scope (defense-in-depth)
    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Invite member
    try:
        member = invite_member(
            institution_id=institution_id,
            email=payload.email,
            role=payload.role,
            session=session,
        )
        session.flush()  # Persist changes within transaction
        return member
    except ValueError:
        raise HTTPException(status_code=422, detail="User not found")


# ============================================================================
# AC-3: Student requests institution link
# ============================================================================


@router.post("/{institution_id}/link-requests", status_code=201, response_model=InstitutionLinkRequestResponse)
def request_institution_link_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> InstitutionLinkRequest:
    """
    AC-3: Student creates PENDING link request to institution.

    Args:
        institution_id: Target institution
        principal: Authenticated principal (must have talent profile)
        session: Database session

    Returns:
        InstitutionLinkRequest (PENDING status)

    Status codes:
        201: Link request created
        409: Duplicate PENDING request
        404: Institution not found
        422: Caller not a student (no talent profile)
    """
    # Verify caller has talent profile
    if not principal.talent_id:
        raise HTTPException(status_code=422, detail="Caller must have a talent profile")

    # Verify institution exists (intentional exception: any student can request link to any institution)
    institution = session.execute(
        select(Institution).where(Institution.id == institution_id)
    ).scalar_one_or_none()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Create link request
    try:
        link_request = request_institution_link(
            institution_id=institution_id,
            talent_profile_id=principal.talent_id,
            session=session,
        )
        session.flush()  # Persist changes within transaction
        return link_request
    except DuplicateLinkRequestError:
        raise HTTPException(status_code=409, detail="Pending link request already exists")


# ============================================================================
# AC-3b: Approve student link request
# ============================================================================


@router.post("/{institution_id}/link-requests/{request_id}/approve", status_code=200, response_model=InstitutionLinkRequestResponse)
def approve_link_request_endpoint(
    institution_id: uuid.UUID,
    request_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> InstitutionLinkRequest:
    """
    AC-3b: Coordinator/Admin approves link request → APPROVED + TalentProfile linked.
    AC-5/AC-S2: Only coordinator/admin of THE institution can approve its requests.

    Args:
        institution_id: Target institution (from URL path, for authorization check)
        request_id: InstitutionLinkRequest ID
        principal: Authenticated principal
        session: Database session

    Returns:
        InstitutionLinkRequest (APPROVED status)

    Status codes:
        200: Request approved
        404: Request not found, institution not found, or user not authorized
        422: Request not PENDING
    """
    # Authorization: Principal must be member of THE institution (ADMIN or COORDINATOR).
    # Per-institution check: institution_id must be in principal.institution_ids.
    if institution_id not in principal.institution_ids:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Verify institution is in scope
    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Verify request exists and belongs to this institution
    link_request = session.execute(
        select(InstitutionLinkRequest).where(
            InstitutionLinkRequest.id == request_id,
            InstitutionLinkRequest.institution_id == institution_id,
        )
    ).scalar_one_or_none()

    if not link_request:
        raise HTTPException(status_code=404, detail="Link request not found")

    # Assert user_id is not None (principal kind is INST_ADMIN or COORDINATOR, which require authentication)
    assert principal.user_id is not None

    # Approve request
    try:
        link_request = approve_institution_link(
            request_id=request_id,
            approver_user_id=principal.user_id,
            session=session,
        )
        session.flush()  # Persist changes within transaction
        return link_request
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
