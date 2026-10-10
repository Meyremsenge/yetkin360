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
from app.models import (
    AuditEvent,
    EmailVerificationToken,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    PasswordResetToken,
    RefreshToken,
    TalentProfile,
    User,
)
from tests._testdb import session_override


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = session_override(session)
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

    def test_register_account_kind_organization_creates_org_with_caller_as_admin(self, client, session):
        """docs/API.md §2.1 (revize): account_kind=ORGANIZATION → Organization + caller ADMIN'i, aynı transaction."""
        response = client.post(
            "/auth/register",
            json={
                "email": "org-founder@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Kuruluş Kurucusu",
                "account_kind": "ORGANIZATION",
                "entity_name": "Test Kuruluşu A.Ş.",
            },
        )
        assert response.status_code == 201
        user_id = uuid.UUID(response.json()["user_id"])

        org = session.execute(
            select(Organization).where(Organization.name == "Test Kuruluşu A.Ş.")
        ).scalars().first()
        assert org is not None
        assert org.verification_level == "T1"

        membership = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id, OrganizationMember.user_id == user_id
            )
        ).scalars().first()
        assert membership is not None
        assert membership.role == "ADMIN"

        # Still gets a talent profile — account_kind never removes that.
        profile = session.execute(
            select(TalentProfile).where(TalentProfile.user_id == user_id)
        ).scalars().first()
        assert profile is not None

    def test_register_account_kind_institution_creates_institution_with_caller_as_admin(self, client, session):
        response = client.post(
            "/auth/register",
            json={
                "email": "inst-founder@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Kurum Kurucusu",
                "account_kind": "INSTITUTION",
                "entity_name": "Test Üniversitesi",
            },
        )
        assert response.status_code == 201
        user_id = uuid.UUID(response.json()["user_id"])

        institution = session.execute(
            select(Institution).where(Institution.name == "Test Üniversitesi")
        ).scalars().first()
        assert institution is not None
        assert institution.verification_level == "T1"

        membership = session.execute(
            select(InstitutionMember).where(
                InstitutionMember.institution_id == institution.id, InstitutionMember.user_id == user_id
            )
        ).scalars().first()
        assert membership is not None
        assert membership.role == "ADMIN"

    def test_register_account_kind_organization_without_entity_name_returns_422(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "missing-name@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Biri",
                "account_kind": "ORGANIZATION",
            },
        )
        assert response.status_code == 422

    def test_register_default_account_kind_talent_creates_no_membership(self, client, session):
        """account_kind'ın hiç gönderilmemesi (mevcut davranış) hâlâ TALENT'e düşmeli — org/institution satırı açılmamalı."""
        response = client.post(
            "/auth/register",
            json={"email": "plain-talent@example.com", "password": "Str0ngPassw0rd!", "full_name": "Sade Kullanıcı"},
        )
        assert response.status_code == 201
        user_id = uuid.UUID(response.json()["user_id"])

        org_membership = session.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == user_id)
        ).scalars().first()
        inst_membership = session.execute(
            select(InstitutionMember).where(InstitutionMember.user_id == user_id)
        ).scalars().first()
        assert org_membership is None
        assert inst_membership is None

    def test_register_duplicate_email_with_account_kind_does_not_create_organization(
        self, client, existing_user, session
    ):
        """AC-S1 korunur: kayıtlı e-postayla account_kind=ORGANIZATION gönderilse bile yeni kuruluş açılmaz (fake user_id yolu)."""
        response = client.post(
            "/auth/register",
            json={
                "email": "existing-auth@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Saldırgan",
                "account_kind": "ORGANIZATION",
                "entity_name": "Saldırgan Şirketi",
            },
        )
        assert response.status_code == 201
        org = session.execute(
            select(Organization).where(Organization.name == "Saldırgan Şirketi")
        ).scalars().first()
        assert org is None


