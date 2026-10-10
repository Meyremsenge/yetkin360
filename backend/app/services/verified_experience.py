"""Verified experience service: business logic for token generation and fetching own verified experiences.

Implements:
- YET-106 (public-dogrulama-linki): Token generation for public verification links (AC-S1)
- AC-7, AC-8: GET /talents/me/verified-experiences listing logic
- PLAN public-profil: owner changes visibility (D6 change-visibility)
"""

import uuid

from sqlalchemy.orm import Session

from app.models.verified_experience import VerifiedExperience, generate_public_token  # noqa: F401
from app.services.audit import log_audit_event
from app.services.authorization import Principal, get_scoped_or_404, scoped_own_verified_experiences

VISIBILITY_VALUES = ("PRIVATE", "INSTITUTION", "ORGANIZATIONS", "PUBLIC")


def _serialize(ve: VerifiedExperience) -> dict:
    return {
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
    }


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

    return [_serialize(ve) for ve in verified_experiences]


def change_own_verified_experience_visibility(
    session: Session,
    principal: Principal,
    experience_id: uuid.UUID,
    visibility: str,
) -> dict | None:
    """
    Change the visibility of one of the principal's own verified experiences.

    visibility is the only mutable column of the append-only verified_experiences
    table (DB trigger enforces it). Ownership comes from the session principal via
    scoped_own_verified_experiences(); another talent's id, an unknown id and a
    talent-less principal all return None, so the caller answers an identical 404.
    """
    if visibility not in VISIBILITY_VALUES:
        raise ValueError(f"visibility must be one of {VISIBILITY_VALUES}")

    scoped_query = scoped_own_verified_experiences(session, principal).where(
        VerifiedExperience.id == experience_id
    )
    ve = get_scoped_or_404(scoped_query, session)
    if ve is None:
        return None

    previous = ve.visibility
    if previous != visibility:
        ve.visibility = visibility
        session.flush()
        log_audit_event(
            session,
            actor_user_id=principal.user_id,
            actor_ip=None,
            action="VERIFIED_EXPERIENCE_VISIBILITY_CHANGED",
            subject_type="verified_experience",
            subject_id=ve.id,
            result="SUCCESS",
            metadata={"from": previous, "to": visibility},
        )
    return _serialize(ve)
