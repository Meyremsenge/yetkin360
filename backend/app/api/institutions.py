"""Institution endpoints (AC-1 through AC-8)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.models import Institution, InstitutionLinkRequest
from app.schemas.reminder import ReminderCreate, ReminderResponse
from app.services.authorization import Principal, get_scoped_or_404, scoped_institutions
from app.services.institution import (
    DuplicateDomainError,
    DuplicateLinkRequestError,
    approve_institution_link,
    create_institution,
    invite_member,
    request_institution_link,
)
from app.services.engagement import get_coordinator_dashboard
from app.services.reminder import create_reminders

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


class DashboardEngagementItem(BaseModel):
    """Engagement item in dashboard response."""

    id: str
    talent_id: str
    organization_id: str
    title: str
    started_on: str | None = None
    ended_on: str | None = None


class DashboardMemberItem(BaseModel):
    """Member item in dashboard response."""

    user_id: str
    email: str
    role: str
    joined_at: datetime


class DashboardSummary(BaseModel):
    """Summary counts in dashboard response."""

    pending_approval: int
    pending_evaluation: int


class DashboardResponse(BaseModel):
    """Response schema for GET /institutions/{id}/dashboard."""

    institution_id: str
    summary: DashboardSummary
    pending_approval: list[DashboardEngagementItem]
    pending_evaluation: list[DashboardEngagementItem]
    members: list[DashboardMemberItem]


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


# ============================================================================
# Coordinator Dashboard (PLAN 3.3 — koordinator-dashboard-ucu)
# ============================================================================


@router.get("/{institution_id}/dashboard", status_code=200, response_model=DashboardResponse)
def get_coordinator_dashboard_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """
    Get coordinator dashboard for institution (PLAN 3.3 — koordinator-dashboard-ucu).

    Returns summary counts and lists of PENDING_APPROVAL and PENDING_EVALUATION engagements
    for the specified institution.

    Args:
        institution_id: Target institution
        principal: Authenticated principal
        session: Database session

    Returns:
        DashboardResponse with summary and engagement lists

    Status codes:
        200: Dashboard retrieved
        404: Institution not found or user not authorized
        401: Unauthenticated
        422: Invalid institution_id format (FastAPI path validation)
    """
    # Verify principal is authenticated
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Kimlik doğrulama gerekli."})

    # Call service (handles authorization and validation)
    try:
        dashboard_data = get_coordinator_dashboard(
            session=session,
            principal=principal,
            institution_id=str(institution_id),
        )
        return DashboardResponse(
            institution_id=dashboard_data["institution_id"],
            summary=DashboardSummary(**dashboard_data["summary"]),
            pending_approval=[DashboardEngagementItem(**item) for item in dashboard_data["pending_approval"]],
            pending_evaluation=[DashboardEngagementItem(**item) for item in dashboard_data["pending_evaluation"]],
            members=[DashboardMemberItem(**item) for item in dashboard_data["members"]],
        )
    except ValueError:
        # Authorization failure or institution not found (both → 404)
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Kurum bulunamadı."})


# ============================================================================
# Bulk Reminders (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu)
# ============================================================================


@router.post(
    "/{institution_id}/reminders",
    status_code=202,
    response_model=ReminderResponse,
)
def create_reminders_endpoint(
    institution_id: uuid.UUID,
    payload: ReminderCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> ReminderResponse:
    """
    Trigger bulk reminders for institution's pending evaluations.

    Implements:
    - AC-1 [Critical]: Happy path → 202 + queued_count
    - AC-2 [Critical]: Validation (empty engagement_ids, missing template) → 400
    - AC-3 [Critical]: Cross-institution filtering (only institution's engagements queued)
    - AC-4 [Critical]: Cross-tenant path → 404 (not 403)
    - AC-5 [Critical]: Insufficient role (not COORDINATOR/ADMIN) → 404
    - AC-6 [High]: All filtered → 202 + queued_count: 0
    - AC-7 [Medium]: Invalid template → 400 (Pydantic validates)
    - AC-S1/S2: Tenant isolation via 404
    - AC-S3: ID enumeration defense (no response field reveals filtering)
    - AC-S6: Audit logging without PII

    Args:
        institution_id: Target institution (must be in principal's scope)
        payload: engagement_ids (≥1), template (non-empty)
        principal: Authenticated principal (must be COORDINATOR or INST_ADMIN)
        session: Database session

    Returns:
        ReminderResponse with queued_count (0..N)

    Status codes:
        202: Reminders queued (queued_count ≥ 0)
        400: Invalid input (empty engagement_ids, missing/empty template)
        404: Institution not found, or user not authorized (same message for both)
        422: Validation error
    """
    # AC-4, AC-5, AC-S1, AC-S2: Authorization check
    # Principal must be COORDINATOR or INST_ADMIN of THIS institution
    if institution_id not in principal.institution_ids:
        # User not authorized for this institution (different institution, or no role)
        # Return 404 without distinguishing between "not found" and "not authorized"
        raise HTTPException(status_code=404, detail="Institution not found")

    # Defense-in-depth: Verify institution exists and is in principal's scope
    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Ensure user_id is available for audit
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Create reminders (AC-1, AC-2, AC-3, AC-6, AC-7, AC-S6)
    # AC-2: Pydantic validates engagement_ids (min_length=1) and template (min_length=1)
    # If validation fails, FastAPI returns 422 automatically
    queued_count = create_reminders(
        institution_id=institution_id,
        engagement_ids=payload.engagement_ids,
        template=payload.template,
        actor_user_id=principal.user_id,
        principal=principal,
        session=session,
    )

    # AC-1: Flush to persist outbox + audit_event within transaction
    session.flush()

    return ReminderResponse(queued_count=queued_count)
