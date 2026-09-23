"""Engagement endpoints (POST /engagements)."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.engagement import (
    InstitutionMismatchError,
    OrganizationNotFoundError,
    TalentNotFoundError,
    EngagementNotFoundError,
    IllegalTransitionError,
    PreconditionFailedError,
    TransitionForbiddenError,
    VersionConflictError,
    create_engagement,
    transition_engagement,
    create_engagement_task,
    create_deliverable,
)

router = APIRouter(prefix="/engagements", tags=["engagements"])


# ============================================================================
# Pydantic Schemas (Request/Response DTOs)
# ============================================================================


class PostEngagementRequest(BaseModel):
    """Request schema for POST /engagements."""

    talent_id: str = Field(..., description="UUID of talent")
    organization_id: str = Field(..., description="UUID of organization")
    kind: Literal["INTERNSHIP", "CAPSTONE", "SHORT_PROJECT", "PART_TIME"] = Field(..., description="Engagement kind")
    title: str = Field(..., min_length=1, description="Engagement title")
    institution_id: str | None = Field(None, description="Optional UUID of institution")
    confidential: bool = Field(False, description="Whether engagement is confidential")

    class Config:
        from_attributes = True


class PostEngagementResponse(BaseModel):
    """Response schema for POST /engagements (201) and transitions (200)."""

    id: str
    talent_id: str
    organization_id: str
    institution_id: str | None
    kind: str
    title: str
    status: str
    version: int
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransitionEngagementRequest(BaseModel):
    """Request schema for POST /engagements/{id}/transitions."""

    to_status: str = Field(..., description="Target status")
    version: int = Field(..., description="Current version for optimistic locking")
    reason: str | None = Field(None, description="Optional reason for REJECTED/CANCELLED transitions")

    class Config:
        from_attributes = True


class PostTaskRequest(BaseModel):
    """Request schema for POST /engagements/{id}/tasks."""

    title: str = Field(..., min_length=1, description="Task title")
    description: str | None = Field(None, description="Optional task description")
    due_at: datetime | None = Field(None, description="Optional due date")

    class Config:
        from_attributes = True


class PostTaskResponse(BaseModel):
    """Response schema for POST /engagements/{id}/tasks (201)."""

    id: str
    engagement_id: str
    title: str
    description: str | None = None
    status: str
    due_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostDeliverableRequest(BaseModel):
    """Request schema for POST /engagements/{id}/deliverables."""

    title: str = Field(..., min_length=1, description="Deliverable title")
    description: str | None = Field(None, description="Optional deliverable description")

    class Config:
        from_attributes = True


class PostDeliverableResponse(BaseModel):
    """Response schema for POST /engagements/{id}/deliverables (201)."""

    id: str
    engagement_id: str
    title: str
    description: str | None = None
    submitted_by_user_id: str
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AC-1: POST /engagements
# ============================================================================


@router.post("", response_model=PostEngagementResponse, status_code=201)
def post_engagements(
    payload: PostEngagementRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PostEngagementResponse:
    """
    AC-1: Create a new engagement (internship/capstone/project/part-time work).

    Returns:
        201 + {id, talent_id, organization_id, institution_id, kind, title, status, version, created_at}

    Errors:
        - 404 TALENT_NOT_FOUND: talent does not exist or not accessible to principal
        - 404 ORGANIZATION_NOT_FOUND: organization does not exist or not accessible
        - 400 INSTITUTION_MISMATCH: institution_id doesn't match talent's institution
        - 422: validation error (invalid kind, empty title, etc.)
        - 401: unauthenticated

    Security:
        - AC-S1: TALENT can only create for own talent_id (403→404)
        - AC-S2: ORG_MEMBER can only create for their organizations (403→404)
        - AC-S3: Institution mismatch error message is generic
        - AC-S4: confidential title not logged
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Kimlik doğrulama gerekli.",
                "request_id": None,
            },
        )

    try:
        engagement = create_engagement(
            session=session,
            principal=principal,
            talent_id=payload.talent_id,
            organization_id=payload.organization_id,
            kind=payload.kind,
            title=payload.title,
            institution_id=payload.institution_id,
            confidential=payload.confidential,
        )
    except TalentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "TALENT_NOT_FOUND",
                "message": "Talent bulunamadı.",
                "request_id": None,
            },
        )
    except OrganizationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organizasyon bulunamadı.",
                "request_id": None,
            },
        )
    except InstitutionMismatchError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INSTITUTION_MISMATCH",
                "message": "institution_id does not match talent's institution",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostEngagementResponse(
        id=str(engagement.id),
        talent_id=str(engagement.talent_id),
        organization_id=str(engagement.organization_id),
        institution_id=str(engagement.institution_id) if engagement.institution_id else None,
        kind=engagement.kind,
        title=engagement.title,
        status=engagement.status,
        version=engagement.version,
        reason=engagement.reason,
        created_at=engagement.created_at,
        updated_at=engagement.updated_at,
    )


