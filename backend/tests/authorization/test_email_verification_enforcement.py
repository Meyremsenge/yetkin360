"""
YET-196 (IS-08, K7=a): a user whose e-mail is not verified must not be able to
write anything (docs/AUTHORIZATION.md G6) -> 401 EMAIL_NOT_VERIFIED, and must be
able to get a fresh verification link (POST /auth/resend-verification).

Setup is genuinely committed and the app uses its real get_session, like
test_auth_logout_real_session.py. Users here stay unverified on purpose
(pytestmark below opts out of the conftest auto-verify).

The write-endpoint table is DISCOVERED from app.routes, not hand-listed: a new
write endpoint that forgets get_verified_principal fails here.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import generate_email_token, hash_email_token, hash_password
from app.main import app
from app.models import EmailVerificationToken, Outbox, RefreshToken, TalentProfile, User

pytestmark = pytest.mark.unverified_users

_PASSWORD = "Str0ngPassw0rd!"
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# Public auth endpoints, plus the two authenticated /auth calls that must keep
# working for an unverified user (sign out / renew the session).
_EXEMPT_PATH_PREFIXES = ("/auth/",)


def _write_routes() -> list[tuple[str, str]]:
    # Read the routes from the OpenAPI schema: it carries the full paths and does
    # not depend on how FastAPI wraps included routers internally.
    found = []
    for path, operations in app.openapi()["paths"].items():
        if path.startswith(_EXEMPT_PATH_PREFIXES):
            continue
        for method in operations:
            if method.upper() in _WRITE_METHODS:
                found.append((method.upper(), path))
    return sorted(found)


def _concrete(path: str) -> str:
    out = path
    for part in path.split("/"):
        if part.startswith("{") and part.endswith("}"):
            out = out.replace(part, str(uuid.uuid4()))
    return out


@pytest.fixture
def world():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)

    class World:
        factory = Session
        user_ids: list[uuid.UUID] = []

        @staticmethod
        def make_user(verified: bool = False) -> tuple[uuid.UUID, str]:
            email = f"verify-enforce-{uuid.uuid4()}@example.com"
            s = Session()
            user = User(email=email, password_hash=hash_password(_PASSWORD))
            s.add(user)
            s.flush()
            s.add(TalentProfile(user_id=user.id, full_name="Verify Test", visibility="PRIVATE"))
            s.commit()
            uid = user.id
            if verified:
                s.execute(
                    text("UPDATE users SET email_verified_at = now() WHERE id = :i"), {"i": uid}
                )
                s.commit()
            s.close()
            World.user_ids.append(uid)
            return uid, email

        @staticmethod
        def login(email: str) -> tuple[TestClient, dict[str, str]]:
            client = TestClient(app)
            response = client.post("/auth/login", json={"email": email, "password": _PASSWORD})
            assert response.status_code == 200
            return client, {"X-CSRF-Token": client.cookies["csrf_token"]}

        @staticmethod
        def user(uid: uuid.UUID) -> User:
            s = Session()
            try:
                row = s.execute(select(User).where(User.id == uid)).scalar_one()
                s.expunge(row)
                return row
            finally:
                s.close()

        @staticmethod
        def tokens(uid: uuid.UUID) -> list[EmailVerificationToken]:
            s = Session()
            try:
                rows = s.execute(
                    select(EmailVerificationToken)
                    .where(EmailVerificationToken.user_id == uid)
                    .order_by(EmailVerificationToken.created_at)
                ).scalars().all()
                s.expunge_all()
                return list(rows)
            finally:
                s.close()

        @staticmethod
        def outbox_for(uid: uuid.UUID) -> list[Outbox]:
            s = Session()
            try:
                rows = s.execute(
                    select(Outbox)
                    .where(Outbox.topic == "email.verify_email")
                    .where(text("payload->>'user_id' = :u").bindparams(u=str(uid)))
                    .order_by(Outbox.id)
                ).scalars().all()
                s.expunge_all()
                return list(rows)
            finally:
                s.close()

        @staticmethod
        def add_token(uid: uuid.UUID, age: timedelta, used: bool = False) -> str:
            raw = generate_email_token()
            s = Session()
            s.add(
                EmailVerificationToken(
                    user_id=uid,
                    token_hash=hash_email_token(raw),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24) - age,
                    used_at=datetime.now(timezone.utc) if used else None,
                    created_at=datetime.now(timezone.utc) - age,
                )
            )
            s.commit()
            s.close()
            return raw

    World.user_ids = []
    yield World

    cleanup = Session()
    for uid in World.user_ids:
        cleanup.execute(
            text("DELETE FROM outbox WHERE topic = 'email.verify_email' AND payload->>'user_id' = :u"),
            {"u": str(uid)},
        )
        cleanup.execute(EmailVerificationToken.__table__.delete().where(EmailVerificationToken.user_id == uid))
        cleanup.execute(RefreshToken.__table__.delete().where(RefreshToken.user_id == uid))
        cleanup.execute(TalentProfile.__table__.delete().where(TalentProfile.user_id == uid))
        cleanup.execute(User.__table__.delete().where(User.id == uid))
    cleanup.commit()
    cleanup.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


def test_write_route_discovery_is_not_silently_empty():
    routes = _write_routes()
    # 25 write endpoints at the time of YET-196; the floor catches a broken
    # discovery (e.g. a router prefix change) instead of passing vacuously.
    assert len(routes) >= 25
    assert ("PATCH", "/talents/me") in routes
    assert ("POST", "/engagements") in routes


@pytest.mark.parametrize("method,path", _write_routes())
def test_unverified_user_is_rejected_on_every_write_endpoint(world, method, path):
    uid, email = world.make_user(verified=False)
    client, csrf = world.login(email)

    response = client.request(method, _concrete(path), json={}, headers=csrf)

    assert response.status_code == 401
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.parametrize("method,path", _write_routes())
def test_verified_user_is_not_blocked_by_the_verification_check(world, method, path):
    """Same request, verified account: whatever the endpoint answers (404/422/...),
    it is not the verification gate - so the 401 above is caused by the gate."""
    uid, email = world.make_user(verified=True)
    client, csrf = world.login(email)

    response = client.request(method, _concrete(path), json={}, headers=csrf)

    assert response.json().get("code") != "EMAIL_NOT_VERIFIED"


def test_rejected_write_leaves_the_database_unchanged(world):
    uid, email = world.make_user(verified=False)
    client, csrf = world.login(email)

    response = client.patch("/talents/me", json={"headline": "should not be saved"}, headers=csrf)

    assert response.status_code == 401
    assert response.json()["code"] == "EMAIL_NOT_VERIFIED"
    s = world.factory()
    try:
        profile = s.execute(select(TalentProfile).where(TalentProfile.user_id == uid)).scalar_one()
        assert profile.headline is None
    finally:
        s.close()


def test_unauthenticated_write_is_unauthenticated_not_unverified():
    response = TestClient(app).patch("/talents/me", json={"headline": "x"})
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_unverified_user_can_still_read_logout_and_refresh(world):
    uid, email = world.make_user(verified=False)
    client, csrf = world.login(email)

    assert client.get("/me").status_code == 200

    assert client.post("/auth/refresh").status_code == 204
    csrf = {"X-CSRF-Token": client.cookies["csrf_token"]}
    assert client.post("/auth/logout", headers=csrf).status_code == 204


# ---------------------------------------------------------------------------
# POST /auth/resend-verification
# ---------------------------------------------------------------------------


def test_resend_requires_authentication(world):
    uid, _ = world.make_user(verified=False)

    response = TestClient(app).post("/auth/resend-verification")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert world.tokens(uid) == []


def test_resend_without_csrf_is_403_and_creates_nothing(world):
    uid, email = world.make_user(verified=False)
    client, _csrf = world.login(email)

    response = client.post("/auth/resend-verification")

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"
    assert world.tokens(uid) == []
    assert world.outbox_for(uid) == []


def test_resend_invalidates_old_link_and_delivers_a_working_new_one(world):
    uid, email = world.make_user(verified=False)
    old_raw = world.add_token(uid, age=timedelta(hours=2))
    client, csrf = world.login(email)

    response = client.post("/auth/resend-verification", headers=csrf)

    assert response.status_code == 204
    tokens = world.tokens(uid)
    assert len(tokens) == 2
    assert tokens[0].used_at is not None  # old link invalidated
    assert tokens[1].used_at is None
    outbox = world.outbox_for(uid)
    assert len(outbox) == 1
    assert set(outbox[0].payload) == {"user_id", "raw_token"}  # no address: worker resolves it

    stale = TestClient(app).post("/auth/verify-email", json={"token": old_raw})
    assert stale.status_code == 400
    assert stale.json()["code"] == "INVALID_TOKEN"
    assert world.user(uid).email_verified_at is None

    fresh = TestClient(app).post("/auth/verify-email", json={"token": outbox[0].payload["raw_token"]})
    assert fresh.status_code == 204
    assert world.user(uid).email_verified_at is not None


def test_resend_within_cooldown_is_a_silent_noop(world):
    uid, email = world.make_user(verified=False)
    client, csrf = world.login(email)

    assert client.post("/auth/resend-verification", headers=csrf).status_code == 204
    assert len(world.tokens(uid)) == 1
    assert len(world.outbox_for(uid)) == 1

    second = client.post("/auth/resend-verification", headers=csrf)

    assert second.status_code == 204
    assert len(world.tokens(uid)) == 1
    assert len(world.outbox_for(uid)) == 1


def test_resend_hourly_cap_is_a_silent_noop(world):
    uid, email = world.make_user(verified=False)
    for minutes in (50, 40, 30, 20, 10):  # 5 tokens in the last hour, all past the cooldown
        world.add_token(uid, age=timedelta(minutes=minutes), used=True)
    client, csrf = world.login(email)

    response = client.post("/auth/resend-verification", headers=csrf)

    assert response.status_code == 204
    assert len(world.tokens(uid)) == 5
    assert world.outbox_for(uid) == []


def test_resend_for_already_verified_user_is_a_silent_noop(world):
    uid, email = world.make_user(verified=True)
    client, csrf = world.login(email)

    response = client.post("/auth/resend-verification", headers=csrf)

    assert response.status_code == 204
    assert world.tokens(uid) == []
    assert world.outbox_for(uid) == []
