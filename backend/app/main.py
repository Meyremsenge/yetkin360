from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.engagements import router as engagements_router
from app.api.evidence import router as evidence_router
from app.api.institutions import router as institutions_router
from app.api.me import router as me_router
from app.api.organizations import router as organizations_router
from app.api.skills import router as skills_router
from app.api.talent_skills import router as talent_skills_router
from app.core.config import settings

app = FastAPI(title="Yetkin360 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(engagements_router)
app.include_router(evidence_router)
app.include_router(institutions_router)
app.include_router(me_router)
app.include_router(organizations_router)
app.include_router(skills_router)
app.include_router(talent_skills_router)


@app.exception_handler(HTTPException)
async def api_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    docs/API.md §1.4: every error body is {code, message, request_id} —
    flat, not FastAPI's default {"detail": ...} wrapper.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail), "request_id": None},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors (422) with standard error format.
    Convert Pydantic's error list to a single error message.
    """
    # Build a simple message from first error
    if exc.errors():
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"][1:])  # Skip "body"
        msg = first_error["msg"]
        error_message = f"{field}: {msg}" if field else msg
    else:
        error_message = "Validasyon hatası"

    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": error_message,
            "request_id": None,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
