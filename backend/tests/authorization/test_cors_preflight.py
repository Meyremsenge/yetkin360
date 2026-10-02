"""CORS preflight policy (YET-233 / L-11): explicit methods/headers, no wildcard
while credentials are enabled."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

ORIGIN = settings.allowed_origins.split(",")[0]
EVIL_ORIGIN = "https://evil.example"


@pytest.fixture(scope="module")
def cors_client() -> TestClient:
    return TestClient(app)


def _preflight(client: TestClient, *, method: str, headers: str, origin: str = ORIGIN):
    return client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_allowed_method_and_headers_pass_preflight(cors_client, method):
    response = _preflight(cors_client, method=method, headers="Content-Type, X-CSRF-Token")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.parametrize("method", ["PUT", "TRACE", "CONNECT"])
def test_unlisted_method_is_rejected_in_preflight(cors_client, method):
    response = _preflight(cors_client, method=method, headers="Content-Type")

    assert response.status_code == 400
    assert "Disallowed CORS method" in response.text


@pytest.mark.parametrize("header", ["X-Evil", "Authorization", "X-Forwarded-Host"])
def test_unlisted_header_is_rejected_in_preflight(cors_client, header):
    response = _preflight(cors_client, method="POST", headers=header)

    assert response.status_code == 400
    assert "Disallowed CORS headers" in response.text


def test_preflight_response_has_no_wildcard(cors_client):
    response = _preflight(cors_client, method="POST", headers="Content-Type, X-CSRF-Token")

    for name in (
        "access-control-allow-origin",
        "access-control-allow-methods",
        "access-control-allow-headers",
    ):
        assert "*" not in response.headers[name], name
    allowed_methods = {m.strip() for m in response.headers["access-control-allow-methods"].split(",")}
    assert allowed_methods == {"GET", "POST", "PATCH", "DELETE"}
    allowed_headers = {h.strip().lower() for h in response.headers["access-control-allow-headers"].split(",")}
    assert {"content-type", "x-csrf-token"} <= allowed_headers
    assert "authorization" not in allowed_headers


def test_disallowed_origin_gets_no_cors_grant(cors_client):
    response = _preflight(cors_client, method="POST", headers="Content-Type", origin=EVIL_ORIGIN)

    assert "access-control-allow-origin" not in response.headers
    assert response.status_code == 400
