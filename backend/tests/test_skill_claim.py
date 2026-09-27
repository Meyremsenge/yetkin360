"""
Skill claim endpoint tests (YET-11 — skill-claims).

Implements AC-1 through AC-8 and behavior contract from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Each AC has one or more test functions
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema
- Skill model imported from app.models (status: ACTIVE/MERGED/DEPRECATED)

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest

from app.models import TalentProfile, User, Skill


# ============================================================================
# Fixtures: Users, TalentProfiles, Skills
# ============================================================================


@pytest.fixture
def user_talent_a(session):
    """Talent user A (basic talent profile)."""
    user = User(email="talent-a@example.com", password_hash="hash_talent_a")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def talent_a(session, user_talent_a):
    """Talent profile for user_talent_a."""
    profile = TalentProfile(
        user_id=user_talent_a.id,
        full_name="Test Talent A",
        visibility="PRIVATE",
        headline=None,
        city=None,
        department=None,
        study_year=None,
        public_slug=None,
    )
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def skill_python(session):
    """ACTIVE skill: Python."""
    skill = Skill(
        slug="test-python",
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
        slug="test-javascript",
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
def skill_deprecated(session):
    """DEPRECATED skill: Old Tech."""
    skill = Skill(
        slug="old-tech",
        name_tr="Eski Teknik",
        name_en="Old Tech",
        category="TOOL",
        status="DEPRECATED",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_merged(session, skill_python):
    """MERGED skill: Java (merged into Python)."""
    skill = Skill(
        slug="test-java",
        name_tr="Java",
        name_en="Java",
        category="LANGUAGE",
        status="MERGED",
        parent_id=None,
        merged_into_id=skill_python.id,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-1: POST /talents/me/skills — Add skill claim
# ============================================================================


class TestPostSkillClaim:
    """AC-1: POST /talents/me/skills adds skill claim."""

    def test_post_skills_happy_path(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-1: POST /talents/me/skills with valid skill_id → 201 + claim data.

        Acceptance Criteria:
        - Status code: 201 Created
        - Response contains: skill_id, claimed_level, source="MANUAL"
        - skill_claims table has one new row
        - Transaction committed
        """
        payload = {"skill_id": str(skill_python.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()

        # Assert: response schema
        assert data.get("skill_id") == str(skill_python.id)
        assert data.get("claimed_level") is None  # claimed_level not provided in request → None
        assert data.get("source") == "MANUAL"

        # Verify in database: skill_claim inserted
        # (SkillClaim model not yet defined, this will error at import — expected)

    def test_post_skills_without_claimed_level(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-1: POST without claimed_level → 201, level is NULL or default.

        Acceptance Criteria:
        - Status code: 201
        - Response contains skill_id and source="MANUAL"
        - claimed_level may be NULL
        """
        payload = {"skill_id": str(skill_python.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201

        data = response.json()
        assert data.get("skill_id") == str(skill_python.id)
        assert data.get("source") == "MANUAL"

    def test_post_skills_with_claimed_level(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-1: POST with claimed_level=ADVANCED → 201, level stored.

        Acceptance Criteria:
        - Status code: 201
        - claimed_level in response == "ADVANCED"
        """
        payload = {
            "skill_id": str(skill_python.id),
            "claimed_level": "ADVANCED",
        }

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 201

        data = response.json()
        assert data.get("skill_id") == str(skill_python.id)
        assert data.get("claimed_level") == "ADVANCED"
        assert data.get("source") == "MANUAL"


# ============================================================================
# AC-2: GET /talents/me/skills — List skill claims
# ============================================================================


class TestGetSkillClaims:
    """AC-2: GET /talents/me/skills returns list of claims."""

    def test_get_skills_happy_path(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-2: GET /talents/me/skills with claims → 200 + items list.

        Acceptance Criteria:
        - Status code: 200 OK
        - Response structure: {items: [{skill: {...}, claimed_level: ...}, ...]}
        - Skill fields: id, slug, name_tr, name_en, category
        """
        # Setup: add a skill claim first
        payload = {"skill_id": str(skill_python.id)}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # Now GET
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: items array present
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1

        # Assert: first item structure
        item = data["items"][0]
        assert "skill" in item
        assert "claimed_level" in item

        skill = item["skill"]
        assert skill.get("id") == str(skill_python.id)
        assert skill.get("slug") == "test-python"
        assert skill.get("name_tr") == "Python"
        assert skill.get("name_en") == "Python"
        assert skill.get("category") == "LANGUAGE"

    def test_get_skills_multiple_claims(self, client, session, user_talent_a, talent_a, skill_python, skill_javascript):
        """
        AC-2: GET /talents/me/skills with multiple claims → all returned.

        Acceptance Criteria:
        - Status code: 200
        - items contains both skills
        """
        # Setup: add two skill claims
        for skill in [skill_python, skill_javascript]:
            payload = {"skill_id": str(skill.id)}
            response = client.post(
                "/talents/me/skills",
                json=payload,
                headers={"X-Debug-User-Id": str(user_talent_a.id)},
            )
            assert response.status_code == 201

        # Now GET
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 2

        skills_in_response = {item["skill"]["slug"] for item in data["items"]}
        assert "test-python" in skills_in_response
        assert "test-javascript" in skills_in_response


# ============================================================================
# AC-3: DELETE /talents/me/skills/{skill_id} — Remove skill claim
# ============================================================================


class TestDeleteSkillClaim:
    """AC-3: DELETE /talents/me/skills/{skill_id} removes claim (hard delete)."""

    def test_delete_skills_happy_path(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-3: DELETE /talents/me/skills/{skill_id} → 204 No Content.

        Acceptance Criteria:
        - Status code: 204
        - No response body
        - skill_claim row is hard-deleted from database
        """
        # Setup: add skill claim
        payload = {"skill_id": str(skill_python.id)}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # DELETE
        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 204

        # Assert: no body
        assert response.text == "" or len(response.text) == 0

    def test_delete_skills_then_get_empty(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-3 (verification): After DELETE, GET returns empty list.

        Acceptance Criteria:
        - After delete, GET /talents/me/skills → {items: []}
        """
        # Setup: add skill claim
        payload = {"skill_id": str(skill_python.id)}
        post_response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert post_response.status_code == 201

        # DELETE
        delete_response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert delete_response.status_code == 204

        # GET — should be empty
        get_response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["items"] == []


# ============================================================================
# AC-4: POST with var olmayan skill_id → 404 SKILL_NOT_FOUND
# ============================================================================


class TestSkillNotFound:
    """AC-4: POST with nonexistent skill_id → 404 SKILL_NOT_FOUND."""

    def test_post_nonexistent_skill_404(self, client, session, user_talent_a, talent_a):
        """
        AC-4: POST /talents/me/skills with nonexistent skill_id → 404.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_NOT_FOUND"
        - No skill_claim inserted
        """
        import uuid

        fake_skill_id = uuid.uuid4()

        payload = {"skill_id": str(fake_skill_id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: error code
        assert data.get("code") == "SKILL_NOT_FOUND", f"Expected code='SKILL_NOT_FOUND', got {data.get('code')}"

        # Assert: message present
        assert "message" in data
        assert isinstance(data["message"], str)

        # Assert: request_id present
        assert "request_id" in data


# ============================================================================
# AC-5: POST with duplicate skill_id → 409 ALREADY_CLAIMED
# ============================================================================


class TestDuplicateSkillClaim:
    """AC-5: POST duplicate skill → 409 ALREADY_CLAIMED."""

    def test_post_duplicate_skill_409(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-5: POST same skill twice → 409 on second attempt.

        Acceptance Criteria:
        - First POST: 201
        - Second POST (same skill): 409 Conflict
        - Error code: "ALREADY_CLAIMED"
        - No new row inserted
        """
        payload = {"skill_id": str(skill_python.id)}

        # First POST — should succeed
        response1 = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )
        assert response1.status_code == 201

        # Second POST — should fail
        response2 = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response2.status_code == 409

        data = response2.json()

        # Assert: error code
        assert data.get("code") == "ALREADY_CLAIMED", f"Expected code='ALREADY_CLAIMED', got {data.get('code')}"

        # Assert: message present
        assert "message" in data


# ============================================================================
# AC-6: POST with MERGED/DEPRECATED skill → 404 SKILL_NOT_FOUND
# ============================================================================


class TestMergedDeprecatedSkill:
    """AC-6: POST MERGED/DEPRECATED skill → 404 SKILL_NOT_FOUND (same code)."""

    def test_post_deprecated_skill_404(self, client, session, user_talent_a, talent_a, skill_deprecated):
        """
        AC-6: POST with DEPRECATED skill → 404 SKILL_NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_NOT_FOUND" (not a special code for deprecated)
        - Status difference not revealed to client
        """
        payload = {"skill_id": str(skill_deprecated.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: same code as nonexistent skill
        assert data.get("code") == "SKILL_NOT_FOUND"

    def test_post_merged_skill_404(self, client, session, user_talent_a, talent_a, skill_merged):
        """
        AC-6: POST with MERGED skill → 404 SKILL_NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_NOT_FOUND"
        - merged_into_id field not exposed
        - No auto-redirect to merged_into_id
        """
        payload = {"skill_id": str(skill_merged.id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        assert data.get("code") == "SKILL_NOT_FOUND"


# ============================================================================
# AC-7: DELETE with var olmayan/claim edilmemiş skill_id → 404 SKILL_CLAIM_NOT_FOUND
# ============================================================================


class TestSkillClaimNotFound:
    """AC-7: DELETE nonexistent/unclaimed skill → 404 SKILL_CLAIM_NOT_FOUND."""

    def test_delete_unclaimed_skill_404(self, client, session, user_talent_a, talent_a, skill_python):
        """
        AC-7: DELETE /talents/me/skills/{skill_id} where claim doesn't exist → 404.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_CLAIM_NOT_FOUND"
        """
        # Don't add the skill claim first

        response = client.delete(
            f"/talents/me/skills/{skill_python.id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: error code (different from SKILL_NOT_FOUND)
        assert data.get("code") == "SKILL_CLAIM_NOT_FOUND", f"Expected code='SKILL_CLAIM_NOT_FOUND', got {data.get('code')}"

        # Assert: message present
        assert "message" in data

    def test_delete_nonexistent_skill_id_404(self, client, session, user_talent_a, talent_a):
        """
        AC-7: DELETE with nonexistent skill_id → 404 SKILL_CLAIM_NOT_FOUND.

        Acceptance Criteria:
        - Status code: 404
        - Error code: "SKILL_CLAIM_NOT_FOUND" (even though skill itself doesn't exist)
        """
        import uuid

        fake_skill_id = uuid.uuid4()

        response = client.delete(
            f"/talents/me/skills/{fake_skill_id}",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        assert data.get("code") == "SKILL_CLAIM_NOT_FOUND"


# ============================================================================
# AC-8: GET with no claims → 200 + empty list
# ============================================================================


class TestEmptySkillList:
    """AC-8: GET /talents/me/skills with no claims → 200 + {items: []}."""

    def test_get_skills_empty_200(self, client, session, user_talent_a, talent_a):
        """
        AC-8: GET /talents/me/skills with no claims → 200, not an error.

        Acceptance Criteria:
        - Status code: 200 OK (not 404)
        - Response: {items: []}
        - No claims present
        """
        response = client.get(
            "/talents/me/skills",
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 200

        data = response.json()

        # Assert: items array is empty, not missing
        assert "items" in data
        assert data["items"] == []


# ============================================================================
# Response Schema Validation (all responses must follow API.md §1.4)
# ============================================================================


class TestResponseSchema:
    """Verify response schemas match API.md §1.4 error contract."""

    def test_error_response_has_code_message_request_id(self, client, user_talent_a, talent_a):
        """All error responses must have {code, message, request_id}."""
        import uuid

        fake_skill_id = uuid.uuid4()

        payload = {"skill_id": str(fake_skill_id)}

        response = client.post(
            "/talents/me/skills",
            json=payload,
            headers={"X-Debug-User-Id": str(user_talent_a.id)},
        )

        assert response.status_code == 404

        data = response.json()

        # Assert: error has code, message, request_id
        assert "code" in data, "Error response must have 'code' field"
        assert "message" in data, "Error response must have 'message' field"
        assert "request_id" in data, "Error response must have 'request_id' field"

        # Assert: code is SCREAMING_SNAKE_CASE
        assert isinstance(data["code"], str)
        assert "_" in data["code"] or data["code"].isupper()

        # Assert: message is Turkish (non-empty string)
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0
