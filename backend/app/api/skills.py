"""Skill search endpoint (YET-10 — skill-search)."""

from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.models import User
from app.services.skill import search_skills

router = APIRouter(prefix="/skills", tags=["skills"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class SkillCategory(str, Enum):
    """Valid skill categories (Pydantic enum for validation)."""

    LANGUAGE = "LANGUAGE"
    FRAMEWORK = "FRAMEWORK"
    TOOL = "TOOL"
    DOMAIN = "DOMAIN"
    SOFT = "SOFT"


class SkillItemResponse(BaseModel):
    """Single skill in search results."""

    id: str
    slug: str
    name_tr: str
    name_en: Optional[str] = None
    category: str
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Response schema for GET /skills."""

    items: list[SkillItemResponse]


# ============================================================================
# AC-1..AC-9: GET /skills
# ============================================================================


@router.get("", response_model=SkillListResponse)
def list_skills(
    q: Optional[str] = Query(None, description="Search query (name_tr, name_en, slug)"),
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    limit: int = Query(50, gt=0, le=100, description="Max results (1-100)"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SkillListResponse:
    """
    AC-1..AC-9: Search ACTIVE skills.

    Parameters:
        q: Search query in skill name_tr, name_en, or slug (case-insensitive, optional)
        category: Filter by category enum (optional)
        limit: Max results to return (1-100, default 50)

    Authentication:
        - Required: get_current_user dependency (401 if missing)

    Returns:
        200 + {items: [{id, slug, name_tr, name_en, category, parent_id}, ...]}
        Only ACTIVE skills are returned.
        Internal fields (status, merged_into_id, created_at, updated_at) are never exposed.
        Empty list {} for no matches (not 404).

    Errors:
        - 401: Unauthenticated (missing/invalid X-Debug-User-Id)
        - 422: Invalid category enum or limit > 100 / <= 0 (Pydantic validation)
    """
    skills = search_skills(
        session,
        q=q,
        category=category.value if category else None,
        limit=limit,
    )

    items = [
        SkillItemResponse(
            id=str(skill.id),
            slug=skill.slug,
            name_tr=skill.name_tr,
            name_en=skill.name_en,
            category=skill.category,
            parent_id=str(skill.parent_id) if skill.parent_id else None,
        )
        for skill in skills
    ]

    return SkillListResponse(items=items)
