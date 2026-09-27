"""Organization endpoints (AC-1 through AC-11)."""

import uuid
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.core.deps import require_csrf
from app.models import Organization
from app.services.authorization import Principal, get_scoped_or_404, scoped_organizations
from app.services.audit import log_audit_event
from app.services.organization import (
    AlreadyMemberError,
    DomainAlreadyVerifiedError,
    DuplicateLegalIdError,
    FreeEmailDomainError,
    RateLimitError,
    create_organization,
    invite_org_member,
    verify_domain,
)
from app.services.outbox import enqueue

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class OrganizationCreate(BaseModel):
    """Request schema for POST /organizations."""

    name: str = Field(..., min_length=1)
    domain: str | None = None
    legal_id: str | None = None


class OrganizationResponse(BaseModel):
    """Response schema for Organization."""

    id: uuid.UUID
    name: str
    domain: str | None
    legal_id: str | None
    verification_level: str
    status: str

    class Config:
        from_attributes = True


class OrganizationMemberInvite(BaseModel):
    """Request schema for POST /organizations/{id}/members."""

    email: str
    role: str  # ADMIN or MEMBER


class OrganizationMemberResponse(BaseModel):
    """Response schema for OrganizationMember."""

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    status: str

    class Config:
        from_attributes = True


class DomainVerifyRequest(BaseModel):
    """Request schema for POST /organizations/{id}/verify-domain."""

    # No body fields required — just the organization ID from URL


class DomainVerifyResponse(BaseModel):
    """Response schema for verify-domain endpoint."""

    dns_txt_record: str
    status: str  # "verified" or "pending"


# ============================================================================
# Helper: Hostname format validation (AC-S5)
# ============================================================================


def validate_hostname(domain: str) -> bool:
    """
    Validate domain is a proper hostname (not IP, localhost, RFC1918, etc.).

    AC-S5: Domain must be standard hostname format, no IP/port/path/localhost/RFC1918.

    Returns:
        True if valid, False otherwise
    """
    if not domain:
        return False

    # Reject localhost, loopback variations
    if domain.lower() in ("localhost", "127.0.0.1", "::1"):
        return False

    # Reject RFC1918 and link-local addresses (if it looks like an IP)
    try:
        # Simple check: if it contains only digits and dots, it's likely an IP
        parts = domain.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            # IPv4 address
            return False
    except Exception:
        pass

    # Reject if contains port (colon) or path (slash)
    if ":" in domain or "/" in domain:
        return False

    # Simple hostname regex: alphanumeric, dots, hyphens (no leading/trailing hyphens)
    # Allows TLDs and subdomains
    hostname_pattern = r"^(?!-)(?:[a-zA-Z0-9-]{1,63}(?<!-)\.)*[a-zA-Z0-9]{1,63}$"
    return bool(re.match(hostname_pattern, domain))


# ============================================================================
# AC-1: Create Organization
# ============================================================================


@router.post("/", status_code=201, response_model=OrganizationResponse)
def create_organization_endpoint(
    payload: OrganizationCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> Organization:
    """
    AC-1: Create organization. Caller becomes ADMIN.
    AC-S3: verification_level, verified_at, verified_by_user_id in input ignored.

    Args:
        payload: name (required), domain (optional), legal_id (optional)
        principal: Authenticated principal
        session: Database session

    Returns:
        Organization (T1, ACTIVE)

    Status codes:
        201: Organization created
        409: Duplicate legal_id
        422: Invalid input / invalid domain format
        401: Unauthenticated
    """
    if not principal.user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Validate name
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=422, detail="Name is required")

    # Validate domain format if provided (AC-S5)
    if payload.domain and not validate_hostname(payload.domain):
        raise HTTPException(status_code=422, detail="Invalid domain format")

    try:
        organization = create_organization(
            name=payload.name,
            domain=payload.domain,
            legal_id=payload.legal_id,
            caller_user_id=principal.user_id,
            session=session,
        )
        session.flush()

        # Log audit event (AC-S7)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="CREATE_ORGANIZATION",
            subject_type="organization",
            subject_id=organization.id,
            result="SUCCESS",
            metadata={"name": payload.name, "legal_id": payload.legal_id},
        )

        return organization
    except DuplicateLegalIdError:
        raise HTTPException(status_code=409, detail="LEGAL_ID_TAKEN")


# ============================================================================
# AC-3: Invite Member to Organization
# ============================================================================


@router.post("/{organization_id}/members", status_code=201, response_model=OrganizationMemberResponse)
def invite_member_endpoint(
    organization_id: uuid.UUID,
    payload: OrganizationMemberInvite,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
):
    """
    AC-3: Invite user to organization (ADMIN-only action).
    AC-4: Duplicate membership → 409 ALREADY_MEMBER.
    AC-S1: Tenant isolation — non-ADMIN or out-of-scope gets 404.
    AC-S2: role must be ADMIN or MEMBER only.
    AC-S6: outbox event added in same transaction.
    AC-S7: Audit logged.

    Args:
        organization_id: Target organization
        payload: email, role
        principal: Authenticated principal
        session: Database session

    Returns:
        OrganizationMember

    Status codes:
        201: Member invited
        404: Organization not found or not authorized
        409: User already a member
        422: Invalid role
    """
    # AC-S2: Validate role
    if payload.role not in ("ADMIN", "MEMBER"):
        raise HTTPException(status_code=422, detail="INVALID_ROLE")

    # AC-S1: Check organization exists and is in principal's scope + is ADMIN
    scoped = scoped_organizations(session, principal)
    org_query = scoped.where(Organization.id == organization_id)
    org = get_scoped_or_404(org_query, session)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if principal is ADMIN of this organization
    if principal.kind != "ORG_ADMIN" or organization_id not in principal.org_admin_ids:
        raise HTTPException(status_code=404, detail="Organization not found")

    try:
        member = invite_org_member(
            organization_id=organization_id,
            email=payload.email,
            role=payload.role,
            session=session,
        )
        session.flush()

        # AC-S6: Enqueue email invitation in same transaction (PII guard: use user_id, not email)
        enqueue(
            session=session,
            topic="email.organization_member_invited",
            payload={
                "user_id": str(member.user_id),
                "organization_id": str(organization_id),
                "organization_name": org.name,
                "role": payload.role,
            },
        )

        # Log audit event (AC-S7)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="INVITE_ORG_MEMBER",
            subject_type="organization_member",
            subject_id=member.id,
            result="SUCCESS",
            metadata={
                "organization_id": str(organization_id),
                "invited_user_id": str(member.user_id),
                "role": payload.role,
            },
        )

        return member
    except AlreadyMemberError:
        raise HTTPException(status_code=409, detail="ALREADY_MEMBER")


