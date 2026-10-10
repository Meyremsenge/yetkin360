"""Admin read-only endpoints: audit log (A1) and reviewed fraud-flag history (F2).

Same gate as app/api/admin.py (`require_platform_admin`, non-admin -> 404).
Both endpoints are read-only; audit_events is append-only and never modified here.

A2 note: these endpoints write no audit rows, so no actor IP is needed here. The
`actor_ip` returned to the admin comes from rows written by auth endpoints
(app/api/auth.py::_client_ip).
"""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.admin import MAX_PAGE_SIZE, require_platform_admin
from app.api.deps import get_session
from app.services.audit import list_audit_events
from app.services.fraud_flag import list_fraud_history
from app.services.fraud_signals import subject_labels

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_platform_admin)])

# Metadata is returned through an allow-list: only short, controlled-vocabulary scalar keys.
# Business/identity values that older rows may carry (name, legal_id, domain, title, ...) are dropped.
_SAFE_METADATA_KEYS = frozenset(
    {
        "verification_level",
        "outcome",
        "slug",
        "category",
        "merged_into_id",
        "note_length",
        "reason",
        "role",
        "via",
        "status",
        "decision",
        "direction",
        "scan_status",
        "from",
        "to",
        "from_status",
        "to_status",
        "from_level",
        "to_level",
        "kind",
        "claim_type",
    }
)
_MAX_SAFE_VALUE_LENGTH = 100


def _safe_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in _SAFE_METADATA_KEYS:
            continue
        if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
            safe[key] = value
        elif isinstance(value, str) and len(value) <= _MAX_SAFE_VALUE_LENGTH:
            safe[key] = value
    return safe


class AuditEventItem(BaseModel):
    id: int
    actor_user_id: Optional[uuid.UUID]
    actor_ip: Optional[str]
    action: str
    subject_type: str
    subject_id: Optional[uuid.UUID]
    result: str
    metadata: dict[str, Any]
    created_at: datetime


class AuditEventsResponse(BaseModel):
    items: list[AuditEventItem]
    limit: int
    offset: int
    has_more: bool


class FraudHistoryItem(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    subject_label: Optional[str] = None
    signal: Optional[str] = None
    reason: str
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    model: str
    status: Literal["CONFIRMED", "DISMISSED"]
    created_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by_user_id: Optional[uuid.UUID]


class FraudHistoryResponse(BaseModel):
    items: list[FraudHistoryItem]
    limit: int
    offset: int
    has_more: bool


@router.get("/audit-events", response_model=AuditEventsResponse)
def get_audit_events(
    action: Optional[str] = Query(None, min_length=1, max_length=100),
    subject_type: Optional[str] = Query(None, min_length=1, max_length=50),
    actor_user_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> AuditEventsResponse:
    """A1: newest-first audit log. Actor is exposed as an id only (never an e-mail)."""
    rows = list_audit_events(
        session,
        action=action,
        subject_type=subject_type,
        actor_user_id=actor_user_id,
        limit=limit,
        offset=offset,
    )
    has_more = len(rows) > limit
    items = [
        AuditEventItem(
            id=row.id,
            actor_user_id=row.actor_user_id,
            actor_ip=str(row.actor_ip) if row.actor_ip is not None else None,
            action=row.action,
            subject_type=row.subject_type,
            subject_id=row.subject_id,
            result=row.result,
            metadata=_safe_metadata(row.event_metadata),
            created_at=row.created_at,
        )
        for row in rows[:limit]
    ]
    return AuditEventsResponse(items=items, limit=limit, offset=offset, has_more=has_more)


@router.get("/fraud-flags/history", response_model=FraudHistoryResponse)
def get_fraud_history(
    status: Optional[Literal["CONFIRMED", "DISMISSED"]] = Query(None),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> FraudHistoryResponse:
    """F2: reviewed (CONFIRMED/DISMISSED) fraud flags, most recently reviewed first."""
    rows = list_fraud_history(session, status=status, limit=limit, offset=offset)
    has_more = len(rows) > limit
    page = rows[:limit]
    labels = subject_labels(session, page)
    items = [
        FraudHistoryItem(
            id=f.id,
            subject_type=f.subject_type,
            subject_id=f.subject_id,
            subject_label=labels.get(f.id),
            signal=f.signal,
            reason=f.reason,
            confidence=f.confidence,  # type: ignore[arg-type]
            model=f.model,
            status=f.status,  # type: ignore[arg-type]
            created_at=f.created_at,
            reviewed_at=f.reviewed_at,
            reviewed_by_user_id=f.reviewed_by_user_id,
        )
        for f in page
    ]
    return FraudHistoryResponse(items=items, limit=limit, offset=offset, has_more=has_more)
