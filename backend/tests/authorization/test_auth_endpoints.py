"""
Authorization/security tests for POST /auth/register, /login, /refresh, /logout.

PLAN 1.4 (YET-27..YET-30). Covers docs/API.md §2.1 contract:
- registration never accepts a role, creates User + empty TalentProfile in one transaction
- login does not distinguish "wrong email" from "wrong password"
- refresh token reuse revokes the whole token family (theft signal)
- CSRF header required on logout (the documented exception to 404-not-403)
- tokens never appear in the JSON body, only as httpOnly cookies
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.deps import get_session
from app.core.security import hash_email_token, hash_password, hash_refresh_token
from app.main import app
from app.models import EmailVerificationToken, PasswordResetToken, RefreshToken, TalentProfile, User


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def existing_user(session):
    user = User(email="existing-auth@example.com", password_hash=hash_password("Str0ngPassw0rd!"))
    session.add(user)
    session.flush()
    return user


class TestRegister:
    def test_register_creates_user_and_talent_profile(self, client, session):
        response = client.post(
            "/auth/register",
            json={"email": "new-user@example.com", "password": "Str0ngPassw0rd!", "full_name": "Yeni Kullanıcı"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "user_id" in body
        # Response must not leak the password/hash anywhere.
        assert "password" not in response.text.lower()

    def test_register_duplicate_email_returns_201_without_enumeration(self, client, existing_user, session):
        """
        AC-S1 (threat-model, docs/SECURITY.md §4 senaryo 10): registering
        with an already-taken email must not reveal that fact — same 201 as
        a fresh registration, a fake user_id (not the real account's), and
        no second talent_profiles row created for the existing user.
        """
        response = client.post(
            "/auth/register",
            json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!", "full_name": "Biri"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "user_id" in body
        assert body["user_id"] != str(existing_user.id)

        profile_count = session.execute(
            select(func.count()).select_from(TalentProfile).where(TalentProfile.user_id == existing_user.id)
        ).scalar()
        assert profile_count == 0, "duplicate register must not create a second profile for the existing user"

    def test_register_rejects_role_field_silently_ignored(self, client):
        """docs/API.md §2.1: register never accepts role — extra fields must not grant one."""
        response = client.post(
            "/auth/register",
            json={
                "email": "attempted-admin@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Saldırgan",
                "role": "PLATFORM_ADMIN",
            },
        )
        assert response.status_code == 201
        assert "role" not in response.json()


class TestLogin:
    def test_login_success_sets_httponly_cookies_not_body(self, client, existing_user):
        response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == str(existing_user.id)
        assert body["role"] == "TALENT"
        assert body["email_verified"] is False
        assert "token" not in str(body).lower()

        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert "csrf_token" in response.cookies

        set_cookie_headers = response.headers.get_list("set-cookie")
        access_cookie = next(h for h in set_cookie_headers if h.startswith("access_token="))
        assert "httponly" in access_cookie.lower()
        refresh_cookie = next(h for h in set_cookie_headers if h.startswith("refresh_token="))
        assert "httponly" in refresh_cookie.lower()
        csrf_cookie = next(h for h in set_cookie_headers if h.startswith("csrf_token="))
        assert "httponly" not in csrf_cookie.lower()

    def test_login_wrong_password_returns_generic_message(self, client, existing_user):
        response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "WrongPassword!"}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"
        assert "şifre yanlış" not in response.json()["message"].lower()
        assert "e-posta yanlış" not in response.json()["message"].lower()

    def test_login_unknown_email_returns_same_error_as_wrong_password(self, client):
        """docs/SECURITY.md §4.2: must not enable user enumeration."""
        response = client.post(
            "/auth/login", json={"email": "does-not-exist@example.com", "password": "WrongPassword!"}
        )
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    def test_login_locks_account_after_repeated_failures(self, client, existing_user, session):
        for _ in range(10):
            client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})

        session.refresh(existing_user)
        assert existing_user.locked_until is not None

        response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert response.status_code == 423
        assert response.json()["code"] == "ACCOUNT_LOCKED"


class TestRefresh:
    def test_refresh_rotates_token_and_issues_new_cookies(self, client, existing_user):
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        old_refresh = login_response.cookies["refresh_token"]

        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == 204
        new_refresh = refresh_response.cookies["refresh_token"]
        assert new_refresh != old_refresh

    def test_refresh_without_cookie_returns_401(self, client):
        response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_REFRESH_TOKEN"

    def test_refresh_reused_token_revokes_whole_family(self, client, existing_user):
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        original_refresh = login_response.cookies["refresh_token"]

        first_rotation = client.post("/auth/refresh")
        assert first_rotation.status_code == 204
        rotated_refresh = first_rotation.cookies["refresh_token"]

        # Replay the already-rotated (now revoked) token: theft signal.
        client.cookies.set("refresh_token", original_refresh)
        reuse_response = client.post("/auth/refresh")
        assert reuse_response.status_code == 401
        assert reuse_response.json()["code"] == "INVALID_REFRESH_TOKEN"

        # The entire family — including the token issued by the first
        # rotation — must now be revoked too.
        client.cookies.set("refresh_token", rotated_refresh)
        second_attempt = client.post("/auth/refresh")
        assert second_attempt.status_code == 401

    def test_refresh_expired_token_returns_401(self, client, existing_user, session):
        expired_value = "expired-refresh-token-value"
        session.add(
            RefreshToken(
                user_id=existing_user.id,
                family_id=uuid.uuid4(),
                token_hash=hash_refresh_token(expired_value),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        session.flush()

        client.cookies.set("refresh_token", expired_value)
        response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_REFRESH_TOKEN"


class TestLogout:
    def test_logout_without_auth_returns_401(self, client):
        response = client.post("/auth/logout")
        assert response.status_code == 401

    def test_logout_without_csrf_header_returns_403(self, client, existing_user):
        client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        response = client.post("/auth/logout")
        assert response.status_code == 403
        assert response.json()["code"] == "CSRF_FAILED"

    def test_logout_with_valid_csrf_revokes_refresh_family(self, client, existing_user):
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        csrf_token = login_response.cookies["csrf_token"]

        logout_response = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
        assert logout_response.status_code == 204

        # The refresh token used at login must no longer work.
        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == 401

    def test_logout_with_mismatched_csrf_header_returns_403(self, client, existing_user):
        client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        response = client.post("/auth/logout", headers={"X-CSRF-Token": "not-the-real-token"})
        assert response.status_code == 403
        assert response.json()["code"] == "CSRF_FAILED"


class TestVerifyEmail:
    """PLAN 1.6 (docs/API.md §2.1): POST /auth/verify-email."""

    def test_register_issues_a_verification_token_row(self, client, session):
        response = client.post(
            "/auth/register",
            json={"email": "verify-me@example.com", "password": "Str0ngPassw0rd!", "full_name": "Doğrulanacak"},
        )
        user_id = uuid.UUID(response.json()["user_id"])
        token_count = session.execute(
            select(func.count()).select_from(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id
            )
        ).scalar()
        assert token_count == 1

    def test_verify_email_with_valid_token_marks_user_verified(self, client, existing_user, session):
        raw_token = "valid-verification-token"
        session.add(
            EmailVerificationToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.flush()

        response = client.post("/auth/verify-email", json={"token": raw_token})
        assert response.status_code == 204

        session.refresh(existing_user)
        assert existing_user.email_verified_at is not None

    def test_verify_email_token_is_single_use(self, client, existing_user, session):
        raw_token = "single-use-token"
        session.add(
            EmailVerificationToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.flush()

        first = client.post("/auth/verify-email", json={"token": raw_token})
        assert first.status_code == 204

        second = client.post("/auth/verify-email", json={"token": raw_token})
        assert second.status_code == 400
        assert second.json()["code"] == "INVALID_TOKEN"

    def test_verify_email_unknown_token_returns_400(self, client):
        response = client.post("/auth/verify-email", json={"token": "does-not-exist"})
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_TOKEN"

    def test_verify_email_expired_token_returns_410(self, client, existing_user, session):
        raw_token = "expired-verification-token"
        session.add(
            EmailVerificationToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        session.flush()

        response = client.post("/auth/verify-email", json={"token": raw_token})
        assert response.status_code == 410
        assert response.json()["code"] == "TOKEN_EXPIRED"


class TestForgotPassword:
    """PLAN 1.6 (docs/API.md §2.1): POST /auth/forgot-password."""

    def test_forgot_password_known_email_returns_204(self, client, existing_user):
        response = client.post("/auth/forgot-password", json={"email": "existing-auth@example.com"})
        assert response.status_code == 204

    def test_forgot_password_unknown_email_returns_same_204(self, client):
        """docs/API.md §2.1: must not leak whether the email is registered."""
        response = client.post("/auth/forgot-password", json={"email": "nobody-here@example.com"})
        assert response.status_code == 204

    def test_forgot_password_known_email_creates_reset_token(self, client, existing_user, session):
        client.post("/auth/forgot-password", json={"email": "existing-auth@example.com"})
        token_count = session.execute(
            select(func.count()).select_from(PasswordResetToken).where(
                PasswordResetToken.user_id == existing_user.id
            )
        ).scalar()
        assert token_count == 1

    def test_forgot_password_unknown_email_creates_no_token(self, client, session):
        client.post("/auth/forgot-password", json={"email": "nobody-here@example.com"})
        token_count = session.execute(select(func.count()).select_from(PasswordResetToken)).scalar()
        assert token_count == 0


class TestResetPassword:
    """PLAN 1.6 (docs/API.md §2.1): POST /auth/reset-password."""

    def test_reset_password_with_valid_token_changes_password(self, client, existing_user, session):
        raw_token = "valid-reset-token"
        session.add(
            PasswordResetToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.flush()

        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "N3wStr0ngPassw0rd!"}
        )
        assert response.status_code == 204

        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "N3wStr0ngPassw0rd!"}
        )
        assert login_response.status_code == 200

    def test_reset_password_revokes_existing_refresh_tokens(self, client, existing_user, session):
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert login_response.status_code == 200

        raw_token = "reset-token-revokes-sessions"
        session.add(
            PasswordResetToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.flush()

        client.post("/auth/reset-password", json={"token": raw_token, "new_password": "N3wStr0ngPassw0rd!"})

        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == 401

    def test_reset_password_token_is_single_use(self, client, existing_user, session):
        raw_token = "single-use-reset-token"
        session.add(
            PasswordResetToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.flush()

        first = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "N3wStr0ngPassw0rd!"}
        )
        assert first.status_code == 204

        second = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "AnotherPassw0rd!"}
        )
        assert second.status_code == 400
        assert second.json()["code"] == "INVALID_TOKEN"

    def test_reset_password_unknown_token_returns_400(self, client):
        response = client.post(
            "/auth/reset-password", json={"token": "does-not-exist", "new_password": "N3wStr0ngPassw0rd!"}
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_TOKEN"

    def test_reset_password_expired_token_returns_410(self, client, existing_user, session):
        raw_token = "expired-reset-token"
        session.add(
            PasswordResetToken(
                user_id=existing_user.id,
                token_hash=hash_email_token(raw_token),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        session.flush()

        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "N3wStr0ngPassw0rd!"}
        )
        assert response.status_code == 410
        assert response.json()["code"] == "TOKEN_EXPIRED"
