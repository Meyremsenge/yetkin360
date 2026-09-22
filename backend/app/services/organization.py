"""Organization service: core business logic for organization management.

Implements AC-1 through AC-11 from atdd.md.
Domain verification requires dnspython for DNS TXT lookups.
"""

import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

import dns.resolver
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationMember, User


# ============================================================================
# Exception Classes
# ============================================================================


class DuplicateLegalIdError(Exception):
    """Raised when creating organization with duplicate legal_id."""

    pass


class AlreadyMemberError(Exception):
    """Raised when inviting user who is already an organization member."""

    pass


class FreeEmailDomainError(Exception):
    """Raised when attempting to verify domain of free email provider."""

    pass


class DomainAlreadyVerifiedError(Exception):
    """Raised when domain is already verified in another organization."""

    pass


class RateLimitError(Exception):
    """Raised when verify-domain is called too frequently (AC-11/AC-S4)."""

    pass


# ============================================================================
# Core Service Functions
# ============================================================================


FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
}


def create_organization(
    name: str,
    domain: Optional[str],
    legal_id: Optional[str],
    caller_user_id: uuid.UUID,
    session: Session,
) -> Organization:
    """
    Create new organization. Caller becomes ADMIN member.

    AC-1: POST /organizations → 201, T1, caller becomes ADMIN.
    AC-S3: verification_level, verified_at, verified_by_user_id fields
           in input are ignored — always created as T1.

    Args:
        name: Organization name (required, non-empty validated in API layer)
        domain: Organization domain (optional, no unique constraint at T1)
        legal_id: Legal entity ID (optional, unique if provided)
        caller_user_id: User creating the organization
        session: Database session

    Returns:
        Organization object (T1 verification level, ACTIVE status)

    Raises:
        DuplicateLegalIdError: If legal_id already exists
    """
    # Check legal_id uniqueness (if provided)
    if legal_id:
        existing = session.execute(
            select(Organization).where(Organization.legal_id == legal_id)
        ).scalar_one_or_none()
        if existing:
            raise DuplicateLegalIdError(f"Legal ID {legal_id} already taken")

    # Create organization with T1 verification level (ignore any input attempt to set T2/T3/T4)
    organization = Organization(
        name=name,
        domain=domain,
        legal_id=legal_id,
        verification_level="T1",
        status="ACTIVE",
    )
    session.add(organization)
    session.flush()  # Get organization.id before creating member

    # Add caller as ADMIN member
    admin_member = OrganizationMember(
        organization_id=organization.id,
        user_id=caller_user_id,
        role="ADMIN",
        status="ACTIVE",
    )
    session.add(admin_member)
    session.flush()

    return organization


def invite_org_member(
    organization_id: uuid.UUID,
    email: str,
    role: str,
    session: Session,
) -> OrganizationMember:
    """
    Invite user to organization by email.

    AC-3: POST /organizations/{id}/members → 201, member created.
    AC-4: Duplicate membership → raise AlreadyMemberError.
    AC-S2: role must be ADMIN or MEMBER (validated in API, but checked here too).

    Args:
        organization_id: Target organization
        email: Email of user to invite
        role: "ADMIN" or "MEMBER"
        session: Database session

    Returns:
        OrganizationMember object (newly created)

    Raises:
        ValueError: If user not found
        AlreadyMemberError: If user is already a member
    """
    # Validate role
    if role not in ("ADMIN", "MEMBER"):
        raise ValueError(f"Invalid role: {role}")

    # Find user by email
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        raise ValueError(f"User {email} not found")

    # Check if already a member
    existing_member = session.execute(
        select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    if existing_member:
        raise AlreadyMemberError(f"User {email} is already a member of this organization")

    # Create new member
    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role=role,
        status="ACTIVE",
    )
    session.add(member)
    session.flush()

    return member


