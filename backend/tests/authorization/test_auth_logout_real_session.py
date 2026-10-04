"""
YET-185 (GUV-06): logout must revoke the refresh-token family even though the
browser only attaches the refresh cookie to the paths its Path attribute
covers.

test_auth_endpoints.py::TestLogout::test_logout_with_valid_csrf_revokes_refresh_family
passes for the wrong reason: logout's delete_cookie() empties the client's own
jar, so the follow-up /auth/refresh has no cookie and 401s regardless of
whether the DB row was revoked. A stolen copy of the token is the real threat,
so these tests replay the token from a SEPARATE client and read the DB row.

Uses the real get_session (no override) and a genuinely committed setup, like
test_auth_refresh_real_session.py.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password, hash_refresh_token
from app.main import app
from app.models import RefreshToken, User

_PASSWORD = "Str0ngPassw0rd!"


def _make_user(Session) -> tuple[uuid.UUID, str]:
    email = f"real-session-logout-{uuid.uuid4()}@example.com"
    setup_session = Session()
    user = User(email=email, password_hash=hash_password(_PASSWORD))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()
    return user_id, email


def _cleanup(Session, engine, user_id: uuid.UUID) -> None:
    cleanup_session = Session()
    cleanup_session.execute(RefreshToken.__table__.delete().where(RefreshToken.user_id == user_id))
    cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
    cleanup_session.commit()
    cleanup_session.close()
    engine.dispose()


def _stored_row(Session, raw_token: str) -> RefreshToken | None:
    check_session = Session()
    try:
        return check_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        ).scalars().first()
    finally:
        check_session.close()


def test_logout_revokes_refresh_token_family_for_stolen_copy():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    user_id, email = _make_user(Session)

    try:
        browser = TestClient(app)
        login_response = browser.post("/auth/login", json={"email": email, "password": _PASSWORD})
        assert login_response.status_code == 200
        stolen_refresh = login_response.cookies["refresh_token"]
        csrf_token = login_response.cookies["csrf_token"]

        # The token exists and is live before logout.
        row_before = _stored_row(Session, stolen_refresh)
        assert row_before is not None
        assert row_before.revoked_at is None

        logout_response = browser.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
        assert logout_response.status_code == 204

        # Re-read the DB: the stolen token's row must be revoked.
        row_after = _stored_row(Session, stolen_refresh)
        assert row_after is not None
        assert row_after.revoked_at is not None, (
            "logout did not revoke the refresh-token family — a stolen refresh token stays valid."
        )

        # And the attacker, holding only the stolen cookie, gets nothing.
        attacker = TestClient(app)
        attacker.cookies.set("refresh_token", stolen_refresh)
        replay = attacker.post("/auth/refresh")
        assert replay.status_code == 401
        assert replay.json()["code"] == "INVALID_REFRESH_TOKEN"
    finally:
        _cleanup(Session, engine, user_id)


def test_refresh_cookie_path_covers_logout_and_legacy_path_is_cleared():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    user_id, email = _make_user(Session)

    try:
        client = TestClient(app)
        login_response = client.post("/auth/login", json={"email": email, "password": _PASSWORD})
        assert login_response.status_code == 200

        set_cookie_headers = login_response.headers.get_list("set-cookie")
        live = [h for h in set_cookie_headers if h.startswith("refresh_token=") and "Max-Age=0" not in h]
        legacy_deletes = [
            h for h in set_cookie_headers
            if h.startswith("refresh_token=") and "Max-Age=0" in h and "Path=/auth/refresh" in h
        ]
        assert len(live) == 1
        assert "Path=/auth;" in live[0] + ";"
        assert "Path=/auth/refresh" not in live[0]
        assert len(legacy_deletes) == 1

        logout_response = client.post("/auth/logout", headers={"X-CSRF-Token": client.cookies["csrf_token"]})
        assert logout_response.status_code == 204
        deletions = [
            h for h in logout_response.headers.get_list("set-cookie")
            if h.startswith("refresh_token=") and "Max-Age=0" in h
        ]
        assert {"/auth", "/auth/refresh"} == {
            part.strip().removeprefix("Path=")
            for h in deletions
            for part in h.split(";")
            if part.strip().startswith("Path=")
        }
    finally:
        _cleanup(Session, engine, user_id)


def test_logout_with_another_users_refresh_token_does_not_revoke_victims_family():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    victim_id, victim_email = _make_user(Session)
    attacker_id, attacker_email = _make_user(Session)

    try:
        victim = TestClient(app)
        victim_login = victim.post("/auth/login", json={"email": victim_email, "password": _PASSWORD})
        assert victim_login.status_code == 200
        victim_refresh = victim_login.cookies["refresh_token"]
        assert _stored_row(Session, victim_refresh) is not None

        attacker = TestClient(app)
        attacker_login = attacker.post("/auth/login", json={"email": attacker_email, "password": _PASSWORD})
        assert attacker_login.status_code == 200
        # Attacker presents the victim's refresh token on their own logout.
        attacker.cookies.set("refresh_token", victim_refresh, path="/auth")
        response = attacker.post("/auth/logout", headers={"X-CSRF-Token": attacker_login.cookies["csrf_token"]})
        assert response.status_code == 204

        victim_row = _stored_row(Session, victim_refresh)
        assert victim_row is not None
        assert victim_row.revoked_at is None
        # The victim's session still refreshes.
        refresh = victim.post("/auth/refresh")
        assert refresh.status_code == 204
    finally:
        _cleanup(Session, engine, victim_id)
        _cleanup(Session, create_engine(settings.database_url), attacker_id)