# ============================================================================
# AC-5/AC-6/AC-7/AC-8: Verify Organization Domain
# ============================================================================


@router.post("/{organization_id}/verify-domain", status_code=200, response_model=DomainVerifyResponse)
def verify_domain_endpoint(
    organization_id: uuid.UUID,
    payload: DomainVerifyRequest = DomainVerifyRequest(),
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
):
    """
    AC-5/AC-6/AC-7/AC-8: Verify organization domain via DNS TXT lookup.

    AC-5: Free email domain → 400 FREE_EMAIL_DOMAIN.
    AC-6/AC-7: DNS TXT found → 200 {status:"verified"}, T2 + verified_at + verified_by_user_id.
    AC-8: DNS error/timeout/not found → 200 {status:"pending"}, no state change (not error).
    AC-9: Domain already verified in another org → 409 DOMAIN_ALREADY_VERIFIED.
    AC-10: Non-ADMIN caller → 404.
    AC-11/AC-S4: Rate limit (60s cooldown) → 429 TOO_MANY_REQUESTS.
    AC-S1: Tenant isolation — out-of-scope gets 404.
    AC-S7: Audit logged (success and failure).

    Args:
        organization_id: Organization to verify
        payload: Empty request body
        principal: Authenticated principal
        session: Database session

    Returns:
        DomainVerifyResponse with dns_txt_record and status

    Status codes:
        200: Verification check completed (status="verified" or "pending")
        400: Free email domain / invalid domain
        404: Organization not found or not authorized
        409: Domain already verified in another organization
        429: Rate limit exceeded
    """
    # AC-S1: Check organization exists and is in principal's scope + is ADMIN
    scoped = scoped_organizations(session, principal)
    org_query = scoped.where(Organization.id == organization_id)
    org = get_scoped_or_404(org_query, session)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check if principal is ADMIN of this organization
    if principal.kind != "ORG_ADMIN" or organization_id not in principal.org_admin_ids:
        raise HTTPException(status_code=404, detail="Organization not found")

    # AC-S5: Validate domain format before DNS lookup (prevent SSRF)
    if not validate_hostname(org.domain):
        raise HTTPException(status_code=400, detail="INVALID_DOMAIN_FORMAT")

    try:
        result = verify_domain(
            organization_id=organization_id,
            session=session,
        )

        # If verification succeeded (T2), set verified_by_user_id
        if result["status"] == "verified":
            org.verified_by_user_id = principal.user_id
            session.flush()

            # Log success (AC-S7)
            log_audit_event(
                session=session,
                actor_user_id=principal.user_id,
                actor_ip=None,
                action="VERIFY_DOMAIN_SUCCESS",
                subject_type="organization",
                subject_id=organization_id,
                result="SUCCESS",
                metadata={"domain": org.domain, "verification_level": "T2"},
            )
        else:
            # Log pending (AC-S7)
            log_audit_event(
                session=session,
                actor_user_id=principal.user_id,
                actor_ip=None,
                action="VERIFY_DOMAIN_PENDING",
                subject_type="organization",
                subject_id=organization_id,
                result="SUCCESS",
                metadata={"domain": org.domain, "status": "pending"},
            )

        return DomainVerifyResponse(
            dns_txt_record=result["dns_txt_record"],
            status=result["status"],
        )

    except FreeEmailDomainError:
        # Log denied (AC-S7)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="VERIFY_DOMAIN_REJECTED",
            subject_type="organization",
            subject_id=organization_id,
            result="DENIED",
            metadata={"domain": org.domain, "reason": "free_email_domain"},
        )
        raise HTTPException(status_code=400, detail="FREE_EMAIL_DOMAIN")

    except RateLimitError:
        raise HTTPException(status_code=429, detail="TOO_MANY_REQUESTS")

    except DomainAlreadyVerifiedError:
        raise HTTPException(status_code=409, detail="DOMAIN_ALREADY_VERIFIED")


# ============================================================================
# AC-S1: Get Organization (for test reference, not critical)
# ============================================================================


@router.get("/{organization_id}", status_code=200, response_model=OrganizationResponse)
def get_organization_endpoint(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
):
    """
    AC-S1: Get organization details (tenant isolation, 404 on out-of-scope).

    Args:
        organization_id: Organization to retrieve
        principal: Authenticated principal
        session: Database session

    Returns:
        Organization object

    Status codes:
        200: Organization found
        404: Organization not found or not authorized
    """
    scoped = scoped_organizations(session, principal)
    org_query = scoped.where(Organization.id == organization_id)
    org = get_scoped_or_404(org_query, session)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org
