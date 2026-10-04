"""
YET-207 (ENT-07): production cookie/CSRF model.

Supported topology is a single origin behind a reverse proxy over HTTPS
(K6 = a). Two things are pinned here:
  1. Settings refuses to start in production with a configuration that would
     silently weaken the cookie/CSRF model (startup validator).
  2. The cookies themselves stay host-only (no Domain) with the documented
     Secure/HttpOnly/SameSite split, logout clears exactly what login wrote,
     and the double-submit contract is unchanged.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.deps import get_session
from app.core.security import hash_password
from app.main import app
from app.models import User
from tests._testdb import session_override

PASSWORD = "Str0ngPassw0rd!"

_SIGNING = "unit-test-signing-value"
_BASE = dict(
    database_url="postgresql://u:p@localhost/db_for_settings_unit_test",
    secret_key=_SIGNING,
    s3_endpoint_url="http://localhost:9000",
    s3_access_key="access",
    s3_secret_key="secret",
)

_GOOD_PROD = dict(
    environment="production",
    debug=False,
    cookie_secure=True,
    frontend_origin="https://yetkin360.example",
    allowed_origins="https://yetkin360.example",
)


def _settings(**overrides) -> Settings:
    # _env_file=None: a developer's real .env must not leak into the unit.
    return Settings(_env_file=None, **{**_BASE, **overrides})


def _reject(**overrides) -> str:
    with pytest.raises(ValidationError) as exc:
        _settings(**{**_GOOD_PROD, **overrides})
    return str(exc.value)


# --- AC-4 / AC-6: accepted configurations ---------------------------------


def test_valid_production_config_is_accepted():
    s = _settings(**_GOOD_PROD)
    assert s.environment == "production"
    assert s.cookie_secure is True


def test_development_local_defaults_still_start():
    s = _settings(environment="development", debug=True, cookie_secure=False)
    assert s.allowed_origins == "http://localhost:3000"


def test_staging_is_a_known_environment_and_not_forced():
    assert _settings(environment="staging", cookie_secure=False).environment == "staging"


# --- AC-1: Secure flag ------------------------------------------------------


def test_production_rejects_insecure_cookies():
    assert "COOKIE_SECURE" in _reject(cookie_secure=False)


# --- AC-2: origins ----------------------------------------------------------


@pytest.mark.parametrize(
    "origins",
    [
        "http://yetkin360.example",
        "https://yetkin360.example,http://other.example",
        "https://localhost:3000",
        "https://127.0.0.1",
        "https://[::1]:3000",
        "https://LOCALHOST",
    ],
)
def test_production_rejects_http_or_loopback_allowed_origins(origins):
    assert "ALLOWED_ORIGINS" in _reject(allowed_origins=origins)


@pytest.mark.parametrize("origin", ["http://yetkin360.example", "https://localhost:3000"])
def test_production_rejects_http_or_loopback_frontend_origin(origin):
    assert "FRONTEND_ORIGIN" in _reject(frontend_origin=origin)


def test_production_default_origins_are_rejected():
    with pytest.raises(ValidationError) as exc:
        _settings(environment="production", debug=False, cookie_secure=True)
    message = str(exc.value)
    assert "ALLOWED_ORIGINS" in message and "FRONTEND_ORIGIN" in message


# --- AC-3: debug ------------------------------------------------------------


def test_production_rejects_debug():
    assert "DEBUG" in _reject(debug=True)


# --- AC-5: environment name -------------------------------------------------


@pytest.mark.parametrize("name", ["prod", "Production", "production ", "", "live"])
def test_unknown_environment_name_is_rejected(name):
    with pytest.raises(ValidationError) as exc:
        _settings(environment=name)
    assert "ENVIRONMENT" in str(exc.value)


# --- AC-11: all problems in one message, no values leaked -------------------


def test_all_problems_reported_together_without_secret_values():
    with pytest.raises(ValidationError) as exc:
        _settings(
            environment="production",
            debug=True,
            cookie_secure=False,
            allowed_origins="http://x.example",
            frontend_origin="http://x.example",
        )
    message = str(exc.value)
    for name in ("COOKIE_SECURE", "DEBUG", "ALLOWED_ORIGINS", "FRONTEND_ORIGIN"):
        assert name in message
    assert _SIGNING not in message
    assert "db_for_settings_unit_test" not in message


# --- AC-7 / AC-8 / AC-9: real API, https host-only cookies ------------------


@pytest.fixture
def https_client(session):
    email = f"cookie207-{uuid.uuid4()}@example.com"
    session.add(User(email=email, password_hash=hash_password(PASSWORD)))
    session.flush()
    app.dependency_overrides[get_session] = session_override(session)
    old_secure = settings.cookie_secure
    settings.cookie_secure = True
    try:
        yield TestClient(app, base_url="https://app.example.com"), email
    finally:
        settings.cookie_secure = old_secure
        app.dependency_overrides.pop(get_session, None)


def _parse(set_cookie_headers):
    parsed = {}
    for raw in set_cookie_headers:
        parts = [p.strip() for p in raw.split(";")]
        name, _, value = parts[0].partition("=")
        attrs = {p.split("=", 1)[0].lower(): (p.split("=", 1)[1] if "=" in p else True) for p in parts[1:]}
        parsed.setdefault(name, []).append((value, attrs))
    return parsed


def _login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response


def test_login_cookies_are_host_only_secure_lax(https_client):
    client, email = https_client
    cookies = _parse(_login(client, email).headers.get_list("set-cookie"))

    written = {name: attrs for name, entries in cookies.items() for value, attrs in entries if value not in ("", "\"\"")}
    assert set(written) == {"access_token", "refresh_token", "csrf_token"}
    for name, attrs in written.items():
        assert "domain" not in attrs, name
        assert attrs.get("secure") is True, name
        assert str(attrs.get("samesite")).lower() == "lax", name
    assert written["access_token"]["httponly"] is True
    assert written["refresh_token"]["httponly"] is True
    assert "httponly" not in written["csrf_token"]  # JS must read it (double submit)
    assert written["access_token"]["path"] == "/"
    assert written["refresh_token"]["path"] == "/auth"
    assert written["csrf_token"]["path"] == "/"


def test_refresh_rewrites_cookies_without_domain(https_client):
    client, email = https_client
    _login(client, email)
    response = client.post("/auth/refresh")
    assert response.status_code == 204
    for raw in response.headers.get_list("set-cookie"):
        assert "domain=" not in raw.lower()


def test_logout_clears_exactly_the_paths_login_wrote(https_client):
    client, email = https_client
    login = _login(client, email)
    written = {(name, attrs["path"]) for name, entries in _parse(login.headers.get_list("set-cookie")).items()
               for value, attrs in entries if value not in ("", "\"\"")}

    response = client.post("/auth/logout", headers={"X-CSRF-Token": client.cookies.get("csrf_token", "")})
    assert response.status_code == 204
    cleared = {(name, attrs["path"]) for name, entries in _parse(response.headers.get_list("set-cookie")).items()
               for value, attrs in entries}
    assert written <= cleared
    assert ("refresh_token", "/auth/refresh") in cleared  # legacy path (YET-185)
    for raw in response.headers.get_list("set-cookie"):
        assert "domain=" not in raw.lower()


def test_double_submit_contract_unchanged(https_client):
    client, email = https_client
    _login(client, email)
    csrf = client.cookies.get("csrf_token")
    assert csrf

    missing = client.post("/auth/logout")
    assert missing.status_code == 403
    assert missing.json()["code"] == "CSRF_FAILED"

    wrong = client.post("/auth/logout", headers={"X-CSRF-Token": csrf + "x"})
    assert wrong.status_code == 403

    ok = client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 204


def test_unauthenticated_write_still_401_before_csrf():
    response = TestClient(app, base_url="https://app.example.com").post("/auth/logout")
    assert response.status_code == 401
