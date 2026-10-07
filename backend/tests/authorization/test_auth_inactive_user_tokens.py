"""
YET-227 (L-03) regression: a SUSPENDED or DELETED user must not obtain tokens
from POST /auth/login or POST /auth/refresh.

The fix itself landed in c83c8b9 (authenticate() / refresh_tokens() status
checks). test_auth_endpoints.py only covers SUSPENDED and never asserts that
no cookie / refresh_tokens row was issued; DELETED had no coverage at all.
This file pins both statuses on both endpoints.
"""

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models import RefreshToken, User

PASSWORD = "Str0ngPassw0rd!"
INACTIVE_STATUSES = ["SUSPENDED", "DELETED"]
TOKEN_COOKIES = ("access_token", "refresh_token")


@pytest.fixture
def user(session):
    row = User(email="inactive-tokens@example.com", password_hash=hash_password(PASSWORD))
    session.add(row)
    session.flush()
    return row


def _refresh_token_count(session, user_id) -> int:
    return session.execute(
        select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user_id)
    ).scalar_one()


def _error_body(response) -> dict:
    body = dict(response.json())
    body.pop("request_id", None)
    return body


@pytest.mark.parametrize("status", INACTIVE_STATUSES)
def test_login_with_correct_password_issues_no_token(client, session, user, status):
    user.status = status
    session.flush()

    response = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    for name in TOKEN_COOKIES:
        assert name not in response.cookies
    assert "set-cookie" not in response.headers
    assert _refresh_token_count(session, user.id) == 0


@pytest.mark.parametrize("status", INACTIVE_STATUSES)
def test_login_inactive_response_equals_wrong_password_response(client, session, user, status):
    """No account-status oracle: same body as a wrong password (request_id excluded)."""
    wrong = client.post("/auth/login", json={"email": user.email, "password": "WrongPassword!"})

    user.status = status
    session.flush()
    inactive = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})

    assert inactive.status_code == wrong.status_code == 401
    assert _error_body(inactive) == _error_body(wrong)


@pytest.mark.parametrize("status", INACTIVE_STATUSES)
def test_refresh_after_status_change_issues_no_new_token(client, session, user, status):
    login = client.post("/auth/login", json={"email": user.email, "password": PASSWORD})
    assert login.status_code == 200
    assert _refresh_token_count(session, user.id) == 1

    user.status = status
    session.flush()

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_REFRESH_TOKEN"
    for name in TOKEN_COOKIES:
        assert name not in response.cookies
    assert _refresh_token_count(session, user.id) == 1, "no rotated refresh token may be created"
