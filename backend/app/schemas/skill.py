"""
Skill response schemas (Pydantic DTOs).

AC-1, AC-4: Response shape {"items": [...], "total": N} with Skill fields.
"""

import uuid

from pydantic import BaseModel, Field


class SkillResponse(BaseModel):
    """
    Single skill in search results.

    AC-1: Each item has id, slug, name_tr, name_en, category, status.
    AC-4: If status=MERGED, includes merged_into_id (and optionally target skill name for UX).
    """

    id: uuid.UUID
    slug: str
    name_tr: str
    name_en: str | None = None
    category: str
    status: str
    merged_into_id: uuid.UUID | None = None
    merged_into_slug: str | None = None
    merged_into_name_tr: str | None = None

    model_config = {"from_attributes": True}


class SkillSearchResponse(BaseModel):
    """
    AC-1, AC-3: Skill search response shape.

    Fields:
        items: List of matching skills (empty list if no matches)
        total: Total count of matches
    """

    items: list[SkillResponse] = Field(default_factory=list)
    total: int
