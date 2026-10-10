"""Talent profile service: core business logic for talent profile management."""

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)
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
        Dict with keys: user, talent_profile, organizations, institutions.
        talent_profile is None for users without one (e.g. the seeded platform admin).
    """
    # Get talent profile for this user via scoped query
    talent_query = scoped_talent_profiles(session, principal)
    talent = get_scoped_or_404(talent_query, session)

    # Organizations this user is a member of (scoped query), with the user's own
    # membership role and unit. The join is pinned to principal.user_id, so another
    # member's role/unit can never appear (SPRINT A AC-S3).
    org_rows = session.execute(
        scoped_organizations(session, principal)
        .join(
            OrganizationMember,
            and_(
                OrganizationMember.organization_id == Organization.id,
                OrganizationMember.user_id == principal.user_id,
            ),
        )
        .add_columns(OrganizationMember.role, OrganizationMember.unit)
        .order_by(Organization.name)
    ).all()
    organizations = [
        {"id": org.id, "name": org.name, "role": role, "unit": unit} for org, role, unit in org_rows
    ]

    # Institutions this user is a member of (scoped query), with the user's own role.
    inst_rows = session.execute(
        scoped_institutions(session, principal)
        .join(
            InstitutionMember,
            and_(
                InstitutionMember.institution_id == Institution.id,
                InstitutionMember.user_id == principal.user_id,
            ),
        )
        .add_columns(InstitutionMember.role)
        .order_by(Institution.name)
    ).all()
    institutions = [{"id": inst.id, "name": inst.name, "role": role} for inst, role in inst_rows]

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

    # The pre-check above has a race window: two concurrent requests can both
    # pass it for the same free slug, then both try to commit. The DB's unique
    # constraint on public_slug is the real guard — catch its violation here
    # and translate it to the same SlugTakenError instead of letting a bare
    # IntegrityError surface as a 500.
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        if "public_slug" in updates:
            raise SlugTakenError(f"Slug {updates['public_slug']} is already taken")
        raise

    return talent_profile
