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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationMember, User
from app.services.outbox import enqueue


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


class DomainLockedError(Exception):
    """Raised when changing the domain of an admin-approved (T3/T4) organization."""

    pass


# ============================================================================
# Core Service Functions
# ============================================================================


# Mailbox providers anyone can register on; owning an address there proves nothing about an organization.
FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "yandex.com",
    "icloud.com",
    "hotmail.com.tr",
    "outlook.com.tr",
    "protonmail.com",
    "mail.ru",
    "yahoo.com.tr",
    "googlemail.com",
    "live.com",
    "msn.com",
    "hotmail.co.uk",
    "hotmail.de",
    "hotmail.fr",
    "outlook.de",
    "yahoo.co.uk",
    "yahoo.de",
    "yahoo.fr",
    "ymail.com",
    "rocketmail.com",
    "gmx.com",
    "gmx.net",
    "gmx.de",
    "gmx.at",
    "gmx.ch",
    "aol.com",
    "mail.com",
    "proton.me",
    "pm.me",
    "tutanota.com",
    "zoho.com",
    "yandex.ru",
    "yandex.com.tr",
    "mynet.com",
}


def is_free_email_domain(domain: str) -> bool:
    """True for a listed provider or any subdomain of one (mail.gmail.com); lookalikes (notgmail.com) are not."""
    normalised = domain.strip().strip(".").lower()
    return any(normalised == free or normalised.endswith("." + free) for free in FREE_EMAIL_DOMAINS)

# Levels that already vouch for a domain; a second org may not claim it (GUV-09).
# Mirrors the partial UNIQUE ix_organizations_domain_verified (YET-241).
_DOMAIN_VERIFIED_LEVELS = ("T2", "T3", "T4")