class TestLogin:
    @pytest.mark.unverified_users
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

    def test_login_tenth_failed_attempt_returns_401_and_sets_lock_until(self, client, existing_user, session):
        """
        AC-2 sınır durumu: 10. yanlış denemenin KENDİSİ 401 INVALID_CREDENTIALS döner
        (henüz kilitli değil), ama bu 10. denemeden sonra locked_until ~now+15dk olmalı.
        """
        # 9 yanlış deneme
        for _ in range(9):
            response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})
            assert response.status_code == 401
            assert response.json()["code"] == "INVALID_CREDENTIALS"

        # 10. deneme: kendisi de 401 döner
        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

        # locked_until şimdi set edilmiş olmalı
        session.refresh(existing_user)
        assert existing_user.locked_until is not None
        now = datetime.now(timezone.utc)
        assert existing_user.locked_until > now
        assert existing_user.locked_until <= now + timedelta(minutes=20)

    def test_login_after_lock_returns_423_with_account_locked(self, client, existing_user, session):
        """
        AC-2 devamı: kilit ayarlandıktan sonra (doğru parola bile) 11. deneme 423 döner.
        """
        # 10 yanlış deneme
        for _ in range(10):
            client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})

        # 11. deneme, doğru parola: 423 döner
        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        assert response.status_code == 423
        assert response.json()["code"] == "ACCOUNT_LOCKED"

    def test_login_wrong_password_logs_audit_denied(self, client, existing_user, session):
        """
        AC-3: yanlış parola denemesi sonrası audit_events'te USER_LOGIN/DENIED satırı
        gerçek session'da (savepoint ıvırında, flush görüntüsü) var.
        """
        before_count = session.execute(select(func.count()).select_from(AuditEvent)).scalar()

        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})
        assert response.status_code == 401

        session.flush()  # Ensure audit event is flushed to visible state
        after_count = session.execute(select(func.count()).select_from(AuditEvent)).scalar()
        assert after_count > before_count

        audit = session.execute(
            select(AuditEvent)
            .where(AuditEvent.action == "USER_LOGIN", AuditEvent.result == "DENIED")
            .order_by(AuditEvent.created_at.desc())
        ).scalars().first()
        assert audit is not None

    def test_login_locked_account_audit_contains_only_locked_reason(self, client, existing_user, session):
        """
        AC-S1 (güvenlik, threat-model): kilitli hesaba giriş denemesi audit'inde
        metadata = {"reason": "locked"} olmalı, email/password/hash hiçbiri YAZILMAMALI.
        """
        # Hesabı kitleyelim
        for _ in range(10):
            client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})

        session.flush()

        # Kilitli hesaba erişim deneyelim
        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        assert response.status_code == 423

        session.flush()

        # Son DENIED audit satırını bul
        audit = session.execute(
            select(AuditEvent)
            .where(AuditEvent.action == "USER_LOGIN", AuditEvent.result == "DENIED")
            .order_by(AuditEvent.id.desc())
        ).scalars().first()
        assert audit is not None
        assert audit.event_metadata == {"reason": "locked"}
        # email, password, hash vb. hiçbiri metadata'da olmamali
        if audit.event_metadata:
            for key in audit.event_metadata.keys():
                assert key not in ["email", "password", "password_hash", "tc_kimlik_no"]

    def test_login_expired_lock_with_correct_password_succeeds_and_resets_count(self, client, existing_user, session):
        """
        AC-4: locked_until geçmişte kalıntı bir zamana set edilirse, doğru parolayla giriş
        başarılı olmalı ve sayaç 0'a, locked_until NULL'a sıfırlanmalı.
        """
        # Sayacı yükselt
        for _ in range(10):
            client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})

        session.flush()
        session.refresh(existing_user)
        assert existing_user.locked_until is not None

        # Kilit süresini geçmişe ayarla
        existing_user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()

        # Doğru parolayla giriş yap
        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        assert response.status_code == 200

        session.refresh(existing_user)
        assert existing_user.failed_login_count == 0
        assert existing_user.locked_until is None

    def test_login_suspended_user_with_correct_password_returns_invalid_credentials(self, client, existing_user, session):
        """
        AC-5 (L-03): SUSPENDED kullanıcı doğru parolayla giriş denerse, 401 INVALID_CREDENTIALS
        döner (200 DEĞİL), ACTIVE kullanıcının yanlış-parola hatasıyla AYNI mesaj.
        """
        existing_user.status = "SUSPENDED"
        session.flush()

        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"})
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_CREDENTIALS"

    def test_login_suspended_vs_wrong_password_same_response_enumeration_protection(self, client, existing_user, session):
        """
        AC-S2 (güvenlik, threat-model, numaralandırma koruması): SUSPENDED kullanıcı + doğru
        parola vs. ACTIVE kullanıcı + yanlış parola iki tepkisinin HTTP status_code,
        error.code ve error.message alanları BİREBİR AYNI olmalı.
        """
        # SUSPENDED kullanıcı + doğru parola
        existing_user.status = "SUSPENDED"
        session.flush()

        response_suspended = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert response_suspended.status_code == 401

        # ACTIVE kullanıcı (yeni user) + yanlış parola
        active_user = User(email="active-user@example.com", password_hash=hash_password("Str0ngPassw0rd!"))
        session.add(active_user)
        session.flush()

        response_active = client.post(
            "/auth/login", json={"email": "active-user@example.com", "password": "WrongPassword"}
        )
        assert response_active.status_code == 401

        # İki tepki aynı olmalı
        assert response_suspended.status_code == response_active.status_code
        assert response_suspended.json()["code"] == response_active.json()["code"]
        assert response_suspended.json()["message"] == response_active.json()["message"]

    def test_login_expired_lock_with_wrong_password_resets_count_and_increments_by_one(
        self, client, existing_user, session
    ):
        """
        AC-8: kilit süresi dolmuş bir kullanıcı yanlış parolayla giriş denerse, sayac 0'a
        sıfırlanır (önce), sonra bu deneme +1 eklenir (sonuç: 1, 0 DEĞİL), locked_until NULL kalır.
        """
        # Sayacı yükselt + lock
        for _ in range(10):
            client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "wrong"})

        session.flush()
        session.refresh(existing_user)

        # Kilit süresini geçmişe ayarla
        existing_user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.flush()

        # Yanlış parolayla giriş yap
        response = client.post("/auth/login", json={"email": "existing-auth@example.com", "password": "WrongPassword"})
        assert response.status_code == 401

        session.refresh(existing_user)
        assert existing_user.failed_login_count == 1, "Should be reset to 0, then +1"
        assert existing_user.locked_until is None

    def test_login_refresh_token_denied_for_suspended_user(self, client, existing_user, session):
        """
        AC-7 (L-03): token sahibinin status'u ACTIVE/PENDING değilse refresh 401 döner.
        """
        # Giriş yap
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.cookies["refresh_token"]

        # Kullanıcıyı SUSPENDED yap
        existing_user.status = "SUSPENDED"
        session.flush()

        # Refresh token'ı kullan
        client.cookies.set("refresh_token", refresh_token)
        response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert response.json()["code"] == "INVALID_REFRESH_TOKEN"


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

    def test_refresh_reused_token_with_suspended_user_still_revokes_family(self, client, existing_user, session):
        """
        Bulgu 2 testi: SUSPENDED kullanıcı + zaten revoke edilmiş refresh token
        kombinasyonunda, REUSE_DETECTED mantığı (aile-çapında revoke + audit)
        çalışmmalı. AC-7 (L-03 status kontrolü) devreye girmeden ONCE REUSE
        tespiti çalışsın diye L-03 kontrol satırları revoked_at/expires_at
        kontrolünden SONRA taşındı.
        """
        # Giriş yap, refresh_token alın
        login_response = client.post(
            "/auth/login", json={"email": "existing-auth@example.com", "password": "Str0ngPassw0rd!"}
        )
        assert login_response.status_code == 200
        original_refresh = login_response.cookies["refresh_token"]

        # İlk rotasyon: orijinal token artık revoked_at dolu
        first_rotation = client.post("/auth/refresh")
        assert first_rotation.status_code == 204
        rotated_refresh = first_rotation.cookies["refresh_token"]

        # Kullanıcıyı SUSPENDED yap
        existing_user.status = "SUSPENDED"
        session.flush()

        # ESKİ (zaten revoke edilmiş) token'ı tekrar kullan: REUSE_DETECTED yoluna gitmeli
        client.cookies.set("refresh_token", original_refresh)
        reuse_response = client.post("/auth/refresh")
        assert reuse_response.status_code == 401
        assert reuse_response.json()["code"] == "INVALID_REFRESH_TOKEN"

        # REUSE_DETECTED audit satırının var olduğunu doğrula
        session.flush()
        audit = session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "REFRESH_TOKEN_REUSE_DETECTED",
                AuditEvent.result == "DENIED",
            )
            .order_by(AuditEvent.created_at.desc())
        ).scalars().first()
        assert audit is not None, "REUSE_DETECTED audit olmalı, SUSPENDED kontrol gelmeden evvel çalışmış olmalı"

        # YENİ rotasyondan gelen token'ın da artık revoke edilmiş olmasını doğrula
        # (aile-çapında revoke başarılı)
        client.cookies.set("refresh_token", rotated_refresh)
        second_attempt = client.post("/auth/refresh")
        assert second_attempt.status_code == 401


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


