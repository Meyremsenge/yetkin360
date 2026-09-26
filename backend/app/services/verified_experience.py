"""Verified experience service: business logic for token generation and fetching own verified experiences.

Implements:
- YET-106 (public-dogrulama-linki): Token generation for public verification links (AC-S1)
- AC-7, AC-8: GET /talents/me/verified-experiences listing logic
"""

import secrets

from sqlalchemy.orm import Session

from app.services.authorization import Principal, scoped_own_verified_experiences


def generate_public_token() -> str:
    """
    Generate a cryptographically secure random token for public verification link.

    Uses secrets.token_urlsafe() with 32 bytes (256 bits) entropy.
    This exceeds AC-S1 minimum requirement of ≥128 bits.

    Alphabet: base64url (64 chars)
    Length: typically 43-44 characters (encoding 32 bytes)
    Entropy: 256 bits >> 128 bits minimum (AC-S1)

    Usage:
        VerifiedExperience.public_token üretiminde kullanılacak (T8 attestation transition).
        NOTE: Bu fonksiyon şu an YERINDEkalmış — token üretimi T8 transition'a entegre etme
              ayrı bir görev (YET-???).

    Returns:
        str: Randomly generated token suitable for URL-safe use
    """
    return secrets.token_urlsafe(32)


def list_own_verified_experiences(
    session: Session,
    principal: Principal,
) -> list[dict]:
    """
    List verified experiences owned by the authenticated talent.

    AC-7, AC-8: GET /talents/me/verified-experiences logic.
    - Returns verified experiences scoped to talent (via scoped_own_verified_experiences)
    - Includes all visibility levels (owner sees PRIVATE records)
    - No visibility filtering (sahibi kendi tüm kayıtlarını görür)
    - Empty list if no verified experiences (AC-8)

    Args:
        session: Database session
        principal: Authorization context (must have talent_id)

    Returns:
        List of dicts: [{"id", "organization_name_snapshot", "role_snapshot", ...}, ...]
    """
    # Get scoped verified experiences for this talent
    scoped_query = scoped_own_verified_experiences(session, principal)
    verified_experiences = session.execute(scoped_query).scalars().all()

    # Build response items
    items = []
    for ve in verified_experiences:
        items.append({
            "id": str(ve.id),
            "organization_name_snapshot": ve.organization_name_snapshot,
            "role_snapshot": ve.role_snapshot,
            "started_on_snapshot": ve.started_on_snapshot.isoformat() if ve.started_on_snapshot else None,
            "ended_on_snapshot": ve.ended_on_snapshot.isoformat() if ve.ended_on_snapshot else None,
            "institution_name_snapshot": ve.institution_name_snapshot,
            "claim_type": ve.claim_type,
            "visibility": ve.visibility,
            "public_token": ve.public_token,
            "created_at": ve.created_at.isoformat() if ve.created_at else None,
        })

    return items
