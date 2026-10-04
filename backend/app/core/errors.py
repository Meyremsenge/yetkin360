"""
Shared HTTP error shape per docs/API.md §1.4: {code, message, request_id}.

One request-scoped id is minted per request (RequestIdMiddleware), echoed in the
X-Request-ID header, placed in every error body and written to the server log, so a
user-reported id can be matched with a log line. The inbound X-Request-ID header is
never trusted (log injection / id spoofing).
"""

import logging
import re
import traceback
from collections.abc import Mapping
from typing import Any, cast

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from uuid6 import uuid7

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

_SNAKE_CODE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")

_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}

_MESSAGE_BY_STATUS = {
    400: "Geçersiz istek.",
    401: "Kimlik doğrulaması gerekli.",
    403: "Bu işlem için yetkiniz yok.",
    404: "Kaynak bulunamadı.",
    405: "Bu yöntem desteklenmiyor.",
    409: "İşlem mevcut durumla çakışıyor.",
    422: "Girdi doğrulanamadı.",
    429: "Çok fazla istek yapıldı. Lütfen daha sonra tekrar deneyin.",
}

INTERNAL_ERROR_MESSAGE = "Beklenmeyen bir hata oluştu."
VALIDATION_MESSAGE = "Girdi doğrulanamadı."
_LOC_PREFIXES = {"body", "query", "path", "header", "cookie"}


class ApiError(HTTPException):
    """request_id is filled by the exception handler with the request-scoped id."""

    def __init__(
        self, status_code: int, code: str, message: str, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "request_id": None},
            headers=headers,
        )


class RequestIdMiddleware:
    """Pure ASGI (no BaseHTTPMiddleware): mints the id, exposes it on request.state and the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid7())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [h for h in message.get("headers", []) if h[0].lower() != b"x-request-id"]
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)


def get_request_id(request: Request) -> str:
    request_id = request.scope.get("state", {}).get("request_id")
    return request_id if isinstance(request_id, str) else str(uuid7())


def _route_template(request: Request) -> str:
    """Route template only: concrete paths may carry tokens or ids (no PII in logs)."""
    route = request.scope.get("route")
    return getattr(route, "path", "-")


def _error_response(
    request: Request,
    status_code: int,
    content: dict[str, Any],
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    content = {**content, "request_id": request_id}
    out_headers = dict(headers or {})
    out_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(status_code=status_code, content=jsonable_encoder(content), headers=out_headers)


def _generic_code(status_code: int) -> str:
    if status_code in _CODE_BY_STATUS:
        return _CODE_BY_STATUS[status_code]
    return "INTERNAL_ERROR" if status_code >= 500 else "BAD_REQUEST"


def _generic_message(status_code: int) -> str:
    if status_code in _MESSAGE_BY_STATUS:
        return _MESSAGE_BY_STATUS[status_code]
    return INTERNAL_ERROR_MESSAGE if status_code >= 500 else "İstek işlenemedi."


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast(StarletteHTTPException, exc)
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("code"), str):
        content = dict(detail)
    elif isinstance(detail, str) and _SNAKE_CODE.match(detail):
        content = {"code": detail, "message": _generic_message(exc.status_code)}
    else:
        content = {"code": _generic_code(exc.status_code), "message": _generic_message(exc.status_code)}
    content.setdefault("message", _generic_message(exc.status_code))
    response = _error_response(request, exc.status_code, content, exc.headers)
    level = logging.WARNING if exc.status_code >= 500 else logging.INFO
    logger.log(
        level,
        "http_error request_id=%s status=%s code=%s method=%s route=%s",
        get_request_id(request),
        exc.status_code,
        content["code"],
        request.method,
        _route_template(request),
    )
    return response


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = list(loc[1:] if loc and loc[0] in _LOC_PREFIXES else loc)
    return ".".join(str(p) for p in parts) or "_"


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    exc = cast(RequestValidationError, exc)
    fields: dict[str, str] = {}
    for error in exc.errors():
        fields.setdefault(_field_name(tuple(error["loc"])), str(error["msg"]))
    logger.info(
        "validation_error request_id=%s method=%s route=%s fields=%s",
        get_request_id(request),
        request.method,
        _route_template(request),
        ",".join(fields),
    )
    return _error_response(
        request, 422, {"code": "VALIDATION_ERROR", "message": VALIDATION_MESSAGE, "fields": fields}
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Frames and exception type only: the exception text can carry SQL parameters or
    e-mail addresses (same rule as the outbox worker's error log).
    """
    request_id = get_request_id(request)
    frames = "".join(traceback.format_tb(exc.__traceback__))
    logger.error(
        "unhandled_exception request_id=%s type=%s method=%s route=%s\n%s",
        request_id,
        type(exc).__name__,
        request.method,
        _route_template(request),
        frames,
    )
    return _error_response(request, 500, {"code": "INTERNAL_ERROR", "message": INTERNAL_ERROR_MESSAGE})