def _domain_held_by_other_org(session: Session, domain: str, organization_id: uuid.UUID) -> bool:
    """True if another active org already holds `domain` at T2/T3/T4."""
    return (
        session.execute(
            select(Organization.id)
            .where(
                Organization.domain == domain,
                Organization.verification_level.in_(_DOMAIN_VERIFIED_LEVELS),
                Organization.id != organization_id,
                Organization.deleted_at.is_(None),
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _flush_domain_claim(session: Session, domain: str) -> None:
    """Flush pending changes; losing a race on the DB unique index is a domain conflict, not a 500."""
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise DomainAlreadyVerifiedError(f"Domain {domain} is already verified in another organization") from exc


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

    # PLAN 3.56: optional AI check of the organization's identity (name/domain
    # consistency) — flags for admin review only, never blocks creation.
    enqueue(
        session=session,
        topic="fraud.organization_identity_check_requested",
        payload={"organization_id": str(organization.id)},
    )

    return organization


def change_organization_domain(org: Organization, new_domain: str, session: Session) -> tuple[bool, str]:
    """
    Change an organization's domain (YET-237 / L-02). The caller has already checked
    that the actor is an ADMIN of `org` and that `new_domain` is a well-formed hostname.

    Same value (case-insensitive) is a no-op. T3/T4 are admin-approved and locked.
    A T2 org drops to T1 (verified_at/verified_by cleared): the DNS proof belonged to the
    old domain. The verification token is always dropped (it was issued for the old
    domain). last_verify_attempt_at is deliberately kept so changing the domain can not
    be used to dodge the verify-domain cooldown.

    Returns (changed, level_before).
    Raises DomainLockedError, FreeEmailDomainError, DomainAlreadyVerifiedError.
    """
    level_before = org.verification_level
    if org.domain is not None and org.domain.lower() == new_domain.lower():
        return False, level_before
    if level_before in ("T3", "T4"):
        raise DomainLockedError(str(org.id))
    if is_free_email_domain(new_domain):
        raise FreeEmailDomainError(f"Free email domain {new_domain} cannot be verified")
    if _domain_held_by_other_org(session, new_domain, org.id):
        raise DomainAlreadyVerifiedError(f"Domain {new_domain} is already verified in another organization")

    org.domain = new_domain
    org.domain_verification_token = None
    if level_before == "T2":
        org.verification_level = "T1"
        org.verified_at = None
        org.verified_by_user_id = None
    session.flush()
    return True, level_before


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
    if is_free_email_domain(org.domain):
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

    # YET-189: read everything the DNS step needs BEFORE commit. Commit expires ORM
    # attributes; touching them afterwards would autobegin a new transaction and the
    # DNS call (up to `timeout` s) would run while holding a pooled connection.
    domain = org.domain
    txt_record = f"yetkin360_verify_{org.domain_verification_token}"
    session.commit()

    # AC-6/AC-7/AC-8: Attempt DNS TXT lookup (no open transaction here)
    try:
        answers = resolver.resolve(domain, "TXT", lifetime=timeout)
        # Check if our verification token is in the TXT records
        for rdata in answers:
            # Not all Rdata subtypes carry .strings (only TXT-like records do);
            # a resolver could theoretically hand back a mixed answer set.
            for txt_string in getattr(rdata, "strings", ()):
                if txt_string.decode().strip() == txt_record:
                    # AC-9: Check if domain is already verified in another organization
                    if _domain_held_by_other_org(session, domain, organization_id):
                        raise DomainAlreadyVerifiedError(
                            f"Domain {domain} is already verified in another organization"
                        )

                    # Found! Promote T1 to T2; an org already at T2+ keeps its level (never downgrade)
                    promoted = org.verification_level == "T1"
                    if promoted:
                        org.verification_level = "T2"
                        org.verified_at = datetime.now(timezone.utc)
                    # verified_by_user_id is set by the router (caller context) when promoted
                    _flush_domain_claim(session, domain)
                    return {
                        "dns_txt_record": txt_record,
                        "status": "verified",
                        "promoted": promoted,
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


class NotPendingError(Exception):
    """Raised when rejecting an organization that is not in the verification queue."""


_LEVEL_RANK = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}


def list_verification_queue(session: Session, limit: int = 50, offset: int = 0) -> list[Organization]:
    """
    List organizations awaiting T3 review (admin-only — PLAN 3.6/YET-136).

    A T2 organization with a legal_id set is treated as "applied for T3"
    (docs/DOMAIN.md §3.4: T3 requires MERSİS/vergi no, simplified to legal_id
    in this schema — see AUTHORIZATION.md §2.4). Oldest first (fairness).
    Rejected applications (verification_rejected_at set) are excluded (YET-198).
    """
    stmt = (
        select(Organization)
        .where(
            Organization.verification_level == "T2",
            Organization.legal_id.isnot(None),
            Organization.status == "ACTIVE",
            Organization.deleted_at.is_(None),
            Organization.verification_rejected_at.is_(None),
        )
        .order_by(Organization.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.execute(stmt).scalars().all())


def set_verification_level(
    session: Session,
    organization_id: uuid.UUID,
    verification_level: str,
    admin_user_id: Optional[uuid.UUID],
) -> Optional[Organization]:
    """
    Set an organization's verification_level as a platform admin decision
    (admin-only — PLAN 3.6/YET-136). Rejecting is a separate action
    (reject_verification). verified_at/verified_by and the rejection mark are
    touched only when the level is RAISED; same value or downgrade changes
    nothing but the level itself (YET-198).

    Returns None if the organization does not exist. Raises DomainAlreadyVerifiedError
    when the new level is T2/T3/T4 and another active org already holds the domain at
    T2+ (YET-241): the DB partial UNIQUE decides, the savepoint rolls the change back.
    """
    org = session.get(Organization, organization_id)
    if org is None or org.deleted_at is not None:
        return None

    if _LEVEL_RANK[verification_level] > _LEVEL_RANK[org.verification_level]:
        org.verified_at = datetime.now(timezone.utc)
        org.verified_by_user_id = admin_user_id
        org.verification_rejected_at = None
    org.verification_level = verification_level
    _flush_domain_claim(session, org.domain or "")
    return org


def reject_verification(session: Session, organization_id: uuid.UUID) -> Optional[Organization]:
    """
    Reject a pending T3 application (admin-only — YET-198): the organization
    leaves the queue; level, verified_at and verified_by stay untouched.

    Returns None if the organization does not exist; raises NotPendingError if
    it is not currently in the queue (not T2 + legal_id, or already rejected).
    """
    org = session.get(Organization, organization_id)
    if org is None or org.deleted_at is not None:
        return None
    if (
        org.verification_level != "T2"
        or org.legal_id is None
        or org.status != "ACTIVE"
        or org.verification_rejected_at is not None
    ):
        raise NotPendingError(str(organization_id))

    org.verification_rejected_at = datetime.now(timezone.utc)
    session.flush()
    return org
