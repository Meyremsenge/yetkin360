"""Institution endpoints (AC-1 through AC-8)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.models import Institution, InstitutionLinkRequest
from app.schemas.reminder import ReminderCreate, ReminderResponse
from app.services.authorization import Principal, get_scoped_or_404, scoped_institutions
from app.services.audit import log_audit_event
from app.services.institution import (
    AlreadyMemberError,
    DuplicateLinkRequestError,
    approve_institution_link,
    create_institution,
    get_institution,
    invite_member,
    list_pending_link_requests,
    reject_institution_link,
    request_institution_link,
)
from app.services.complaint import upheld_complaint_count
from app.services.engagement import get_coordinator_dashboard
from app.services.outbox import enqueue
from app.services.rate_limit import RateLimitExceeded
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


class PendingLinkRequestItem(BaseModel):
    """Single item in GET /institutions/{id}/link-requests response."""

    id: uuid.UUID
    talent_profile_id: uuid.UUID
    talent_full_name: str
    status: str
    requested_at: datetime


class PendingLinkRequestsListResponse(BaseModel):
    """Response schema for GET /institutions/{id}/link-requests."""

    items: list[PendingLinkRequestItem]


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
    upheld_complaint_count: int = 0  # admin-upheld complaints about this institution (sikayet-backend C7)


# ============================================================================
# AC-1: Create Institution
# ============================================================================


@router.post("/", status_code=201, response_model=InstitutionResponse)
def create_institution_endpoint(
    payload: InstitutionCreate,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> Institution:
    """
    AC-1: Create institution. Caller becomes ADMIN.

    Args:
        payload: name (required), domain (accepted but ignored: GUV-09, unverified)
        principal: Authenticated principal
        session: Database session

    Returns:
        Institution (T1, ACTIVE, domain None)

    Status codes:
        201: Institution created
        422: Invalid input
        401: Unauthenticated
    """
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Validate name
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")

    # GUV-09: payload.domain is unverified, attacker-chosen text and the column is UNIQUE, so
    # storing it would let the first caller lock out the real institution. Never reserve it here;
    # only the seed / a platform admin sets an institution domain (trusted service callers).
    institution = create_institution(
        name=payload.name,
        domain=None,
        caller_user_id=principal.user_id,
        session=session,
    )
    session.flush()  # Persist changes within transaction
    return institution


# ============================================================================
# AC-2: Invite Member to Institution
# ============================================================================


@router.post("/{institution_id}/members", status_code=202)
def invite_member_endpoint(
    institution_id: uuid.UUID,
    payload: InstitutionMemberInvite,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
):
    """
    AC-1/AC-2/AC-4/AC-6: Invite user to institution (ADMIN-only action).
    AC-1: Bilinen e-posta → 202 {"status": "queued"}, üyelik + outbox enqueue + audit
    AC-2: Bilinmeyen e-posta → 202 {"status": "queued"}, hiç üyelik oluşmaz, yalnız audit
    AC-3: Geçersiz rol → 422 INVALID_ROLE
    AC-4: Zaten üye → 202 (rol değişmez)
    AC-5/AC-8: Tenant isolation — COORDINATOR or out-of-scope ADMIN gets 404.
    AC-6: Audit event yazılması (yeni)

    Args:
        institution_id: Target institution
        payload: email, role
        principal: Authenticated principal
        session: Database session

    Returns:
        {"status": "queued"}

    Status codes:
        202: Invitation queued (whether member created or not)
        404: Institution not found or user not authorized
        422: Invalid role
    """
    # AC-3: Validate role (HAND, not Pydantic Literal)
    if payload.role not in ("ADMIN", "COORDINATOR"):
        raise ApiError(422, "INVALID_ROLE", "Geçerli rol değeri: ADMIN veya COORDINATOR")

    # AC-8: Authorization: Principal must be ADMIN of THIS institution (not just any admin).
    # Per-kurum check: institution_id must be in principal.institution_admin_ids.
    if institution_id not in principal.institution_admin_ids:
        # Not admin of this institution. Return 404 (not 403, to hide resource existence).
        raise ApiError(404, "NOT_FOUND", "Kurum bulunamadı")

    # AC-8: Verify institution exists and is in scope (defense-in-depth)
    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise ApiError(404, "NOT_FOUND", "Kurum bulunamadı")

    # Invite member (isolate exception handling to invite_member only)
    member = None
    try:
        member = invite_member(
            institution_id=institution_id,
            email=payload.email,
            role=payload.role,
            session=session,
        )
    except AlreadyMemberError:
        # AC-4: Zaten üye → 202 (rol değişmez, hiçbir şey yapılmaz)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="INVITE_INSTITUTION_MEMBER",
            subject_type="institution",
            subject_id=institution_id,
            result="SUCCESS",
            metadata={
                "institution_id": str(institution_id),
                "role": payload.role,
                "reason": "already_member",
            },
        )
    except ValueError:
        # AC-2: Bilinmeyen e-posta → 202 (hiçbir üyelik oluşmaz, yalnız audit)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="INVITE_INSTITUTION_MEMBER",
            subject_type="institution",
            subject_id=institution_id,
            result="SUCCESS",
            metadata={
                "institution_id": str(institution_id),
                "role": payload.role,
                "reason": "user_not_found",
            },
        )

    # AC-1: Member created successfully → enqueue + audit (outside invite_member exception handler)
    if member:
        enqueue(
            session=session,
            topic="email.institution_member_invited",
            payload={
                "user_id": str(member.user_id),
                "institution_id": str(institution_id),
                "institution_name": institution.name,
                "role": payload.role,
            },
        )

        # AC-6: Log audit event
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="INVITE_INSTITUTION_MEMBER",
            subject_type="institution_member",
            subject_id=member.id,
            result="SUCCESS",
            metadata={
                "institution_id": str(institution_id),
                "invited_user_id": str(member.user_id),
                "role": payload.role,
            },
        )

    return {"status": "queued"}


# ============================================================================
# AC-3: Student requests institution link
# ============================================================================


@router.post("/{institution_id}/link-requests", status_code=201, response_model=InstitutionLinkRequestResponse)
def request_institution_link_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
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
    institution = get_institution(session, institution_id)

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
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
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

    # Assert user_id is not None (principal kind is INST_ADMIN or COORDINATOR, which require authentication)
    assert principal.user_id is not None

    # Approve request (service scopes request_id to institution_id — AC-5/AC-S2)
    try:
        link_request = approve_institution_link(
            request_id=request_id,
            institution_id=institution_id,
            approver_user_id=principal.user_id,
            session=session,
        )
        session.flush()  # Persist changes within transaction
        return link_request
    except ValueError as e:
        message = str(e)
        if "not found" in message:
            raise HTTPException(status_code=404, detail="Link request not found")
        raise HTTPException(status_code=422, detail=message)


# ============================================================================
# YET-197/IS-10: Reject student link request
# ============================================================================


@router.post("/{institution_id}/link-requests/{request_id}/reject", status_code=200, response_model=InstitutionLinkRequestResponse)
def reject_link_request_endpoint(
    institution_id: uuid.UUID,
    request_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> InstitutionLinkRequest:
    """
    YET-197/IS-10: Coordinator/Admin rejects link request → REJECTED (talent stays unlinked).
    AC-5/AC-S2: Only coordinator/admin of THE institution can reject its requests
    (same tenant-isolation pattern as approve_link_request_endpoint).

    Args:
        institution_id: Target institution (from URL path, for authorization check)
        request_id: InstitutionLinkRequest ID
        principal: Authenticated principal
        session: Database session

    Returns:
        InstitutionLinkRequest (REJECTED status)

    Status codes:
        200: Request rejected
        404: Request not found, institution not found, or user not authorized
        422: Request not PENDING
    """
    # Authorization: Principal must be member of THE institution (ADMIN or COORDINATOR).
    if institution_id not in principal.institution_ids:
        raise HTTPException(status_code=404, detail="Institution not found")

    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    assert principal.user_id is not None

    try:
        link_request = reject_institution_link(
            request_id=request_id,
            institution_id=institution_id,
            rejecter_user_id=principal.user_id,
            session=session,
        )
        session.flush()
        return link_request
    except ValueError as e:
        message = str(e)
        if "not found" in message:
            raise HTTPException(status_code=404, detail="Link request not found")
        raise HTTPException(status_code=422, detail=message)


# ============================================================================
# YET-197/IS-10: List pending link requests (coordinator view)
# ============================================================================


@router.get("/{institution_id}/link-requests", status_code=200, response_model=PendingLinkRequestsListResponse)
def list_pending_link_requests_endpoint(
    institution_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PendingLinkRequestsListResponse:
    """
    YET-197/IS-10: Coordinator/Admin lists PENDING link requests for their institution.
    AC-5/AC-S2: Same tenant-isolation pattern as approve/reject — only coordinator/admin
    of THE institution can see its pending requests.

    Args:
        institution_id: Target institution (from URL path, for authorization check)
        principal: Authenticated principal
        session: Database session

    Returns:
        PendingLinkRequestsListResponse (items: id, talent_profile_id, talent_full_name,
        status, requested_at — oldest first)

    Status codes:
        200: List retrieved (possibly empty)
        404: Institution not found or user not authorized
    """
    if institution_id not in principal.institution_ids:
        raise HTTPException(status_code=404, detail="Institution not found")

    scoped = scoped_institutions(session, principal).where(Institution.id == institution_id)
    institution = get_scoped_or_404(scoped, session)

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    items = list_pending_link_requests(institution_id=institution_id, session=session)
    return PendingLinkRequestsListResponse(items=[PendingLinkRequestItem(**item) for item in items])


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
            upheld_complaint_count=upheld_complaint_count(session, "INSTITUTION", institution_id),
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
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
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
    try:
        queued_count = create_reminders(
            institution_id=institution_id,
            engagement_ids=payload.engagement_ids,
            template=payload.template,
            actor_user_id=principal.user_id,
            principal=principal,
            session=session,
        )
    except RateLimitExceeded as exc:
        # YET-213: per-institution quota (20 requests/hour); checked after the scope check, so 404 wins.
        raise ApiError(
            429,
            "RATE_LIMITED",
            "Çok fazla hatırlatma isteği yapıldı. Lütfen daha sonra tekrar deneyin.",
            headers={"Retry-After": str(exc.retry_after)},
        )

    # AC-1: Flush to persist outbox + audit_event within transaction
    session.flush()

    return ReminderResponse(queued_count=queued_count)
