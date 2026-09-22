"""Skill search service (YET-10)."""

from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models import Skill


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
