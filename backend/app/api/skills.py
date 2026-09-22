"""
Skill search endpoint (GET /skills/search?q=...).

AC-1 through AC-11: Skill taxonomy search with validation, auth, and error handling.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_principal, get_session
from app.services.authorization import Principal
from app.services.skill import search_skills
from app.schemas.skill import SkillSearchResponse
from app.core.errors import ApiError

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/search", response_model=SkillSearchResponse)
def search(
    q: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> SkillSearchResponse:
    """
    AC-1 through AC-11: Search skill taxonomy.

    GET /skills/search?q=python&limit=20&offset=0

    Query Parameters:
        q (required): Search query (min 2 chars, max 200 chars)
        limit (optional): Max results to return (default 20, max 100)
        offset (optional): Pagination offset (default 0)

    Returns:
        200: SkillSearchResponse {"items": [...], "total": N}
            - AC-1: Results sorted alphabetically by name_tr
            - AC-3: Empty results return {"items": [], "total": 0}
            - AC-4: MERGED skills include merged_into_id; DEPRECATED excluded
        400: Validation error (q too short/long, limit > 100, invalid offset)
        401: Unauthenticated (no valid token/principal)
        500: Database error (generic message, no details leaked)

    Acceptance Criteria:
        - AC-1: Happy path — 200 + sorted results
        - AC-2: q min_length=2, validated manually
        - AC-3: No matches → 200 + empty list (not 404)
        - AC-4: MERGED included with merged_into_id; DEPRECATED excluded
        - AC-5: No token → 401 (get_current_principal enforces this)
        - AC-9 (AC-S1): ILIKE wildcard safe (parametrized query)
        - AC-10 (AC-S2): DB errors → 500 with generic message
        - AC-11 (AC-S3): q > 200 or limit > 100 → 400 (manual validation)
    """
    # Manual validation of q parameter
    # AC-2: q is required, min_length=2
    if q is None:
        raise ApiError(400, "VALIDATION_ERROR", "Arama sorgusu (q) gereklidir.")
    if len(q) < 2:
        raise ApiError(400, "VALIDATION_ERROR", "Arama sorgusu en az 2 karakter uzunluğunda olmalıdır.")
    # AC-11 (AC-S3): q > 200
    if len(q) > 200:
        raise ApiError(400, "VALIDATION_ERROR", "Arama sorgusu en fazla 200 karakter uzunluğunda olmalıdır.")

    # Manual validation of limit parameter
    # AC-11 (AC-S3): limit defaults to 20, max 100
    if limit is None:
        limit = 20
    else:
        # Attempt to convert to int if it came as string (shouldn't happen with FastAPI, but defensive)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            raise ApiError(400, "VALIDATION_ERROR", "Limit sayısal bir değer olmalıdır.")
        if limit < 1:
            raise ApiError(400, "VALIDATION_ERROR", "Limit en az 1 olmalıdır.")
        if limit > 100:
            raise ApiError(400, "VALIDATION_ERROR", "Limit en fazla 100 olmalıdır.")

    # Manual validation of offset parameter
    # AC-11: offset defaults to 0, must be >= 0
    if offset is None:
        offset = 0
    else:
        try:
            offset = int(offset)
        except (ValueError, TypeError):
            raise ApiError(400, "VALIDATION_ERROR", "Offset sayısal bir değer olmalıdır.")
        if offset < 0:
            raise ApiError(400, "VALIDATION_ERROR", "Offset negatif olamaz.")

    try:
        # AC-9 (AC-S1): Call service which uses parametrized ilike() query
        # Principal is authenticated (get_current_principal ensures 401 if not)
        response = search_skills(
            session=session,
            principal=principal,
            q=q,
            limit=limit,
            offset=offset,
        )
        return response

    except Exception as exc:
        # AC-10 (AC-S2): Catch DB errors and return generic 500
        # Don't leak SQLAlchemy exception types, query details, or stack trace
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Skill search error: {exc}", exc_info=True)

        raise ApiError(
            500,
            "INTERNAL_SERVER_ERROR",
            "İç sunucu hatası. Lütfen daha sonra tekrar deneyin.",
        )
