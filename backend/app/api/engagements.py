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
    InvalidSkillError as EngInvalidSkillError,
    create_engagement,
    transition_engagement,
    create_engagement_task,
    create_deliverable,
)
from app.services.evaluation import (
    EngagementNotFoundError as EvalEngagementNotFoundError,
    IllegalTransitionError as EvalIllegalTransitionError,
    TransitionForbiddenError as EvalTransitionForbiddenError,
    DuplicateEvaluationError,
    InvalidSkillError as EvalInvalidSkillError,
    create_evaluation,
)
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationResponse,
    EvaluationItemResponse,
)

router = APIRouter(prefix="/engagements", tags=["engagements"])
attestations_router = APIRouter(prefix="/attestations", tags=["attestations"])


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
    skill_id: str | None = Field(None, description="Optional UUID of skill for SkillSignal generation")

    class Config:
        from_attributes = True


class PostTaskResponse(BaseModel):
    """Response schema for POST /engagements/{id}/tasks (201)."""

    id: str
    engagement_id: str
    skill_id: str | None = None
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
    skill_id: str | None = Field(None, description="Optional UUID of skill for SkillSignal generation")

    class Config:
        from_attributes = True


class PostDeliverableResponse(BaseModel):
    """Response schema for POST /engagements/{id}/deliverables (201)."""

    id: str
    engagement_id: str
    skill_id: str | None = None
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
            skill_id=payload.skill_id,
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
    except EngInvalidSkillError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Geçersiz skill_id.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostTaskResponse(
        id=str(task.id),
        engagement_id=str(task.engagement_id),
        skill_id=str(task.skill_id) if task.skill_id else None,
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
            skill_id=payload.skill_id,
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
    except EngInvalidSkillError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Geçersiz skill_id.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return PostDeliverableResponse(
        id=str(deliverable.id),
        engagement_id=str(deliverable.engagement_id),
        skill_id=str(deliverable.skill_id) if deliverable.skill_id else None,
        title=deliverable.title,
        description=deliverable.description,
        submitted_by_user_id=str(deliverable.submitted_by_user_id),
        submitted_at=deliverable.submitted_at,
        created_at=deliverable.created_at,
        updated_at=deliverable.updated_at,
    )


# ============================================================================
# PLAN 2.7: POST /engagements/{id}/evaluation (Evaluation Form Submission)
# ============================================================================


@router.post("/{engagement_id}/evaluation", response_model=EvaluationResponse, status_code=201)
def post_engagement_evaluation(
    engagement_id: str,
    payload: EvaluationCreate,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> EvaluationResponse:
    """
    PLAN 2.7 (YET-69, YET-86, YET-87): Submit a structured evaluation form on an engagement.

    Implements AC-1 through AC-9, AC-S1 through AC-S3.

    Returns:
        201 + evaluation object (private_note NEVER included in response).

    Errors:
        - 404 NOT_FOUND: Engagement not found or not accessible
        - 403 FORBIDDEN: Principal authorized but not allowed to evaluate (direction/role mismatch, AC-S3)
        - 409 CONFLICT: Engagement not in PENDING_EVALUATION, or duplicate evaluation (UNIQUE violation)
        - 422 UNPROCESSABLE_ENTITY: Invalid items[], criterion missing/empty, invalid skill_id, etc.
        - 401: Unauthenticated

    Security:
        - AC-S1: private_note NEVER appears in response JSON
        - AC-S2: evaluator_user_id always from principal (never from request body)
        - AC-S3: direction must match principal's role (TALENT→TALENT_TO_ORG only, ORG_MEMBER→ORG_TO_TALENT only)
        - AC-5: Scope check (out-of-scope → 404, in-scope but wrong role → 403)
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
        # Build items list from request (convert skill_id UUID to string for service layer)
        items = []
        for item in payload.items:
            items.append({
                "criterion": item.criterion,
                "skill_id": str(item.skill_id) if item.skill_id else None,
                "rating": item.rating,
                "comment": item.comment,
            })

        evaluation = create_evaluation(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            direction=payload.direction,
            items=items,
            private_note=payload.private_note,
        )
    except EvalEngagementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Engagement bulunamadı.",
                "request_id": None,
            },
        )
    except EvalIllegalTransitionError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONFLICT",
                "message": "Engagement bu durumda değerlendirilemiyor.",
                "request_id": None,
            },
        )
    except EvalTransitionForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu yönde değerlendirme yapma yetkiniz yok.",
                "request_id": None,
            },
        )
    except DuplicateEvaluationError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONFLICT",
                "message": "Bu yönde zaten değerlendirme gönderilmiş.",
                "request_id": None,
            },
        )
    except EvalInvalidSkillError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_REQUEST",
                "message": "Geçersiz skill_id.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    # Build response (query evaluation items from DB to ensure fresh data)
    # Refresh to get related items
    session.refresh(evaluation)

    # Load evaluation_items relationship
    evaluation_items_response = []
    for db_item in evaluation.evaluation_items:
        evaluation_items_response.append(
            EvaluationItemResponse(
                id=str(db_item.id),
                criterion=db_item.criterion,
                skill_id=str(db_item.skill_id) if db_item.skill_id else None,
                rating=db_item.rating,
                comment=db_item.comment,
            )
        )

    return EvaluationResponse(
        id=str(evaluation.id),
        engagement_id=str(evaluation.engagement_id),
        direction=evaluation.direction,
        items=evaluation_items_response,
        submitted_at=evaluation.submitted_at,
        # CRITICAL: private_note is NOT included in response
    )


# ============================================================================
# Attestation Route (PLAN 2.8 — YET-70)
# ============================================================================


class AttestationCreateRequest(BaseModel):
    """Request schema for POST /engagements/{id}/attestations."""

    claim_type: Literal["PARTICIPATION", "CONTRIBUTION", "COMPETENCE", "CONDUCT"] = Field(
        ..., description="Requested claim type"
    )
    version: int = Field(..., description="Current engagement version (optimistic locking)")
    skill_id: str | None = Field(None, description="Optional UUID of skill for SkillSignal creation")

    class Config:
        from_attributes = True
        extra = "forbid"  # Reject unknown fields (AC-S4: no tampering with downgrade logic)


class AttestationResponse(BaseModel):
    """Response schema for POST /engagements/{id}/attestations (201)."""

    id: str
    claim_type: str
    requested_claim_type: str
    downgrade_reasons: list[str]

    class Config:
        from_attributes = True


@router.post("/{engagement_id}/attestations", response_model=AttestationResponse, status_code=201)
def post_engagement_attestation(
    engagement_id: str,
    payload: AttestationCreateRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> AttestationResponse:
    """
    PLAN 2.8 (YET-70, YET-88, YET-89, YET-90): Submit attestation (tanıklık) on EVALUATED engagement.

    Implements T8 transition (EVALUATED → VERIFIED) with COMPETENCE precondition checking (DOMAIN.md §3.11).
    Triggers single transaction: Attestation + VerifiedExperience + SkillSignal + AuditEvent + Outbox + Engagement.status update.

    AC-1 through AC-9, AC-S1 through AC-S5.

    Returns:
        201 + Attestation object (claim_type after downgrade logic, downgrade_reasons list)

    Errors:
        - 404 NOT_FOUND: Engagement not found or not accessible
        - 403 FORBIDDEN: Principal (TALENT) cannot attest (S6 exception)
        - 409 CONFLICT: Engagement not EVALUATED, version mismatch, already attested, self-attestation
        - 422 UNPROCESSABLE_ENTITY: Invalid claim_type or request body
        - 401 UNAUTHORIZED: Unauthenticated

    Security:
        - AC-S1: claim_type from request, downgrade_reasons computed server-side (no request-body tampering)
        - AC-S2: Engagement fetched via scoped_engagements() (cross-tenant 404)
        - AC-S3: Self-attestation check (attestor_user_id != talent_id)
        - AC-S4: Pydantic extra="forbid" rejects unknown fields
        - AC-S5: DB-level optimistic locking prevents race conditions
    """
    from app.services.attestation import (
        EngagementNotFoundError as AttEngagementNotFoundError,
        IllegalTransitionError as AttIllegalTransitionError,
        TransitionForbiddenError as AttTransitionForbiddenError,
        SelfAttestationError,
        AttestationAlreadyExistsError,
        VersionMismatchError,
        create_attestation,
    )

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
        attestation, verified_exp = create_attestation(
            session=session,
            principal=principal,
            engagement_id=engagement_id,
            requested_claim_type=payload.claim_type,
            version=payload.version,
            skill_id=payload.skill_id,
        )
    except AttEngagementNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Engagement bulunamadı veya erişilemez.",
                "request_id": None,
            },
        )
    except AttTransitionForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu işlem için yetkiniz yok.",
                "request_id": None,
            },
        )
    except AttIllegalTransitionError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": "Engagement bu durumda tanıklanmak için uygun değildir.",
                "request_id": None,
            },
        )
    except VersionMismatchError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CONFLICT",
                "message": "Sürüm uyumsuzluğu (eşzamanlı güncelleme).",
                "request_id": None,
            },
        )
    except SelfAttestationError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SELF_ATTESTATION_FORBIDDEN",
                "message": "Kendi deneyiminize tanıklık yapamazsınız.",
                "request_id": None,
            },
        )
    except AttestationAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ATTESTATION_ALREADY_EXISTS",
                "message": "Bu engagement için zaten tanıklık gönderilmiş.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    return AttestationResponse(
        id=str(attestation.id),
        claim_type=attestation.claim_type,
        requested_claim_type=attestation.requested_claim_type,
        downgrade_reasons=attestation.downgrade_reasons if attestation.downgrade_reasons else [],
    )


# ============================================================================
# Attestation Revoke Route (PLAN 2.10 — YET-72)
# ============================================================================


class RevokeAttestationRequest(BaseModel):
    """Request schema for POST /attestations/{id}/revoke."""

    revoke_reason: str = Field(..., min_length=1, description="Reason for revoking attestation")

    class Config:
        from_attributes = True


class RevokeAttestationResponse(BaseModel):
    """Response schema for POST /attestations/{id}/revoke (200)."""

    id: str
    revoked_at: datetime
    revoke_reason: str

    class Config:
        from_attributes = True


@attestations_router.post("/{attestation_id}/revoke", response_model=RevokeAttestationResponse, status_code=200)
def revoke_attestation_endpoint(
    attestation_id: str,
    payload: RevokeAttestationRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> RevokeAttestationResponse:
    """
    PLAN 2.10 (YET-72): Revoke an attestation (set revoked_at and revoke_reason).

    Implements AC-1 through AC-8, AC-S1 through AC-S3.
    Single transaction: Attestation update + tombstone SkillSignal + superseded_by_id update + AuditEvent.

    Returns:
        200 + Attestation object (with revoked_at and revoke_reason)

    Errors:
        - 404 NOT_FOUND: Attestation not found or not accessible
        - 403 FORBIDDEN: Principal is not the attestor
        - 409 ALREADY_REVOKED: Attestation already revoked
        - 422 UNPROCESSABLE_ENTITY: Missing/empty revoke_reason
        - 401 UNAUTHORIZED: Unauthenticated

    Security:
        - AC-2: Only attestor can revoke → 403 if not attestor
        - AC-3: Scope check (out-of-scope → 404)
        - AC-S1: revoke_reason METNİ audit metadata'ya yazılmaz
        - AC-S2: Race condition handled via UPDATE WHERE revoked_at IS NULL
        - AC-S3: DB trigger prevents other field updates
    """
    from app.services.attestation import (
        AttestationNotFoundError,
        RevokeForbiddenError,
        AttestationAlreadyRevokedError,
        revoke_attestation,
    )

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
        attestation = revoke_attestation(
            session=session,
            principal=principal,
            attestation_id=attestation_id,
            revoke_reason=payload.revoke_reason,
        )
    except AttestationNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": "Attestation bulunamadı.",
                "request_id": None,
            },
        )
    except RevokeForbiddenError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": "Bu tanıklığı sadece yapan kişi geri çekebilir.",
                "request_id": None,
            },
        )
    except AttestationAlreadyRevokedError:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ALREADY_REVOKED",
                "message": "Bu tanıklık zaten geri çekilmiş.",
                "request_id": None,
            },
        )

    # Commit transaction
    session.commit()

    assert attestation.revoked_at is not None
    assert attestation.revoke_reason is not None
    return RevokeAttestationResponse(
        id=str(attestation.id),
        revoked_at=attestation.revoked_at,
        revoke_reason=attestation.revoke_reason,
    )
