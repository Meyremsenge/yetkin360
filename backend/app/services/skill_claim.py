"""Skill claim service: core business logic for talent skill claims."""

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Skill, SkillClaim
from app.services.authorization import Principal, scoped_skill_claims


class SkillNotFoundError(Exception):
    """Raised when attempting to claim a skill that does not exist or is not ACTIVE."""
    pass


class SkillNotFoundStatusError(Exception):
    """Raised when attempting to claim a MERGED/DEPRECATED skill."""
    pass


class SkillAlreadyClaimedError(Exception):
    """Raised when attempting to claim a skill that is already claimed."""
    pass


class SkillClaimNotFoundError(Exception):
    """Raised when attempting to delete a skill claim that does not exist."""
    pass


def add_skill_claim(
    session: Session,
    principal: Principal,
    skill_id: str,
    claimed_level: str | None = None,
) -> SkillClaim:
    """
    Add a new skill claim for the authenticated talent.

    AC-1: POST /talents/me/skills logic.
    - Validates skill exists and is ACTIVE
    - Validates skill is not already claimed
    - Atomicity: all validations before INSERT

    Args:
        session: Database session
        principal: Authorization context (must have talent_id)
        skill_id: UUID of skill to claim
        claimed_level: Optional level (BEGINNER/INTERMEDIATE/ADVANCED)

    Returns:
        Created SkillClaim object

    Raises:
        SkillNotFoundError: If skill does not exist or is not ACTIVE
        SkillAlreadyClaimedError: If talent already claimed this skill
    """
    import uuid

    # Parse skill_id
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise SkillNotFoundError(f"Invalid skill_id format: {skill_id}")

    # Validate skill exists and is ACTIVE (AC-4, AC-6)
    skill = session.execute(
        select(Skill).where(Skill.id == skill_uuid)
    ).scalar_one_or_none()

    if not skill or skill.status != "ACTIVE":
        raise SkillNotFoundError(f"Skill {skill_id} not found or not active")

    # Validate skill is not already claimed (AC-5)
    existing_claim = session.execute(
        select(SkillClaim).where(
            and_(
                SkillClaim.talent_id == principal.talent_id,
                SkillClaim.skill_id == skill_uuid,
            )
        )
    ).scalar_one_or_none()

    if existing_claim:
        raise SkillAlreadyClaimedError(
            f"Skill {skill_id} already claimed by talent {principal.talent_id}"
        )

    # Create new claim (AC-1)
    claim = SkillClaim(
        talent_id=principal.talent_id,
        skill_id=skill_uuid,
        claimed_level=claimed_level,
        source="MANUAL",
        confirmed_by_user_at=None,
    )
    session.add(claim)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise SkillAlreadyClaimedError(
            f"Skill {skill_id} already claimed by talent {principal.talent_id}"
        )

    return claim


def list_skill_claims(
    session: Session,
    principal: Principal,
) -> list[dict]:
    """
    List all skill claims for the authenticated talent.

    AC-2: GET /talents/me/skills logic.
    - Returns claims scoped to talent (via scoped_skill_claims)
    - Each item includes skill details (id, slug, name_tr, name_en, category)
    - Empty list if no claims (AC-8)

    Args:
        session: Database session
        principal: Authorization context (must have talent_id)

    Returns:
        List of dicts: [{"skill": {...}, "claimed_level": ...}, ...]
    """
    # Get scoped claims for this talent
    scoped_query = scoped_skill_claims(session, principal)
    claims = session.execute(scoped_query).scalars().all()

    # Build response items with skill details joined
    items = []
    for claim in claims:
        # Fetch the skill for this claim
        skill = session.execute(
            select(Skill).where(Skill.id == claim.skill_id)
        ).scalar_one()

        items.append({
            "skill": {
                "id": str(skill.id),
                "slug": skill.slug,
                "name_tr": skill.name_tr,
                "name_en": skill.name_en,
                "category": skill.category,
            },
            "claimed_level": claim.claimed_level,
        })

    return items


def remove_skill_claim(
    session: Session,
    principal: Principal,
    skill_id: str,
) -> None:
    """
    Remove a skill claim for the authenticated talent.

    AC-3: DELETE /talents/me/skills/{skill_id} logic.
    - Hard-delete (AC-3: no deleted_at column)
    - Only talent's own claims can be deleted (AC-S4)
    - 404 if claim does not exist (AC-7)

    Args:
        session: Database session
        principal: Authorization context (must have talent_id)
        skill_id: UUID of skill claim to remove

    Raises:
        SkillClaimNotFoundError: If claim does not exist or belongs to another talent
    """
    import uuid

    # Parse skill_id
    try:
        skill_uuid = uuid.UUID(skill_id)
    except ValueError:
        raise SkillClaimNotFoundError(f"Invalid skill_id format: {skill_id}")

    # Fetch claim scoped to this talent (AC-S4: 404 if not found or other talent's)
    scoped_query = scoped_skill_claims(session, principal).where(
        SkillClaim.skill_id == skill_uuid
    )
    claim = session.execute(scoped_query).scalar_one_or_none()

    if not claim:
        raise SkillClaimNotFoundError(
            f"Skill claim {skill_id} not found for talent {principal.talent_id}"
        )

    # Hard-delete (AC-3)
    session.delete(claim)
    session.flush()
