"""
YET-228 (L-04): auth cookie Max-Age must follow settings, not hard-coded values.

If the access/refresh TTL settings change, the cookie lifetimes have to move
with them — otherwise the browser drops a still-valid JWT early, or keeps a
dead one around.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.deps import get_session
from app.core.security import hash_password
from app.main import app
from app.models import User
from tests._testdb import session_override

_EMAIL = "cookie-max-age@example.com"
_PASSWORD = "Str0ngPassw0rd!"


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = session_override(session)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def user(session):
    u = User(email=_EMAIL, password_hash=hash_password(_PASSWORD))
    session.add(u)
    session.flush()
    return u


def _max_age(response, cookie_name: str) -> int:
    header = next(h for h in response.headers.get_list("set-cookie") if h.startswith(f"{cookie_name}="))
    match = re.search(r"Max-Age=(\d+)", header, re.IGNORECASE)
    assert match, f"{cookie_name} cookie has no Max-Age"
    return int(match.group(1))


def _login(client):
    response = client.post("/auth/login", json={"email": _EMAIL, "password": _PASSWORD})
    assert response.status_code == 200
    return response


def test_cookie_max_age_matches_default_settings(client, user):
    response = _login(client)
    assert _max_age(response, "access_token") == settings.access_token_ttl_minutes * 60
    assert _max_age(response, "refresh_token") == settings.refresh_token_ttl_days * 86400
    assert _max_age(response, "csrf_token") == settings.refresh_token_ttl_days * 86400


def test_cookie_max_age_follows_changed_settings(client, user, monkeypatch):
    monkeypatch.setattr(settings, "access_token_ttl_minutes", 7)
    monkeypatch.setattr(settings, "refresh_token_ttl_days", 3)

    response = _login(client)

    assert _max_age(response, "access_token") == 7 * 60
    assert _max_age(response, "refresh_token") == 3 * 86400
    assert _max_age(response, "csrf_token") == 3 * 86400
