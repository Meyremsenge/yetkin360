from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.certificate_checks import router as certificate_checks_router
from app.api.engagements import router as engagements_router, attestations_router
from app.api.evidence import router as evidence_router
from app.api.institution_link_requests import router as institution_link_requests_router
from app.api.institutions import router as institutions_router
from app.api.me import router as me_router
from app.api.organizations import router as organizations_router
from app.api.public import router as public_router
from app.api.skills import router as skills_router
from app.api.skill_signals import router as skill_signals_router, signals_alias_router
from app.api.talent_skills import router as talent_skills_router
from app.api.verified_experiences import router as verified_experiences_router
from app.core.config import settings
from app.core.errors import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

# Explicit lists: a wildcard is incompatible with credentials and widens the
# surface needlessly. Methods mirror the routes in app/api; headers are the
# ones the frontend sends (client.ts) — CSRF name must match core/deps.py.
CORS_ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE"]
CORS_ALLOWED_HEADERS = ["Content-Type", "X-CSRF-Token"]


def create_app(environment: str) -> FastAPI:
    # YET-212: the interactive docs and the schema describe every route; they are
    # development tools, not a production surface.
    docs_enabled = environment != "production"
    application = FastAPI(
        title="Yetkin360 API",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Added last = outermost, so every response (CORS preflight included) carries the id.
    application.add_middleware(RequestIdMiddleware)

    application.include_router(admin_router)
    application.include_router(auth_router)
    application.include_router(certificate_checks_router)
    application.include_router(engagements_router)
    application.include_router(attestations_router)
    application.include_router(evidence_router)
    application.include_router(institution_link_requests_router)
    application.include_router(institutions_router)
    application.include_router(me_router)
    application.include_router(organizations_router)
    application.include_router(public_router)
    application.include_router(skills_router)
    application.include_router(skill_signals_router)
    application.include_router(signals_alias_router)
    application.include_router(talent_skills_router)
    application.include_router(verified_experiences_router)

    # docs/API.md §1.4: every error body is {code, message, request_id} — flat, not
    # FastAPI's default {"detail": ...}. Starlette's base class also covers unknown
    # routes (404) and wrong methods (405), which FastAPI's HTTPException does not.
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app(settings.environment)
