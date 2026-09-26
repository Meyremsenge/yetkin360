"""
Reminder schemas (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu).

Implements request/response DTOs for POST /institutions/{id}/reminders.
"""

import uuid
from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    """Request schema for POST /institutions/{id}/reminders."""

    engagement_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="At least one engagement ID required"
    )
    template: str = Field(..., min_length=1, description="Template name (e.g., 'evaluation_pending')")


class ReminderResponse(BaseModel):
    """Response schema for POST /institutions/{id}/reminders."""

    queued_count: int = Field(..., ge=0, description="Number of engagements queued for reminder")
