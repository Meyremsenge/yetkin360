"""Skill search + admin management service (YET-10, YET-137)."""

import uuid
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models import Skill


class DuplicateSkillSlugError(Exception):
    """Raised when creating a skill with a slug that already exists."""


class InvalidSkillReferenceError(Exception):
    """Raised when parent_id/merged_into_id points to a missing, self, or non-ACTIVE skill."""


class SkillStatusTransitionError(Exception):
    """Raised when attempting an invalid skill status transition (e.g., MERGED→DEPRECATED)."""


def list_all_skills(session: Session, limit: int = 200, offset: int = 0) -> Sequence[Skill]:
    """
    List ALL skills regardless of status (ACTIVE/DEPRECATED/MERGED) — for
    admin taxonomy management (YET-137). Unlike search_skills(), this is not
    filtered to ACTIVE only, since admins need to see/manage deprecated and
    merged skills too.
    """
    stmt = select(Skill).order_by(Skill.name_tr).limit(limit).offset(offset)
    return session.execute(stmt).scalars().all()


def search_skills(
    session: Session,
    q: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> Sequence[Skill]:
    """
    Search ACTIVE skills by query, category, and limit.

    Args:
        session: Database session
        q: Search query in name_tr, name_en, slug (case-insensitive ILIKE)
        category: Filter by category (LANGUAGE|FRAMEWORK|TOOL|DOMAIN|SOFT)
        limit: Max results to return (1-100, default 50)

    Returns:
        List of ACTIVE Skill objects matching the criteria.
        Only skills with status='ACTIVE' are returned.
    """
    stmt = select(Skill).where(Skill.status == "ACTIVE")

    if q:
        escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(
            or_(
                Skill.name_tr.ilike(f"%{escaped_q}%", escape="\\"),
                Skill.name_en.ilike(f"%{escaped_q}%", escape="\\"),
                Skill.slug.ilike(f"%{escaped_q}%", escape="\\"),
            )
        )

    if category:
        stmt = stmt.where(Skill.category == category)

    stmt = stmt.limit(limit)

    return session.execute(stmt).scalars().all()


def create_skill(
    session: Session,
    slug: str,
    name_tr: str,
    name_en: str | None,
    category: str,
    parent_id: uuid.UUID | None = None,
) -> Skill:
    """
    Create a new skill (admin-only — YET-137). No free-text skill creation
    exists elsewhere; this is the single controlled entry point (docs/DOMAIN.md §3.5).

    Raises:
        DuplicateSkillSlugError: slug already taken.
        InvalidSkillReferenceError: parent_id does not reference an existing skill.
    """
    if session.execute(select(Skill).where(Skill.slug == slug)).scalars().first():
        raise DuplicateSkillSlugError(f"Skill slug {slug!r} already exists")

    if parent_id is not None and session.get(Skill, parent_id) is None:
        raise InvalidSkillReferenceError(f"parent_id {parent_id} bulunamadı")

    skill = Skill(
        slug=slug,
        name_tr=name_tr,
        name_en=name_en,
        category=category,
        parent_id=parent_id,
    )
    session.add(skill)
    session.flush()
    return skill


# Sentinel: indicates parent_id parameter was explicitly passed (including None)
_UNSET = object()


def update_skill(
    session: Session,
    skill_id: uuid.UUID,
    name_tr: str | None = None,
    name_en: str | None = None,
    category: str | None = None,
    parent_id = _UNSET,  # AC-13: Can be None to remove parent
    status: str | None = None,  # AC-13: Status transition (validate MERGED→DEPRECATED)
) -> Skill | None:
    """
    Update a skill's editable fields (admin-only — YET-137).
    AC-13 (L-10): Handle parent_id removal and MERGED→DEPRECATED validation.

    Returns None if skill_id does not exist.

    Raises:
        InvalidSkillReferenceError: parent_id is the skill itself or does not exist.
        SkillStatusTransitionError: Cannot transition MERGED→DEPRECATED.
    """
    skill = session.get(Skill, skill_id)
    if skill is None:
        return None

    # AC-13: Handle parent_id (including None to remove parent)
    if parent_id is not _UNSET:
        if parent_id is not None:
            if parent_id == skill_id:
                raise InvalidSkillReferenceError("Bir skill kendi üst kategorisi olamaz")
            if session.get(Skill, parent_id) is None:
                raise InvalidSkillReferenceError(f"parent_id {parent_id} bulunamadı")
            skill.parent_id = parent_id
        else:
            # Explicitly remove parent
            skill.parent_id = None

    # AC-13: Validate status transitions
    if status is not None:
        if status == "DEPRECATED" and skill.merged_into_id is not None:
            raise SkillStatusTransitionError(
                "MERGED bir beceri DEPRECATED durumuna geçemez (merged_into_id tutarlılığı)"
            )
        skill.status = status

    if name_tr is not None:
        skill.name_tr = name_tr
    if name_en is not None:
        skill.name_en = name_en
    if category is not None:
        skill.category = category

    session.flush()
    return skill


def deprecate_skill(session: Session, skill_id: uuid.UUID) -> Skill | None:
    """Mark a skill DEPRECATED (admin-only — YET-137). Returns None if not found."""
    skill = session.get(Skill, skill_id)
    if skill is None:
        return None
    skill.status = "DEPRECATED"
    session.flush()
    return skill


def merge_skill(session: Session, skill_id: uuid.UUID, merged_into_id: uuid.UUID) -> Skill | None:
    """
    Mark a skill MERGED into another ACTIVE skill (admin-only — YET-137).
    docs/DOMAIN.md §3.5: queries redirect to the merge target.

    Returns None if skill_id does not exist.

    Raises:
        InvalidSkillReferenceError: merge target is the skill itself, missing, or not ACTIVE.
    """
    skill = session.get(Skill, skill_id)
    if skill is None:
        return None

    if merged_into_id == skill_id:
        raise InvalidSkillReferenceError("Bir skill kendisiyle birleştirilemez")

    target = session.get(Skill, merged_into_id)
    if target is None or target.status != "ACTIVE":
        raise InvalidSkillReferenceError(f"merged_into_id {merged_into_id} geçerli bir ACTIVE skill değil")

    skill.status = "MERGED"
    skill.merged_into_id = merged_into_id
    session.flush()
    return skill
