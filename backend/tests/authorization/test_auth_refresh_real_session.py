"""
Integration test for POST /auth/refresh using the REAL get_session dependency
(no override) — i.e. real per-request commit/rollback, not the test
savepoint fixture used by test_auth_endpoints.py.

Why this file exists separately: every test in test_auth_endpoints.py
overrides get_session with the shared `session` fixture from
tests/authorization/conftest.py, which never commits — it only rolls back
the whole transaction at the end of the test. That hides a real class of
bug: any change made inside a request handler that gets flushed but not
committed before an exception is raised will be silently undone by
get_session's `except Exception: session.rollback()` in production, while
looking correct under the overridden fixture (flushed rows are visible
within the same uncommitted transaction all test long).

This exact bug was found here: app/services/auth.py's refresh_tokens()
revokes an entire refresh-token family on reuse-detection, then raises
InvalidRefreshToken. The API layer turns that into an HTTPException, which
made the real get_session roll back the family-revoke along with it —
the reused (stolen) token's sibling was silently left valid. Fixed by
committing before raising in that one branch (see the comment there).
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password, hash_refresh_token
from app.main import app
from app.models import RefreshToken, User


def test_reused_refresh_token_family_revoke_survives_real_commit_rollback_cycle():
    """
    Uses the real get_session (no dependency_overrides) so the request that
    detects reuse actually commits and the request that raises 401 for it
    actually rolls back — the two must not cancel each other out.

    Deliberately does NOT use the shared `session` fixture from
    tests/authorization/conftest.py: that fixture holds its own connection
    with an outer transaction and a savepoint-mode ORM session, so a
    `commit()` on it only releases the savepoint — it never reaches
    PostgreSQL in a way that app/core/deps.py's separately-pooled engine
    (used by the real get_session) could see. This test needs a genuinely
    separate, really-committed connection to set up and inspect state.
    """
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    setup_session = Session()

    email = f"real-session-reuse-{uuid.uuid4()}@example.com"
    user = User(email=email, password_hash=hash_password("Str0ngPassw0rd!"))
    setup_session.add(user)
    setup_session.commit()
    user_id = user.id
    setup_session.close()

    try:
        client = TestClient(app)

        login_response = client.post("/auth/login", json={"email": email, "password": "Str0ngPassw0rd!"})
        assert login_response.status_code == 200
        original_refresh = login_response.cookies["refresh_token"]

        first_rotation = client.post("/auth/refresh")
        assert first_rotation.status_code == 204
        rotated_refresh = first_rotation.cookies["refresh_token"]

        # Replay the original (now-rotated-away) token: triggers reuse-detection.
        client.cookies.set("refresh_token", original_refresh)
        reuse_response = client.post("/auth/refresh")
        assert reuse_response.status_code == 401
        assert reuse_response.json()["code"] == "INVALID_REFRESH_TOKEN"

        # The token issued by the (now known-stolen) family's rotation must
        # be persisted as revoked in the real database, not just flushed
        # within a transaction that gets rolled back.
        check_session = Session()
        rotated_hash = hash_refresh_token(rotated_refresh)
        row = check_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == rotated_hash)
        ).scalars().first()
        assert row is not None
        assert row.revoked_at is not None, (
            "Family-wide revoke on reuse-detection was rolled back — "
            "the stolen token's sibling is still usable."
        )
        check_session.close()

        # And using it through the real API must be rejected too.
        client.cookies.set("refresh_token", rotated_refresh)
        second_attempt = client.post("/auth/refresh")
        assert second_attempt.status_code == 401
    finally:
        cleanup_session = Session()
        cleanup_session.execute(RefreshToken.__table__.delete().where(RefreshToken.user_id == user_id))
        cleanup_session.execute(User.__table__.delete().where(User.id == user_id))
        cleanup_session.commit()
        cleanup_session.close()
        engine.dispose()
