"""
POST /auth/register, /auth/login, /auth/refresh, /auth/logout.

docs/API.md §1.7 and §2.1: tokens never appear in the response body — they
travel as httpOnly + Secure + SameSite=Lax cookies. Write methods require a
matching X-CSRF-Token header (double-submit), except register/login which
issue the CSRF cookie for the first time and therefore cannot be expected to
already carry it.
"""

import ipaddress

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_session, require_csrf
from app.core.errors import ApiError
from app.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_ACCESS_TOKEN_MAX_AGE = 15 * 60
_REFRESH_TOKEN_MAX_AGE = 30 * 24 * 60 * 60

# The refresh cookie must reach both /auth/refresh and /auth/logout (the latter
# revokes the token family), so its Path is /auth. Sessions issued before
# YET-185 carry the old, narrower path; it is deleted wherever the cookie is
# set or cleared so the two copies never coexist.
_REFRESH_COOKIE_PATH = "/auth"
_LEGACY_REFRESH_COOKIE_PATH = "/auth/refresh"


def _client_ip(request: Request) -> str | None:
    """audit_events.actor_ip is INET — reject anything that isn't a real address."""
    if request.client is None:
        return None
    try:
        ipaddress.ip_address(request.client.host)
    except ValueError:
        return None
    return request.client.host


def _set_auth_cookies(response: Response, tokens: auth_service.IssuedTokens) -> None:
    response.set_cookie(
        "access_token",
        tokens.access_token,
        max_age=_ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        tokens.refresh_token,
        max_age=_REFRESH_TOKEN_MAX_AGE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
    )
    response.delete_cookie("refresh_token", path=_LEGACY_REFRESH_COOKIE_PATH)
    response.set_cookie(
        "csrf_token",
        tokens.csrf_token,
        max_age=_REFRESH_TOKEN_MAX_AGE,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=_REFRESH_COOKIE_PATH)
    response.delete_cookie("refresh_token", path=_LEGACY_REFRESH_COOKIE_PATH)
    response.delete_cookie("csrf_token", path="/")


@router.post("/register", status_code=201, response_model=RegisterResponse)
def register(body: RegisterRequest, session: Session = Depends(get_session)) -> RegisterResponse:
    # docs/SECURITY.md §4 senaryo 10: always 201, never leaks whether the
    # email was already registered (see register_user's docstring).
    result = auth_service.register_user(session, body.email, body.password, body.full_name)
    return RegisterResponse(user_id=result.user_id)


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    try:
        result = auth_service.authenticate(session, body.email, body.password, _client_ip(request))
    except auth_service.AccountLocked:
        raise ApiError(423, "ACCOUNT_LOCKED", "Hesap geçici olarak kilitlendi.")
    except auth_service.InvalidCredentials:
        raise ApiError(401, "INVALID_CREDENTIALS", "E-posta veya şifre hatalı.")

    _set_auth_cookies(response, result.tokens)
    return LoginResponse(user_id=result.tokens.user_id, role=result.role, email_verified=result.email_verified)


@router.post("/refresh", status_code=204)
def refresh(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    refresh_token_value = request.cookies.get("refresh_token")
    if refresh_token_value is None:
        raise ApiError(401, "INVALID_REFRESH_TOKEN", "Oturum yenilenemedi.")

    try:
        tokens = auth_service.refresh_tokens(session, refresh_token_value, _client_ip(request))
    except auth_service.InvalidRefreshToken:
        _clear_auth_cookies(response)
        raise ApiError(401, "INVALID_REFRESH_TOKEN", "Oturum yenilenemedi.")

    _set_auth_cookies(response, tokens)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    # get_current_user (401) runs as a dependency before this body executes;
    # require_csrf is called explicitly here, after it, so 401 UNAUTHENTICATED
    # always takes priority over 403 CSRF_FAILED.
    require_csrf(request)
    refresh_token_value = request.cookies.get("refresh_token")
    auth_service.logout(
        session,
        refresh_token_value,
        current_user.id,
        _client_ip(request),
    )
    _clear_auth_cookies(response)


@router.post("/resend-verification", status_code=204)
def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    # Same ordering as /auth/logout: get_current_user (401) first, then CSRF (403).
    # Always 204: already-verified and rate-limited calls are silent no-ops
    # (see auth_service.resend_email_verification).
    require_csrf(request)
    auth_service.resend_email_verification(session, current_user.id, _client_ip(request))


@router.post("/verify-email", status_code=204)
def verify_email(body: VerifyEmailRequest, session: Session = Depends(get_session)) -> None:
    try:
        auth_service.verify_email(session, body.token)
    except auth_service.InvalidEmailToken:
        raise ApiError(400, "INVALID_TOKEN", "Doğrulama bağlantısı geçersiz.")
    except auth_service.EmailTokenExpired:
        raise ApiError(410, "TOKEN_EXPIRED", "Doğrulama bağlantısının süresi dolmuş.")


@router.post("/forgot-password", status_code=204)
def forgot_password(body: ForgotPasswordRequest, session: Session = Depends(get_session)) -> None:
    # docs/API.md §2.1: always 204, whether or not the email is registered
    # (enumeration guard — same principle as /auth/register).
    auth_service.request_password_reset(session, body.email)


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetPasswordRequest, session: Session = Depends(get_session)) -> None:
    try:
        auth_service.reset_password(session, body.token, body.new_password)
    except auth_service.InvalidEmailToken:
        raise ApiError(400, "INVALID_TOKEN", "Bağlantı geçersiz.")
    except auth_service.EmailTokenExpired:
        raise ApiError(410, "TOKEN_EXPIRED", "Bağlantının süresi dolmuş.")
