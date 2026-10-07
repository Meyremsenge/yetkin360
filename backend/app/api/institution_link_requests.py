"""Talent's own institution link request history (GET /talents/me/institution-link-requests)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.institution import list_my_link_requests

router = APIRouter(prefix="/talents/me/institution-link-requests", tags=["institution-link-requests"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class MyLinkRequestItem(BaseModel):
    """Single item in GET /talents/me/institution-link-requests response."""

    id: uuid.UUID
    institution_id: uuid.UUID
    institution_name: str
    status: str
    requested_at: datetime
    decided_at: datetime | None


class MyLinkRequestsListResponse(BaseModel):
    """Response schema for GET /talents/me/institution-link-requests."""

    items: list[MyLinkRequestItem]


# ============================================================================
# YET-197/IS-10: Talent's own link request history
# ============================================================================


@router.get("", status_code=200, response_model=MyLinkRequestsListResponse)
def list_my_link_requests_endpoint(
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> MyLinkRequestsListResponse:
    """
    YET-197/IS-10: Authenticated talent lists their own institution link requests,
    all statuses (PENDING/APPROVED/REJECTED), newest first.

    Args:
        principal: Authenticated principal
        session: Database session

    Returns:
        MyLinkRequestsListResponse (items: id, institution_id, institution_name,
        status, requested_at, decided_at)

    Status codes:
        200: List retrieved (possibly empty)
        401: Unauthenticated
        404: Caller has no talent profile
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Kimlik doğrulama gerekli.", "request_id": None},
        )

    if principal.talent_id is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TALENT_PROFILE_NOT_FOUND", "message": "Talent profili bulunamadı.", "request_id": None},
        )

    items = list_my_link_requests(session=session, principal=principal)
    return MyLinkRequestsListResponse(items=[MyLinkRequestItem(**item) for item in items])
