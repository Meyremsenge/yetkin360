"""
YET-212 (OPS-04): every error response is {code, message, request_id} (docs/API.md §1.4),
request_id matches the X-Request-ID header and the server log, and internals never leak.
"""

import logging
import re
import uuid

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import ApiError
from app.main import app, create_app

probe = APIRouter(prefix="/__contract__")
# Runtime value: it is not part of any source line a traceback frame could echo.
_LEAK_MARKER = "internal-" + uuid.uuid4().hex


class _Body(BaseModel):
    name: str
    count: int


@probe.get("/boom")
def _boom() -> None:
    raise RuntimeError(_LEAK_MARKER)


@probe.get("/snake")
def _snake() -> None:
    raise HTTPException(status_code=400, detail="FREE_EMAIL_DOMAIN")


@probe.get("/plain")
def _plain() -> None:
    raise HTTPException(status_code=404, detail="Institution not found")


@probe.get("/dict-no-id")
def _dict_no_id() -> None:
    raise HTTPException(
        status_code=409, detail={"code": "SOME_CONFLICT", "message": "Çakışma.", "request_id": None}
    )


@probe.get("/api-error")
def _api_error() -> None:
    raise ApiError(403, "CSRF_FAILED", "CSRF doğrulaması başarısız.")


@probe.get("/too-many")
def _too_many() -> None:
    raise HTTPException(status_code=429, detail="TOO_MANY_REQUESTS")


@probe.post("/body")
def _body(payload: _Body) -> None:
    return None


@pytest.fixture(scope="module")
def contract_client():
    app.include_router(probe)
    app.openapi_schema = None
    yield TestClient(app, raise_server_exceptions=False)
    app.router.routes[:] = [r for r in app.router.routes if not getattr(r, "path", "").startswith("/__contract__")]
    app.openapi_schema = None


def _assert_contract(resp, status: int, code: str) -> dict:
    assert resp.status_code == status
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert set(body) >= {"code", "message", "request_id"}
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert body["request_id"]
    uuid.UUID(body["request_id"])
    assert resp.headers["X-Request-ID"] == body["request_id"]
    assert "detail" not in body
    return body


def test_unknown_route_is_404_contract(contract_client):
    body = _assert_contract(contract_client.get("/yok-boyle-bir-yol"), 404, "NOT_FOUND")
    assert body["message"] == "Kaynak bulunamadı."


def test_wrong_method_is_405_contract_and_keeps_allow_header(contract_client):
    resp = contract_client.delete("/health")
    _assert_contract(resp, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in resp.headers["allow"]


def test_snake_case_string_detail_becomes_code(contract_client):
    body = _assert_contract(contract_client.get("/__contract__/snake"), 400, "FREE_EMAIL_DOMAIN")
    assert "FREE_EMAIL_DOMAIN" not in body["message"]


def test_plain_string_detail_gets_generic_turkish_message_not_http_error(contract_client):
    body = _assert_contract(contract_client.get("/__contract__/plain"), 404, "NOT_FOUND")
    assert "not found" not in body["message"].lower()


def test_string_429_is_rate_limited_contract(contract_client):
    _assert_contract(contract_client.get("/__contract__/too-many"), 429, "TOO_MANY_REQUESTS")


def test_dict_detail_with_null_request_id_is_filled(contract_client):
    body = _assert_contract(contract_client.get("/__contract__/dict-no-id"), 409, "SOME_CONFLICT")
    assert body["message"] == "Çakışma."


def test_api_error_keeps_code_and_message_and_uses_request_scoped_id(contract_client):
    body = _assert_contract(contract_client.get("/__contract__/api-error"), 403, "CSRF_FAILED")
    assert body["message"] == "CSRF doğrulaması başarısız."


def test_validation_error_has_fixed_message_and_fields(contract_client):
    resp = contract_client.post("/__contract__/body", json={"count": "x"})
    body = _assert_contract(resp, 422, "VALIDATION_ERROR")
    assert body["message"] == "Girdi doğrulanamadı."
    assert set(body["fields"]) == {"name", "count"}
    assert all(isinstance(v, str) and v for v in body["fields"].values())


def test_unhandled_exception_is_json_500_without_internals(contract_client, caplog):
    with caplog.at_level(logging.ERROR):
        resp = contract_client.get("/__contract__/boom")
    body = _assert_contract(resp, 500, "INTERNAL_ERROR")
    assert body["message"] == "Beklenmeyen bir hata oluştu."
    assert _LEAK_MARKER not in resp.text
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert body["request_id"] in logged
    assert "RuntimeError" in logged
    assert _LEAK_MARKER not in logged  # exception text may carry PII/SQL params


def test_request_ids_differ_per_request_and_inbound_header_is_ignored(contract_client):
    a = contract_client.get("/yok", headers={"X-Request-ID": "attacker-chosen"}).json()["request_id"]
    b = contract_client.get("/yok").json()["request_id"]
    assert a != b and a != "attacker-chosen"


def test_handled_error_is_logged_with_request_id_and_route_template_only(contract_client, caplog):
    with caplog.at_level(logging.INFO):
        resp = contract_client.get("/__contract__/plain")
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert resp.json()["request_id"] in logged


def test_unauthorized_resource_stays_404_not_403(contract_client):
    """Contract fix must not move the 404-not-403 rule: unknown ≡ out-of-scope shape."""
    a = contract_client.get(f"/engagements/{uuid.uuid4()}")
    assert a.status_code in (401, 404)
    assert a.json()["code"] != "FORBIDDEN"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_closed_in_production_open_in_development(path):
    prod = TestClient(create_app("production"), raise_server_exceptions=False)
    resp = prod.get(path)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"
    dev = TestClient(create_app("development"))
    assert dev.get(path).status_code == 200


def test_create_app_instances_share_error_contract():
    other: FastAPI = create_app("production")
    resp = TestClient(other, raise_server_exceptions=False).get("/nope")
    assert re.fullmatch(r"[0-9a-f-]{36}", resp.json()["request_id"])
