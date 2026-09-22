"""
Skill service: search business logic.

AC-1, AC-3, AC-4, AC-9: Arama sorgusu mantığı (ILIKE, DEPRECATED hariç, MERGED dahil).
Router'da iş mantığı yazılmaz — burada olur (CLAUDE.md kuralı).
"""

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import Skill
from app.services.authorization import Principal, scoped_skills
from app.schemas.skill import SkillResponse, SkillSearchResponse


def search_skills(
    session: Session,
    principal: Principal,
    q: str,
    limit: int = 20,
    offset: int = 0,
) -> SkillSearchResponse:
    """
    AC-1, AC-3, AC-4, AC-9: Search skills by name (ILIKE).

    Args:
        session: SQLAlchemy Session
        principal: Authorization context (authenticated user)
        q: Search query (min_length=2, max_length=200 — validated by router)
        limit: Max results to return (default 20, max 100 — validated by router)
        offset: Pagination offset (default 0)

    Returns:
        SkillSearchResponse: {"items": [...], "total": N}

    Behavior:
        - AC-1: Results sorted by name_tr (alphabetically ascending)
        - AC-3: Empty results → 200 + {"items": [], "total": 0} (not 404)
        - AC-4: DEPRECATED skills excluded, MERGED skills included with merged_into_id
        - AC-9 (AC-S1): Query parametrized (ilike()), no raw string interpolation (SQL injection safe)
    """
    # Get scoped skills query (global taxonomy, no tenant filter, but marshalled through scoped_skills)
    scoped_query = scoped_skills(session, principal)

    # Extract common filter conditions to avoid duplication
    filter_clause = (Skill.status != "DEPRECATED") & (
        (Skill.name_tr.ilike(f"%{q}%"))  # AC-1, AC-9: ilike() parametrized
        | (Skill.name_en.ilike(f"%{q}%"))
    )

    # Build the search query: case-insensitive match on name_tr or name_en
    # AC-9: Use ilike() for case-insensitive search; parameter is safe (SQLAlchemy parametrizes it)
    # DEPRECATED status excluded, MERGED included
    query = session.execute(
        scoped_query
        .where(filter_clause)
        .order_by(Skill.name_tr)  # AC-1: Sort alphabetically by Turkish name
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    # Count total matches (without LIMIT/OFFSET for total)
    total_count = session.execute(
        select(func.count(Skill.id))
        .select_from(Skill)
        .where(filter_clause)
    ).scalar() or 0

    # Collect merged_into_id values for MERGED skills
    merged_target_ids = [skill.merged_into_id for skill in query if skill.status == "MERGED" and skill.merged_into_id]

    # Fetch target skills if any MERGED skills exist
    target_skills_map = {}
    if merged_target_ids:
        target_skills = session.execute(
            select(Skill).where(Skill.id.in_(merged_target_ids))
        ).scalars().all()
        target_skills_map = {s.id: (s.slug, s.name_tr) for s in target_skills}

    # Convert ORM models to Pydantic responses
    # AC-4: MERGED skills include merged_into_id + merged_into_slug + merged_into_name_tr
    items = []
    for skill in query:
        response = SkillResponse.model_validate(skill)
        if skill.status == "MERGED" and skill.merged_into_id in target_skills_map:
            slug, name_tr = target_skills_map[skill.merged_into_id]
            response = response.model_copy(update={"merged_into_slug": slug, "merged_into_name_tr": name_tr})
        items.append(response)

    return SkillSearchResponse(items=items, total=total_count)
