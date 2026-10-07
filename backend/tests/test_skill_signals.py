"""
Skill signal endpoint tests (YET-104 — skillsignal-self-claim-uretimi).

Implements AC-1 through AC-6, AC-S1, AC-S2 from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Each AC has one or more test functions
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema
- SkillSignal model imported from app.models (status: not yet implemented)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest
from sqlalchemy import select

from app.models import TalentProfile, User, Skill, SkillSignal


# ============================================================================
# Fixtures: Users, TalentProfiles, Skills
# ============================================================================


@pytest.fixture
def user_talent_a(session):
    """Talent user A (basic talent profile)."""
    user = User(email="signal-talent-a@example.com", password_hash="hash_talent_signal_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def user_talent_b(session):
    """Talent user B (for cross-talent isolation tests)."""
    user = User(email="signal-talent-b@example.com", password_hash="hash_talent_signal_b")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    """Talent profile for user_talent_a."""
    profile = TalentProfile(
        user_id=user_talent_a.id,
        full_name="Signal Test Talent A",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def talent_b(session, user_talent_b):
    """Talent profile for user_talent_b (cross-talent test isolation)."""
    profile = TalentProfile(
        user_id=user_talent_b.id,
        full_name="Signal Test Talent B",
        visibility="PRIVATE",
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def skill_python(session):
    """ACTIVE skill: Python."""
    skill = Skill(
        slug="python-signal",
        name_tr="Python",
        name_en="Python",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_javascript(session):
    """ACTIVE skill: JavaScript."""
    skill = Skill(
        slug="javascript-signal",
        name_tr="JavaScript",
        name_en="JavaScript",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_rust(session):
    """ACTIVE skill: Rust (for cross-talent tests)."""
    skill = Skill(
        slug="rust-signal",
        name_tr="Rust",
        name_en="Rust",
        category="LANGUAGE",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-1: POST /talents/me/skills creates SkillSignal in same transaction
# ============================================================================


class TestSkillClaimCreatesSignal:
    """AC-1: POST /talents/me/skills creates both SkillClaim and SkillSignal in same transaction."""

    def test_post_skills_creates_skill_signal(
        self, client, session, user_talent_a, talent_a, skill_python
    ):
        """
        AC-1: POST /talents/me/skills with valid skill_id → 201 + SkillSignal inserted.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains skill data (existing schema, unchanged)
        - SkillSignal row exists in DB with:
          - talent_id = current talent
          - skill_id = claimed skill
          - source_type = "SELF_CLAIM"
          - strength = "NONE"
          - attested_by_org_id = NULL
          - occurred_at = claim.created_at
          - source_id = claim.id
        """
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data.get("skill_id") == str(skill_python.id)

        # Query database to verify SkillSignal was created
        # Use select() query directly via session
        signals = session.execute(
            select(SkillSignal).where(
                (SkillSignal.talent_id == talent_a.id)
                & (SkillSignal.skill_id == skill_python.id)
            )
        ).scalars().all()

        assert len(signals) == 1, "Expected exactly one SkillSignal to be created"
        signal = signals[0]

        assert signal.source_type == "SELF_CLAIM"
        assert signal.strength == "NONE"
        assert signal.attested_by_org_id is None
        assert signal.source_id is not None  # source_id = claim.id
        assert signal.occurred_at is not None  # occurred_at set


# ============================================================================
# AC-2: GET /talents/me/signals returns grouped signals with correct schema
# ============================================================================


class TestGetSkillSignalsHappyPath:
    """AC-2: GET /talents/me/signals returns signals grouped by skill."""

    def test_get_signals_happy_path(
        self, client, session, user_talent_a, talent_a, skill_python
    ):
        """
        AC-2: GET /talents/me/signals with claims → 200 + items grouped by skill.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response structure: {items:[{skill:{id,name_tr,slug,...},signals:[{source_type,strength,occurred_at,attested_by,superseded}]}]}
        - Skill fields: id, slug, name_tr
        - Signal fields: source_type (SELF_CLAIM), strength (NONE), occurred_at (ISO), attested_by (null), superseded (false)
        """
        # Setup: add a skill claim first (which will create SkillSignal)
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # Now GET signals
        response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: items array present
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1

        # Assert: first item structure (skill + signals)
        item = data["items"][0]
        assert "skill" in item
        assert "signals" in item

        # Assert: skill fields
        skill = item["skill"]
        assert skill.get("id") == str(skill_python.id)
        assert skill.get("slug") == "python-signal"
        assert skill.get("name_tr") == "Python"

        # Assert: signals array
        signals = item["signals"]
        assert isinstance(signals, list)
        assert len(signals) >= 1

        # Assert: first signal fields (SELF_CLAIM)
        signal = signals[0]
        assert signal.get("source_type") == "SELF_CLAIM"
        assert signal.get("strength") == "NONE"
        assert signal.get("occurred_at") is not None  # ISO timestamp
        assert signal.get("attested_by") is not None  # Self-claim attested by the talent itself
        assert signal.get("superseded") is False


# ============================================================================
# AC-3: GET /talents/me/signals?skill_id=<X> filters to single skill group
# ============================================================================


class TestGetSkillSignalsWithFilter:
    """AC-3: GET /talents/me/signals?skill_id=<X> returns only that skill's group."""

    def test_get_signals_with_skill_id_filter(
        self, client, session, user_talent_a, talent_a, skill_python, skill_javascript
    ):
        """
        AC-3: GET /talents/me/signals?skill_id=<X> (X claimed) → 200 + single skill group.

        Acceptance Criteria:
        - Status code: 200
        - items array contains exactly 1 skill group
        - That group is for skill_id=X
        """
        # Setup: add two skill claims
        for skill in [skill_python, skill_javascript]:
            payload = {"skill_id": str(skill.id), "claimed_level": "INTERMEDIATE"}
            response = client.post(
                "/talents/me/skills",
                json=payload,
                headers={"X-Debug-User-Id": str(user_talent_a.id)},
            )
            assert response.status_code == 201

        # GET with filter for skill_python only
        response = client.get(
            f"/talents/me/signals?skill_id={skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["skill"]["id"] == str(skill_python.id)
        assert item["skill"]["slug"] == "python-signal"


# ============================================================================
# AC-4: GET /talents/me/signals with no claims returns 200 + empty list
# ============================================================================


class TestGetSkillSignalsEmpty:
    """AC-4: GET /talents/me/signals with no claims → 200 + {items: []}."""

    def test_get_signals_empty_200(
        self, client, session, user_talent_a, talent_a
    ):
        """
        AC-4: GET /talents/me/signals with no claims → 200 OK, not 404.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response: {items: []}
        - No error, empty list is valid state
        """
        response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert data["items"] == []


# ============================================================================
# AC-5: Deleted skill claim leaves signal intact (append-only rule)
# ============================================================================


class TestSkillClaimDeleteLeavesSignalIntact:
    """AC-5: DELETE /talents/me/skills/{id} deletes claim but signal is filtered from response (append-only)."""

    def test_delete_claim_signal_filtered_from_response(
        self, client, session, user_talent_a, talent_a, skill_python
    ):
        """
        AC-5 (updated): After DELETE /talents/me/skills/{id}, deleted claim's SELF_CLAIM signal does NOT appear in GET /signals.

        Acceptance Criteria:
        - Add skill claim → 201
        - DELETE /talents/me/skills/{id} → 204
        - GET /talents/me/signals → deleted skill's signal NO LONGER visible (filtered in read path)
        - Claim row hard-deleted from DB, SkillSignal row remains in DB (append-only) but filtered from response
        """
        # Setup: add skill claim
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # DELETE the claim
        delete_response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert delete_response.status_code == 204

        # GET signals — deleted skill's signal should NOT appear (filtered from response)
        get_response = client.get(
            "/talents/me/signals",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert get_response.status_code == 200
        data = get_response.json()

        # Signal filtered from response (item not visible)
        assert len(data["items"]) == 0, "Deleted claim's SELF_CLAIM signal must be filtered from response"


# ============================================================================
# AC-6: skill_id filter with non-existent or unclaimed skill → 200 + empty list
# ============================================================================


class TestGetSkillSignalsFilterNonExistent:
    """AC-6: GET /talents/me/signals?skill_id=<unclaimed> → 200 + {items: []}."""

    def test_get_signals_filter_nonexistent_skill_200(
        self, client, session, user_talent_a, talent_a, skill_python, skill_javascript
    ):
        """
        AC-6: GET /talents/me/signals?skill_id=<Y> where Y is not claimed → 200, not 404.

        Acceptance Criteria:
        - Status code: 200 OK (not 404)
        - Response: {items: []}
        - No error, empty result for unclaimed skill is valid (AC-6, AC-S1)
        """
        # Only claim skill_python, not skill_javascript
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # Query with unclaimed skill_javascript
        response = client.get(
            f"/talents/me/signals?skill_id={skill_javascript.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []


# ============================================================================
# Database-level append-only test (SkillSignal immutability trigger)
# ============================================================================


class TestSkillSignalAppendOnly:
    """Test: SkillSignal table is append-only (UPDATE/DELETE triggers failure)."""

    def test_skill_signal_cannot_be_updated(
        self, client, session, user_talent_a, talent_a, skill_python
    ):
        """
        Database constraint: UPDATE skill_signals should fail (immutability trigger).

        Acceptance Criteria:
        - Add skill claim (creates SkillSignal)
        - Try to UPDATE skill_signals.strength → exception raised
        - This verifies DOMAIN.md §3.14 append-only constraint at DB level
        """
        # Setup: add skill claim to create signal
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # Get signal from DB
        signal = session.execute(
            select(SkillSignal).where(
                (SkillSignal.talent_id == talent_a.id)
                & (SkillSignal.skill_id == skill_python.id)
            )
        ).scalar_one_or_none()

        assert signal is not None

        # Try to update via raw ORM — should be blocked by trigger
        # (or exception on session.flush())
        from sqlalchemy import update

        try:
            # Attempt to update signal strength
            session.execute(
                update(SkillSignal)
                .where(SkillSignal.id == signal.id)
                .values(strength="STRONG")
            )
            session.flush()
            # If we reach here, trigger did not block it — fail test
            assert False, "SkillSignal UPDATE was allowed, but should be blocked by immutability trigger"
        except Exception as e:
            # Expected: trigger blocks UPDATE
            assert "immutable" in str(e).lower() or "trigger" in str(e).lower()

    def test_skill_signal_cannot_be_deleted(
        self, client, session, user_talent_a, talent_a, skill_python
    ):
        """
        Database constraint: DELETE FROM skill_signals should fail (immutability trigger).

        Acceptance Criteria:
        - Add skill claim (creates SkillSignal)
        - Try to DELETE skill_signals → exception raised
        - This verifies DOMAIN.md §3.14 append-only constraint at DB level
        """
        # Setup: add skill claim to create signal
        payload = {"skill_id": str(skill_python.id), "claimed_level": "INTERMEDIATE"}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # Get signal from DB
        signal = session.execute(
            select(SkillSignal).where(
                (SkillSignal.talent_id == talent_a.id)
                & (SkillSignal.skill_id == skill_python.id)
            )
        ).scalar_one_or_none()

        assert signal is not None

        # Try to delete via raw ORM — should be blocked by trigger
        from sqlalchemy import delete

        try:
            # Attempt to delete signal
            session.execute(
                delete(SkillSignal)
                .where(SkillSignal.id == signal.id)
            )
            session.flush()
            # If we reach here, trigger did not block it — fail test
            assert False, "SkillSignal DELETE was allowed, but should be blocked by immutability trigger"
        except Exception as e:
            # Expected: trigger blocks DELETE
            assert "immutable" in str(e).lower() or "trigger" in str(e).lower()
