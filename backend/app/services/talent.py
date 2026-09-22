"""Talent profile service: core business logic for talent profile management."""

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import TalentProfile, User
from app.services.authorization import Principal, get_scoped_or_404, scoped_institutions, scoped_organizations, scoped_talent_profiles


class SlugTakenError(Exception):
    """Raised when attempting to set a public_slug that is already taken."""

    pass


def get_me_context(principal: Principal, user: User, session: Session) -> dict:
    """
    Build GET /me response context for authenticated user.

    AC-1: Return user, talent_profile, organizations[], institutions[].

    Args:
        principal: Authorization context of authenticated principal
        user: Authenticated User object
        session: Database session

    Returns:
        Dict with keys: user, talent_profile, organizations, institutions
    """
    # Get talent profile for this user via scoped query
    talent_query = scoped_talent_profiles(session, principal)
    talent = get_scoped_or_404(talent_query, session)  # Guaranteed by register invariant
    if talent is None:
        raise ValueError("TalentProfile not found for authenticated user — register invariant violated")

    # Get organizations this user is member of via scoped query
    org_query = scoped_organizations(session, principal)
    organizations = session.execute(org_query).scalars().all()

    # Get institutions this user is member of via scoped query
    inst_query = scoped_institutions(session, principal)
    institutions = session.execute(inst_query).scalars().all()

    return {
        "user": user,
        "talent_profile": talent,
        "organizations": organizations,
        "institutions": institutions,
    }


def update_talent_profile(
    talent_profile: TalentProfile,
    updates: dict,
    session: Session,
) -> TalentProfile:
    """
    Update talent profile with given fields.

    AC-3 through AC-7: PATCH /talents/me logic.
    - Validates public_slug uniqueness BEFORE any DB write
    - Updates only provided fields
    - Atomicity: if slug conflicts, NO update occurs

    Args:
        talent_profile: TalentProfile object to update (already scoped/authorized)
        updates: Dict with field names and values (pre-validated by Pydantic)
        session: Database session

    Returns:
        Updated TalentProfile object

    Raises:
        SlugTakenError: If public_slug is taken by another profile
    """
    # Check public_slug uniqueness BEFORE touching DB
    if "public_slug" in updates and updates["public_slug"]:
        new_slug = updates["public_slug"]
        existing = session.execute(
            select(TalentProfile).where(
                and_(
                    TalentProfile.public_slug == new_slug,
                    TalentProfile.id != talent_profile.id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise SlugTakenError(f"Slug {new_slug} is already taken")

    # Apply updates (only provided fields)
    for field, value in updates.items():
        if hasattr(talent_profile, field):
            setattr(talent_profile, field, value)

    # Update timestamp
    talent_profile.updated_at = datetime.now(timezone.utc)

    session.flush()

    return talent_profile
