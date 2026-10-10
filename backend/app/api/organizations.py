"""Organization endpoints (AC-1 through AC-11)."""

import uuid
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session, get_verified_principal
from app.core.deps import require_csrf
from app.core.errors import ApiError
from app.models import Organization
from app.services.authorization import (
    Principal,
    get_scoped_or_404,
    scoped_organization_directory,
    scoped_organizations,
)
from app.services.audit import log_audit_event
from app.services.complaint import upheld_complaint_count, upheld_complaint_counts
from app.services.organization import (
    AlreadyMemberError,
    DomainAlreadyVerifiedError,
    DomainLockedError,
    DuplicateLegalIdError,
    FreeEmailDomainError,
    InvalidUnitError,
    RateLimitError,
    change_organization_domain,
    create_organization,
    invite_org_member,
    list_approvers,
    list_org_members,
    normalize_unit,
    set_showcase_public,
    update_member_unit,
    verify_domain,
)
from app.services.outbox import enqueue
from app.services.rate_limit import RateLimitExceeded

router = APIRouter(prefix="/organizations", tags=["organizations"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class OrganizationCreate(BaseModel):
    """Request schema for POST /organizations."""

    name: str = Field(..., min_length=1)
    domain: str | None = None
    legal_id: str | None = None


class OrganizationUpdate(BaseModel):
    """Request schema for PATCH /organizations/{id}: the domain can be changed (not
    cleared) and the public showcase switched; at least one of them is required."""

    domain: str | None = None
    showcase_public: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "OrganizationUpdate":
        if self.domain is None and self.showcase_public is None:
            raise ValueError("domain or showcase_public is required")
        return self


class OrganizationResponse(BaseModel):
    """Response schema for Organization."""

    id: uuid.UUID
    name: str
    domain: str | None
    legal_id: str | None
    verification_level: str
    status: str
    showcase_public: bool

    class Config:
        from_attributes = True


class OrganizationDirectoryEntry(BaseModel):
    """Response schema for GET /organizations (directory/picker) — deliberately
    thinner than OrganizationResponse: no legal_id/status, those are internal
    to the organization's own admins, not the browsing talent."""

    id: uuid.UUID
    name: str
    domain: str | None
    verification_level: str
    upheld_complaint_count: int = 0  # admin-upheld complaints (sikayet-backend C7)

    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """GET /organizations/{id}: OrganizationResponse + the admin-upheld complaint count."""

    upheld_complaint_count: int


class OrganizationDirectoryResponse(BaseModel):
    items: list[OrganizationDirectoryEntry]


class OrganizationMemberInvite(BaseModel):
    """Request schema for POST /organizations/{id}/members."""

    email: str
    role: str  # ADMIN or MEMBER
    unit: str | None = None


class OrganizationMemberResponse(BaseModel):
    """Response schema for OrganizationMember."""

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    status: str

    class Config:
        from_attributes = True


class OrgMemberListEntry(BaseModel):
    """GET /organizations/{id}/members row; email is only filled for the org's admins."""

    user_id: uuid.UUID
    display_name: str
    role: str
    unit: str | None
    open_assigned_count: int
    email: str | None


class OrgMemberUnitUpdate(BaseModel):
    """Request schema for PATCH /organizations/{id}/members/{user_id}; null clears the unit."""

    unit: str | None


class ApproverEntry(BaseModel):
    """GET /organizations/{id}/approvers row — deliberately no e-mail and no role."""

    user_id: uuid.UUID
    display_name: str
    unit: str | None


def _invalid_unit() -> ApiError:
    return ApiError(422, "INVALID_UNIT", "Birim adı en fazla 60 karakter olabilir")


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
# PLAN 3.53: Organization directory (picker for "Yeni Çalışma")
# ============================================================================


DIRECTORY_MAX_RESULTS = 50


@router.get("/", status_code=200, response_model=OrganizationDirectoryResponse)
def list_organization_directory_endpoint(
    q: str | None = None,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
) -> OrganizationDirectoryResponse:
    """
    PLAN 3.53: any authenticated talent browses/searches the organization
    directory to pick one and start a new engagement with it
    (POST /engagements already requires only an organization_id, no prior
    membership). This is intentionally NOT tenant-scoped — see
    scoped_organization_directory()'s docstring.

    Args:
        q: optional case-insensitive substring match on name

    Returns:
        Up to DIRECTORY_MAX_RESULTS organizations, ordered by name.
    """
    query = scoped_organization_directory(session, principal)
    if q:
        query = query.where(Organization.name.ilike(f"%{q}%"))
    query = query.order_by(Organization.name).limit(DIRECTORY_MAX_RESULTS)

    orgs = session.execute(query).scalars().all()
    upheld = upheld_complaint_counts(session, "ORGANIZATION", [org.id for org in orgs])
    return OrganizationDirectoryResponse(
        items=[
            OrganizationDirectoryEntry.model_validate(org).model_copy(
                update={"upheld_complaint_count": upheld.get(org.id, 0)}
            )
            for org in orgs
        ]
    )


# ============================================================================
# AC-1: Create Organization
# ============================================================================


@router.post("/", status_code=201, response_model=OrganizationResponse)
def create_organization_endpoint(
    payload: OrganizationCreate,
    principal: Principal = Depends(get_verified_principal),
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
# YET-237 / L-02: Change organization domain
# ============================================================================


@router.patch("/{organization_id}", status_code=200, response_model=OrganizationResponse)
def update_organization_endpoint(
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> Organization:
    """
    Change the organization's domain and/or public showcase switch (org ADMIN only).

    Domain — T1: changes. T2: changes and drops to T1 (re-verify via DNS). T3/T4: locked.
    Same value is a 200 no-op. showcase_public (SPRINT D2) is set independently.

    Status codes:
        200: Changed (or same value)
        400: FREE_EMAIL_DOMAIN
        404: Organization not found / caller is not an ADMIN of it
        409: ALAN_ADI_KILITLI (T3/T4) / DOMAIN_ALREADY_VERIFIED (held by another org)
        422: Invalid domain format / empty body
    """
    scoped = scoped_organizations(session, principal)
    org = get_scoped_or_404(scoped.where(Organization.id == organization_id), session)
    if not org or organization_id not in principal.org_admin_ids:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")

    if payload.domain is not None:
        _change_domain(org, payload.domain, principal, session)

    if payload.showcase_public is not None and set_showcase_public(org, payload.showcase_public, session):
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="ORGANIZATION_SHOWCASE_CHANGED",
            subject_type="organization",
            subject_id=organization_id,
            result="SUCCESS",
            metadata={"showcase_public": payload.showcase_public},
        )

    return org


def _change_domain(org: Organization, domain: str, principal: Principal, session: Session) -> None:
    new_domain = domain.strip()
    if not validate_hostname(new_domain):
        raise ApiError(422, "INVALID_DOMAIN_FORMAT", "Geçersiz alan adı biçimi")

    try:
        changed, level_before = change_organization_domain(org, new_domain, session)
    except DomainLockedError:
        raise ApiError(409, "ALAN_ADI_KILITLI", "Doğrulanmış kurumun alan adı değiştirilemez")
    except FreeEmailDomainError:
        raise ApiError(400, "FREE_EMAIL_DOMAIN", "Ücretsiz e-posta sağlayıcısı alan adı olamaz")
    except DomainAlreadyVerifiedError:
        raise ApiError(409, "DOMAIN_ALREADY_VERIFIED", "Alan adı başka bir kurumda doğrulanmış")

    if changed:
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="ORGANIZATION_DOMAIN_CHANGED",
            subject_type="organization",
            subject_id=org.id,
            result="SUCCESS",
            metadata={"from_level": level_before, "to_level": org.verification_level},
        )


# ============================================================================
# AC-3: Invite Member to Organization
# ============================================================================


@router.post("/{organization_id}/members", status_code=202)
def invite_member_endpoint(
    organization_id: uuid.UUID,
    payload: OrganizationMemberInvite,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
):
    """
    AC-1/AC-2/AC-4: Invite user to organization (ADMIN-only action).
    AC-1: Bilinen e-posta → 202 {"status": "queued"}, üyelik + outbox enqueue + audit
    AC-2: Bilinmeyen e-posta → 202 {"status": "queued"}, hiç üyelik oluşmaz, yalnız audit
    AC-4: Zaten üye → 202 (rol değişmez)
    AC-3: Geçersiz rol → 422 INVALID_ROLE
    AC-S1: Tenant isolation — non-ADMIN or out-of-scope gets 404.
    AC-S6/AC-S7: outbox + audit same transaction.

    Args:
        organization_id: Target organization
        payload: email, role
        principal: Authenticated principal
        session: Database session

    Returns:
        {"status": "queued"}

    Status codes:
        202: Invitation queued (whether member created or not)
        404: Organization not found or not authorized
        422: Invalid role
    """
    # AC-3: Validate role (HAND, not Pydantic Literal)
    if payload.role not in ("ADMIN", "MEMBER"):
        raise ApiError(422, "INVALID_ROLE", "Geçerli rol değeri: ADMIN veya MEMBER")

    # AC-S1: Check organization exists and is in principal's scope + is ADMIN
    scoped = scoped_organizations(session, principal)
    org_query = scoped.where(Organization.id == organization_id)
    org = get_scoped_or_404(org_query, session)
    if not org:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")

    # Check if principal is ADMIN of this organization
    if organization_id not in principal.org_admin_ids:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")

    # SPRINT D2: optional unit label, validated after the scope check
    try:
        unit = normalize_unit(payload.unit)
    except InvalidUnitError:
        raise _invalid_unit()

    # Invite member (isolate exception handling to invite_org_member only)
    member = None
    try:
        member = invite_org_member(
            organization_id=organization_id,
            email=payload.email,
            role=payload.role,
            session=session,
            unit=unit,
        )
    except AlreadyMemberError:
        # AC-4: Zaten üye → 202 (rol değişmez, hiçbir şey yapılmaz)
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="INVITE_ORG_MEMBER",
            subject_type="organization",
            subject_id=organization_id,
            result="SUCCESS",
            metadata={
                "organization_id": str(organization_id),
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
            action="INVITE_ORG_MEMBER",
            subject_type="organization",
            subject_id=organization_id,
            result="SUCCESS",
            metadata={
                "organization_id": str(organization_id),
                "role": payload.role,
                "reason": "user_not_found",
            },
        )

    # AC-1: Member created successfully → enqueue + audit (outside invite_org_member exception handler)
    if member:
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

        # Log audit event
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

    return {"status": "queued"}


# ============================================================================
# SPRINT D2: team list, unit labels, approver picker
# ============================================================================


@router.get("/{organization_id}/members", status_code=200, response_model=list[OrgMemberListEntry])
def list_members_endpoint(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> list[OrgMemberListEntry]:
    """
    Team list for any member of the organization; e-mail only for its admins.

    Status codes:
        200: List (admins first, then by unit and name)
        404: Organization not found / caller is not a member of it
    """
    scoped = scoped_organizations(session, principal)
    org = get_scoped_or_404(scoped.where(Organization.id == organization_id), session)
    if not org:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")

    rows = list_org_members(
        session, organization_id, include_email=organization_id in principal.org_admin_ids
    )
    return [OrgMemberListEntry.model_validate(row, from_attributes=True) for row in rows]


@router.patch(
    "/{organization_id}/members/{user_id}", status_code=200, response_model=OrgMemberListEntry
)
def update_member_unit_endpoint(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: OrgMemberUnitUpdate,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
    _csrf: None = Depends(require_csrf),
) -> OrgMemberListEntry:
    """
    Set or clear a member's unit (org ADMIN only). Blank text clears it.

    Status codes:
        200: Updated member row (same value is a no-op)
        404: Organization not found / caller is not its ADMIN / user is not a member of it
        422: INVALID_UNIT (longer than 60 characters)
    """
    scoped = scoped_organizations(session, principal)
    org = get_scoped_or_404(scoped.where(Organization.id == organization_id), session)
    if not org or organization_id not in principal.org_admin_ids:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")

    try:
        result = update_member_unit(session, organization_id, user_id, payload.unit)
    except InvalidUnitError:
        raise _invalid_unit()
    if result is None:
        raise ApiError(404, "NOT_FOUND", "Üye bulunamadı")

    row, changed = result
    if changed:
        log_audit_event(
            session=session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="ORG_MEMBER_UNIT_CHANGED",
            subject_type="organization",
            subject_id=organization_id,
            result="SUCCESS",
            metadata={"member_user_id": str(user_id), "cleared": row.unit is None},
        )
    return OrgMemberListEntry.model_validate(row, from_attributes=True)


@router.get("/{organization_id}/approvers", status_code=200, response_model=list[ApproverEntry])
def list_approvers_endpoint(
    organization_id: uuid.UUID,
    principal: Principal = Depends(get_verified_principal),
    session: Session = Depends(get_session),
) -> list[ApproverEntry]:
    """
    Approver picker for a student starting an engagement: any e-mail-verified
    user, no membership needed (like the directory). Name + unit only.

    Status codes:
        200: List (by unit, no unit last, then name)
        401: Unauthenticated / EMAIL_NOT_VERIFIED
        404: Organization not found, deleted or not ACTIVE (same body)
        429: RATE_LIMITED (60/min/user, shared with Keşfet)
    """
    try:
        rows = list_approvers(session, principal, organization_id)
    except RateLimitExceeded as exc:
        raise ApiError(
            429,
            "RATE_LIMITED",
            "Çok fazla istek yapıldı. Lütfen biraz sonra tekrar deneyin.",
            headers={"Retry-After": str(exc.retry_after)},
        )
    if rows is None:
        raise ApiError(404, "NOT_FOUND", "Organizasyon bulunamadı")
    return [ApproverEntry.model_validate(row, from_attributes=True) for row in rows]


# ============================================================================
# AC-5/AC-6/AC-7/AC-8: Verify Organization Domain
# ============================================================================


@router.post("/{organization_id}/verify-domain", status_code=200, response_model=DomainVerifyResponse)
def verify_domain_endpoint(
    organization_id: uuid.UUID,
    payload: DomainVerifyRequest = DomainVerifyRequest(),
    principal: Principal = Depends(get_verified_principal),
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
    if organization_id not in principal.org_admin_ids:
        raise HTTPException(status_code=404, detail="Organization not found")

    # AC-S5: Validate domain format before DNS lookup (prevent SSRF)
    if not validate_hostname(org.domain):
        raise HTTPException(status_code=400, detail="INVALID_DOMAIN_FORMAT")

    try:
        result = verify_domain(
            organization_id=organization_id,
            session=session,
        )

        # If verification succeeded, record who promoted the org to T2 (an org already at T2+ keeps its record)
        if result["status"] == "verified":
            if result.get("promoted"):
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
                metadata={"domain": org.domain, "verification_level": org.verification_level},
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


@router.get("/{organization_id}", status_code=200, response_model=OrganizationDetailResponse)
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

    return OrganizationDetailResponse(
        **OrganizationResponse.model_validate(org).model_dump(),
        upheld_complaint_count=upheld_complaint_count(session, "ORGANIZATION", org.id),
    )