def verify_domain(
    organization_id: uuid.UUID,
    session: Session,
    resolver: Optional[dns.resolver.Resolver] = None,
    timeout: float = 3.0,
) -> dict:
    """
    Verify organization domain via DNS TXT lookup.

    AC-5: Free email domain (gmail.com, hotmail.com, etc.) → 400 error.
    AC-6/AC-8: Generate TXT token, attempt DNS lookup. If found → T2 + verified_at
               + verified_by_user_id. If not found/timeout/error → pending (200 with
               status="pending"), no state change.
    AC-9/AC-9b: Prevent same domain from being verified in multiple organizations
                (partial unique index in DB + code check).
    AC-11/AC-S4: Rate limit — max 1 verify-domain per 60 seconds per organization.

    Args:
        organization_id: Organization to verify
        session: Database session
        resolver: DNS resolver (default: dnspython's dns.resolver.Resolver)
                  Injected for testability (mock in tests)
        timeout: DNS query timeout in seconds (default: 3.0, matches AC-8 performance_target)

    Returns:
        dict with keys:
          - dns_txt_record: The TXT token to place in DNS (format: "yetkin360_verify_<token>")
          - status: "verified" or "pending"
          - organization (optional on verified): Organization object with updated T2 level

    Raises:
        ValueError: If organization not found
        FreeEmailDomainError: If domain is free email provider
        DomainAlreadyVerifiedError: If domain already verified in another org
        RateLimitError: If called more than once per 60 seconds
    """
    # Create default resolver if not provided (testability)
    if resolver is None:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout

    # Load organization
    org = session.execute(
        select(Organization).where(Organization.id == organization_id)
    ).scalar_one_or_none()
    if not org:
        raise ValueError(f"Organization {organization_id} not found")

    # Validate domain exists
    if not org.domain:
        raise ValueError(f"Organization {organization_id} has no domain set")

    # AC-5: Reject free email domains
    domain_lower = org.domain.lower()
    if domain_lower in FREE_EMAIL_DOMAINS:
        raise FreeEmailDomainError(f"Free email domain {org.domain} cannot be verified")

    # AC-11/AC-S4: Rate limit check (60 second cooldown)
    if org.last_verify_attempt_at:
        elapsed = datetime.now(timezone.utc) - org.last_verify_attempt_at
        if elapsed.total_seconds() < 60:
            raise RateLimitError(
                f"Too many verify-domain calls. Please wait {60 - int(elapsed.total_seconds())} seconds."
            )

    # Generate or reuse verification token
    if not org.domain_verification_token:
        org.domain_verification_token = secrets.token_urlsafe(16)
        session.flush()

    # Update last_verify_attempt_at for rate-limit tracking
    org.last_verify_attempt_at = datetime.now(timezone.utc)
    session.flush()
    session.commit()

    txt_record = f"yetkin360_verify_{org.domain_verification_token}"

    # AC-6/AC-7/AC-8: Attempt DNS TXT lookup
    try:
        answers = resolver.resolve(org.domain, "TXT", lifetime=timeout)
        # Check if our verification token is in the TXT records
        for rdata in answers:
            for txt_string in rdata.strings:
                if txt_string.decode().strip() == txt_record:
                    # AC-9: Check if domain is already verified in another organization
                    conflicting_org = session.execute(
                        select(Organization).where(
                            and_(
                                Organization.domain == org.domain,
                                Organization.verification_level == "T2",
                                Organization.id != organization_id,
                                Organization.deleted_at.is_(None),
                            )
                        )
                    ).scalar_one_or_none()
                    if conflicting_org:
                        raise DomainAlreadyVerifiedError(
                            f"Domain {org.domain} is already verified in another organization"
                        )

                    # Found! Update organization to T2
                    org.verification_level = "T2"
                    org.verified_at = datetime.now(timezone.utc)
                    # verified_by_user_id is set by the router (caller context)
                    session.flush()
                    return {
                        "dns_txt_record": txt_record,
                        "status": "verified",
                    }

        # TXT record not found, but DNS query succeeded
        return {
            "dns_txt_record": txt_record,
            "status": "pending",
        }

    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout, dns.exception.DNSException):
        # Any DNS error (domain not found, no answer, timeout, etc.) → pending
        # AC-8: "Hiçbir şey yapılamadı ama hata yok" — silent success with pending status
        return {
            "dns_txt_record": txt_record,
            "status": "pending",
        }
