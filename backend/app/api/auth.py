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
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_ACCESS_TOKEN_MAX_AGE = 15 * 60
_REFRESH_TOKEN_MAX_AGE = 30 * 24 * 60 * 60


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
        path="/auth/refresh",
    )
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
    response.delete_cookie("refresh_token", path="/auth/refresh")
    response.delete_cookie("csrf_token", path="/")


@router.post("/register", status_code=201, response_model=RegisterResponse)
def register(body: RegisterRequest, session: Session = Depends(get_session)) -> RegisterResponse:
    try:
        result = auth_service.register_user(session, body.email, body.password, body.full_name)
    except auth_service.EmailAlreadyTaken:
        raise ApiError(409, "EMAIL_TAKEN", "Bu e-posta adresi zaten kayıtlı.")
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
