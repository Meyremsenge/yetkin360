"""
Reminder schemas (PLAN 3.4 — yet-108-toplu-hatirlatma-ucu).

Implements request/response DTOs for POST /institutions/{id}/reminders.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

# YET-213: the template becomes the outbox topic (reminder.<template>), so it is a
# closed set; a free-text value would let a caller mint arbitrary topics.
ReminderTemplate = Literal["evaluation_pending"]

# YET-213: upper bound on one request's fan-out (and on the audit metadata it writes).
MAX_ENGAGEMENT_IDS = 100


class ReminderCreate(BaseModel):
    """Request schema for POST /institutions/{id}/reminders."""

    engagement_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=MAX_ENGAGEMENT_IDS,
        description="1-100 engagement IDs",
    )
    template: ReminderTemplate = Field(..., description="Template name (e.g., 'evaluation_pending')")


class ReminderResponse(BaseModel):
    """Response schema for POST /institutions/{id}/reminders."""

    queued_count: int = Field(..., ge=0, description="Number of engagements queued for reminder")