# ============================================================================
# PLAN 2.2: POST /engagements/{id}/transitions (Engagement state machine)
# ============================================================================


@router.post("/{engagement_id}/transitions", response_model=PostEngagementResponse)
def post_engagement_transitions(
    engagement_id: str,
    payload: TransitionEngagementRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PostEngagementResponse:
    """
    PLAN 2.2: Transition engagement status (state machine: DRAFT→PENDING_APPROVAL→ACTIVE→CANCELLED, etc.).

    Implements AC-1 through AC-14, AC-S1 through AC-S4 (ATDD-driven).

    Valid transitions (4):
    - T1: DRAFT → PENDING_APPROVAL (TALENT/ORG_MEMBER/ORG_ADMIN, requires institution_id)
    - T2: PENDING_APPROVAL → ACTIVE (COORDINATOR/INST_ADMIN)
    - T3: PENDING_APPROVAL → REJECTED (COORDINATOR/INST_ADMIN, requires reason)
    - T6: ACTIVE → CANCELLED (ORG_ADMIN/COORDINATOR, requires reason)

    Returns:
        200 + {id, status, version, ...} (same schema as POST /engagements)

    Errors:
        - 404 NOT_FOUND: Engagement not found or not accessible
        - 403 FORBIDDEN: Principal authorized to access but not for this transition
        - 422 ILLEGAL_TRANSITION: Transition not in table
        - 422 PRECONDITION_FAILED: Preconditions not met (institution_id NULL, reason missing)
        - 409 CONFLICT: Optimistic locking failure (version mismatch)
        - 401: Unauthenticated

    Security:
        - AC-S2: Tenant isolation (403→404 for out-of-scope engagements)
        - AC-S3: TALENT cannot do T2 (FORBIDDEN)
        - AC-S4: Version tampering → 409 (durum makinesi atlatılamaz)
        - reason field NOT logged to audit/outbox (PII risk)
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Kimlik doğrulama gerekli.",
                "request_id": None,
            },
        )

    try:
        engagement = transition_engagement(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            to_status=payload.to_status,
            version=payload.version,
            reason=payload.reason,
        )
    except EngagementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Engagement bulunamadı.",
                "request_id": None,
            },
        )
    except IllegalTransitionError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ILLEGAL_TRANSITION",
                "message": f"Bu durumdan '{payload.to_status}' durumuna geçiş yapılamaz.",
                "request_id": None,
            },
        )
    except PreconditionFailedError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PRECONDITION_FAILED",
                "message": str(e),
                "request_id": None,
            },
        )
    except TransitionForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu geçişi yapma yetkiniz yok.",
                "request_id": None,
            },
        )
    except VersionConflictError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONFLICT",
                "message": "Kayıt başka tarafından değiştirilmiş. Lütfen yeniden yükleyin.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostEngagementResponse(
        id=str(engagement.id),
        talent_id=str(engagement.talent_id),
        organization_id=str(engagement.organization_id),
        institution_id=str(engagement.institution_id) if engagement.institution_id else None,
        kind=engagement.kind,
        title=engagement.title,
        status=engagement.status,
        version=engagement.version,
        reason=engagement.reason,
        created_at=engagement.created_at,
        updated_at=engagement.updated_at,
    )


# ============================================================================
# PLAN 2.4: POST /engagements/{id}/tasks (Engagement Task Creation)
# ============================================================================


@router.post("/{engagement_id}/tasks", response_model=PostTaskResponse, status_code=201)
def post_engagement_tasks(
    engagement_id: str,
    payload: PostTaskRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PostTaskResponse:
    """
    PLAN 2.4: Create a task within an engagement (AC-1).

    Returns:
        201 + {id, engagement_id, title, description, status="PLANNED", due_at, completed_at, created_at, updated_at}

    Errors:
        - 404 NOT_FOUND: Engagement not found or not accessible
        - 403 FORBIDDEN: Principal authorized but not allowed to create tasks (e.g., TALENT)
        - 422 PRECONDITION_FAILED: Engagement not ACTIVE
        - 401: Unauthenticated

    Security:
        - AC-S1: TALENT cannot create tasks (403 FORBIDDEN)
        - AC-S5: Scope check before validation (404 before 422)
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Kimlik doğrulama gerekli.",
                "request_id": None,
            },
        )

    try:
        task = create_engagement_task(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
        )
    except EngagementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Engagement bulunamadı.",
                "request_id": None,
            },
        )
    except PreconditionFailedError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PRECONDITION_FAILED",
                "message": str(e),
                "request_id": None,
            },
        )
    except TransitionForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu işlemi yapma yetkiniz yok.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostTaskResponse(
        id=str(task.id),
        engagement_id=str(task.engagement_id),
        title=task.title,
        description=task.description,
        status=task.status,
        due_at=task.due_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ============================================================================
# PLAN 2.4: POST /engagements/{id}/deliverables (Deliverable Submission)
# ============================================================================


@router.post("/{engagement_id}/deliverables", response_model=PostDeliverableResponse, status_code=201)
def post_engagement_deliverables(
    engagement_id: str,
    payload: PostDeliverableRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> PostDeliverableResponse:
    """
    PLAN 2.4: Submit a deliverable (evidence) on an engagement (AC-2).

    Returns:
        201 + {id, engagement_id, title, description, submitted_by_user_id, submitted_at, created_at, updated_at}

    Errors:
        - 404 NOT_FOUND: Engagement not found or not accessible
        - 403 FORBIDDEN: Principal authorized but not allowed to submit deliverables (e.g., ORG_MEMBER)
        - 422 PRECONDITION_FAILED: Engagement not ACTIVE
        - 401: Unauthenticated

    Security:
        - AC-S2: Only TALENT can submit deliverables (403 FORBIDDEN for ORG_MEMBER/ORG_ADMIN/COORDINATOR)
        - AC-S3: submitted_by_user_id always from principal.user_id (never from request body)
        - AC-S5: Scope check before validation (404 before 422)
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Kimlik doğrulama gerekli.",
                "request_id": None,
            },
        )

    try:
        deliverable = create_deliverable(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            title=payload.title,
            description=payload.description,
        )
    except EngagementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Engagement bulunamadı.",
                "request_id": None,
            },
        )
    except PreconditionFailedError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PRECONDITION_FAILED",
                "message": str(e),
                "request_id": None,
            },
        )
    except TransitionForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu işlemi yapma yetkiniz yok.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostDeliverableResponse(
        id=str(deliverable.id),
        engagement_id=str(deliverable.engagement_id),
        title=deliverable.title,
        description=deliverable.description,
        submitted_by_user_id=str(deliverable.submitted_by_user_id),
        submitted_at=deliverable.submitted_at,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at,
    )
