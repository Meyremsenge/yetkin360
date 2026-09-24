"""
Evaluation request/response schemas (Pydantic DTOs).

PLAN 2.7 (YET-69, YET-86, YET-87): Evaluation form submission + response.

Critical rule: EvaluationResponse MUST NOT include private_note field (PII protection).
This ensures talent cannot access org's private evaluation notes even in GET context.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class EvaluationItemCreate(BaseModel):
    """
    Request schema for a single evaluation criterion.

    Fields:
        criterion: Criterion/yetkinlik tanımı (required, min_length=1).
        skill_id: Optional UUID of related skill.
        rating: Rating value (BELOW/MEETS/EXCEEDS/NOT_OBSERVED).
        comment: Optional comment (not required even for NOT_OBSERVED).
    """

    criterion: str = Field(min_length=1, description="Criterion/yetkinlik tanımı")
    skill_id: uuid.UUID | None = Field(None, description="Optional skill UUID")
    rating: Literal["BELOW", "MEETS", "EXCEEDS", "NOT_OBSERVED"] = Field(
        description="Rating value"
    )
    comment: str | None = Field(None, description="Optional comment")


class EvaluationItemResponse(BaseModel):
    """
    Response schema for evaluation_items (no private_note).

    Fields:
        id: UUIDv7 of evaluation_item.
        criterion: Criterion text.
        skill_id: Optional skill UUID.
        rating: Rating value.
        comment: Optional comment.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="UUIDv7")
    criterion: str
    skill_id: str | None = None
    rating: str
    comment: str | None = None


class EvaluationCreate(BaseModel):
    """
    Request schema for POST /engagements/{id}/evaluation.

    Fields:
        direction: ORG_TO_TALENT or TALENT_TO_ORG.
        items: List of evaluation criteria (min_length=1, all-or-nothing).
        private_note: Optional private note (stored but never returned in response).

    Note:
        - evaluator_user_id NOT in request — always from principal.
        - submitted_at NOT in request — always set to utcnow().
    """

    model_config = ConfigDict(from_attributes=True)

    direction: Literal["ORG_TO_TALENT", "TALENT_TO_ORG"] = Field(
        description="Evaluation direction"
    )
    items: list[EvaluationItemCreate] = Field(
        min_length=1, description="At least 1 evaluation item required"
    )
    private_note: str | None = Field(None, description="Optional private note (org/admin only)")


class EvaluationResponse(BaseModel):
    """
    Response schema for evaluation submission (201) and future GET endpoints.

    CRITICAL: private_note field is EXPLICITLY OMITTED — not in __fields__, not returned.
    This prevents PII leakage even if schema is misused or future GET endpoint forgets to filter.

    Fields:
        id: UUIDv7.
        engagement_id: Related engagement UUID.
        direction: ORG_TO_TALENT or TALENT_TO_ORG.
        items: List of evaluation_items (without private_note).
        submitted_at: ISO 8601 timestamp (UTC).
        (private_note is NEVER included)
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="UUIDv7")
    engagement_id: str
    direction: str
    items: list[EvaluationItemResponse]
    submitted_at: datetime