class TestRegisterOrganizationCorporateIdentity:
    """Kuruluş kaydı: doğrulama e-postası her zaman kurumsal adrese gider
    (ücretsiz sağlayıcı sunucuda reddedilir) ve MERSİS numarası kuruluşa yazılır."""

    @staticmethod
    def _payload(email: str, **overrides) -> dict:
        payload = {
            "email": email,
            "password": "Str0ngPassw0rd!",
            "full_name": "Kuruluş Yetkilisi",
            "account_kind": "ORGANIZATION",
            "entity_name": "Kurumsal Kimlik A.Ş.",
        }
        payload.update(overrides)
        return payload

    @pytest.mark.parametrize(
        "email", ["kurucu@gmail.com", "kurucu@HOTMAIL.com", "kurucu@mail.gmail.com", "kurucu@yandex.com.tr"]
    )
    def test_organization_registration_with_free_email_is_rejected_422(self, client, session, email):
        response = client.post("/auth/register", json=self._payload(email))

        assert response.status_code == 422, response.text
        body = response.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "email" in body["fields"]
        assert session.execute(select(func.count()).select_from(User).where(User.email == email)).scalar() == 0
        assert (
            session.execute(
                select(func.count()).select_from(Organization).where(Organization.name == "Kurumsal Kimlik A.Ş.")
            ).scalar()
            == 0
        )

    def test_free_email_rejection_does_not_depend_on_the_account_existing(self, client, existing_user, session):
        """Enumeration guard: aynı cevap, hesap var olsa da olmasa da — karar yalnız istekten verilir."""
        existing_user.email = "zaten-kayitli@gmail.com"
        session.flush()

        taken = client.post("/auth/register", json=self._payload("zaten-kayitli@gmail.com"))
        free = client.post("/auth/register", json=self._payload("hic-kayitli-degil@gmail.com"))

        assert taken.status_code == free.status_code == 422
        assert taken.json()["fields"] == free.json()["fields"]

    @pytest.mark.parametrize("account_kind", ["TALENT", "INSTITUTION"])
    def test_free_email_is_still_allowed_for_other_account_kinds(self, client, account_kind):
        payload = self._payload(f"kisi-{account_kind.lower()}@gmail.com", account_kind=account_kind)
        if account_kind == "TALENT":
            payload.pop("entity_name")

        assert client.post("/auth/register", json=payload).status_code == 201

    def test_verification_email_is_queued_for_the_corporate_address(self, client, session):
        from app.models import Outbox

        response = client.post("/auth/register", json=self._payload("yetkili@kurumsal-firma.example.com"))

        assert response.status_code == 201, response.text
        user_id = response.json()["user_id"]
        user = session.execute(select(User).where(User.email == "yetkili@kurumsal-firma.example.com")).scalars().one()
        assert str(user.id) == user_id
        queued = session.execute(select(Outbox).where(Outbox.topic == "email.verify_email")).scalars().all()
        assert [row.payload["user_id"] for row in queued] == [user_id]

    def test_mersis_number_is_stored_on_the_organization(self, client, session):
        response = client.post(
            "/auth/register", json=self._payload("yetkili@mersisli-firma.example.com", legal_id="0123456789012345")
        )

        assert response.status_code == 201, response.text
        org = session.execute(
            select(Organization).where(Organization.name == "Kurumsal Kimlik A.Ş.")
        ).scalars().one()
        assert org.legal_id == "0123456789012345"
        assert org.verification_level == "T1"  # a number alone verifies nothing

    @pytest.mark.parametrize("legal_id", ["123", "012345678901234X", "01234567890123456", "0123 4567 8901 2345"])
    def test_malformed_mersis_number_is_rejected_422(self, client, legal_id):
        response = client.post(
            "/auth/register", json=self._payload("yetkili@bicimsiz-firma.example.com", legal_id=legal_id)
        )

        assert response.status_code == 422
        assert "legal_id" in response.json()["fields"]

    def test_mersis_number_of_another_organization_is_rejected_409_and_nothing_is_created(self, client, session):
        session.add(Organization(name="İlk Sahibi Ltd.", legal_id="0999999999999999", verification_level="T1"))
        session.flush()

        response = client.post(
            "/auth/register", json=self._payload("ikinci@ikinci-firma.example.com", legal_id="0999999999999999")
        )

        assert response.status_code == 409, response.text
        assert response.json()["code"] == "LEGAL_ID_TAKEN"
        assert (
            session.execute(
                select(func.count()).select_from(Organization).where(Organization.name == "Kurumsal Kimlik A.Ş.")
            ).scalar()
            == 0
        )

    def test_mersis_number_is_ignored_for_non_organization_accounts(self, client, session):
        response = client.post(
            "/auth/register",
            json={
                "email": "ogrenci-mersis@example.com",
                "password": "Str0ngPassw0rd!",
                "full_name": "Öğrenci",
                "legal_id": "0111111111111111",
            },
        )

        assert response.status_code == 201
        assert (
            session.execute(
                select(func.count()).select_from(Organization).where(Organization.legal_id == "0111111111111111")
            ).scalar()
            == 0
        )
