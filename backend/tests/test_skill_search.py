"""
Skill search endpoint tests (YET-10 — skill-search).

Implements AC-1 through AC-9 from atdd.md.

Test patterns:
- Real Postgres transaction per test (inherited from conftest.py)
- FastAPI TestClient for HTTP endpoint testing
- Each AC has one or more test functions
- Error responses validated against {"code": ..., "message": ..., "request_id": ...} schema

Status: Tests are RED/IMPORT-ERROR — implementation not yet written.
This is expected behavior. Tests implement behavior contract (ATDD).
"""

import pytest

from app.models import Skill, User


# ============================================================================
# Fixtures: Users, Skills
# ============================================================================


@pytest.fixture
def user_talent(session):
    """Authenticated test user (any skill searcher)."""
    user = User(email="searcher@example.com", password_hash="hash_searcher")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def skill_python_active(session):
    """ACTIVE skill: Python language."""
    skill = Skill(
        slug="python",
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
def skill_javascript_active(session):
    """ACTIVE skill: JavaScript language."""
    skill = Skill(
        slug="javascript",
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
def skill_react_framework(session):
    """ACTIVE skill: React framework."""
    skill = Skill(
        slug="react",
        name_tr="React",
        name_en="React",
        category="FRAMEWORK",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_fastapi_framework(session):
    """ACTIVE skill: FastAPI framework."""
    skill = Skill(
        slug="fastapi",
        name_tr="FastAPI",
        name_en="FastAPI",
        category="FRAMEWORK",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_docker_tool(session):
    """ACTIVE skill: Docker tool."""
    skill = Skill(
        slug="docker",
        name_tr="Docker",
        name_en="Docker",
        category="TOOL",
        status="ACTIVE",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_merged_into_python(session, skill_python_active):
    """MERGED skill pointing to Python."""
    skill = Skill(
        slug="python2",
        name_tr="Python 2",
        name_en="Python 2",
        category="LANGUAGE",
        status="MERGED",
        parent_id=None,
        merged_into_id=skill_python_active.id,
    )
    session.add(skill)
    session.flush()
    return skill


@pytest.fixture
def skill_deprecated(session):
    """DEPRECATED skill."""
    skill = Skill(
        slug="deprecated-old",
        name_tr="Deprecated Old Skill",
        name_en="Deprecated Old Skill",
        category="LANGUAGE",
        status="DEPRECATED",
        parent_id=None,
        merged_into_id=None,
    )
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# AC-1: GET /skills?q=python → 200 + {items: [...]} (search by name/slug)
# ============================================================================


class TestSkillSearchHappyPath:
    """AC-1: GET /skills with query parameter returns matching ACTIVE skills."""

    def test_search_by_name_en(self, client, user_talent, skill_python_active, skill_javascript_active):
        """
        AC-1: Search by English name.

        GET /skills?q=python → 200 + {items: [{id, slug, name_tr, name_en, category, parent_id}, ...]}
        """
        response = client.get("/skills?q=python", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1

        # Find Python skill in results
        python_item = next((item for item in data["items"] if item["slug"] == "python"), None)
        assert python_item is not None, "Python skill not found in search results"

        # Validate response schema
        assert "id" in python_item
        assert python_item["slug"] == "python"
        assert python_item["name_tr"] == "Python"
        assert python_item["name_en"] == "Python"
        assert python_item["category"] == "LANGUAGE"
        assert python_item["parent_id"] is None

    def test_search_by_name_tr(self, client, user_talent, skill_python_active):
        """AC-1: Search by Turkish name."""
        response = client.get("/skills?q=Python", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        python_item = next((item for item in data["items"] if item["slug"] == "python"), None)
        assert python_item is not None

    def test_search_by_slug(self, client, user_talent, skill_python_active):
        """AC-1: Search by slug (case-insensitive CITEXT)."""
        response = client.get("/skills?q=python", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        python_item = next((item for item in data["items"] if item["slug"] == "python"), None)
        assert python_item is not None

    def test_search_returns_only_active_skills(self, client, user_talent, skill_python_active, skill_merged_into_python):
        """
        AC-1 + AC-7: Search results include only ACTIVE skills.

        Merged/deprecated skills must NOT appear.
        """
        response = client.get("/skills?q=python", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        slugs = [item["slug"] for item in data["items"]]
        assert "python" in slugs, "Active Python skill should be in results"
        assert "python2" not in slugs, "MERGED Python 2 skill should NOT be in results"


# ============================================================================
# AC-2: GET /skills (no q) → 200 + first limit (default 50) ACTIVE skills
# ============================================================================


class TestSkillSearchNoQuery:
    """AC-2: GET /skills without query parameter returns first limit (default 50) skills."""

    def test_get_skills_no_query_returns_default_limit(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_javascript_active,
        skill_react_framework,
        skill_fastapi_framework,
        skill_docker_tool,
    ):
        """
        AC-2: GET /skills (no q) → 200 + {items: [...]} first limit (default 50).

        This is a valid request, not an error.
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        # At least the 5 skills we created should be returned (up to default limit 50)
        assert len(data["items"]) <= 50, "Should respect default limit of 50"
        assert len(data["items"]) >= 5, "Should return at least the 5 skills we created"

    def test_get_skills_no_query_with_limit_parameter(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_javascript_active,
        skill_react_framework,
    ):
        """AC-2: GET /skills with explicit limit parameter."""
        response = client.get("/skills?limit=2", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) <= 2, "Should respect custom limit of 2"


# ============================================================================
# AC-3: GET /skills?q=nonexistent → 200 + {items: []} (not 404)
# ============================================================================


class TestSkillSearchNoResults:
    """AC-3: Search with no matches returns 200 + empty list, NOT 404."""

    def test_search_no_matches_returns_empty_list(self, client, user_talent, skill_python_active):
        """
        AC-3: GET /skills?q=nonexistent → 200 + {items: []}.

        This is a valid search result (empty), not a 404 error.
        """
        response = client.get("/skills?q=nonexistentskill123456", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "items" in data
        assert data["items"] == []


# ============================================================================
# AC-4: GET /skills?category=LANGUAGE → 200 + filtered by category
# ============================================================================


class TestSkillSearchByCategory:
    """AC-4: Search with category filter returns only skills in that category."""

    def test_search_by_category_language(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_javascript_active,
        skill_react_framework,
        skill_fastapi_framework,
    ):
        """AC-4: GET /skills?category=LANGUAGE → return only LANGUAGE skills."""
        response = client.get("/skills?category=LANGUAGE", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) >= 2, "Should return at least Python and JavaScript"
        for item in data["items"]:
            assert item["category"] == "LANGUAGE", f"All items should be LANGUAGE, got {item['category']}"

    def test_search_by_category_framework(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_react_framework,
        skill_fastapi_framework,
    ):
        """AC-4: GET /skills?category=FRAMEWORK → return only FRAMEWORK skills."""
        response = client.get("/skills?category=FRAMEWORK", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) >= 2, "Should return at least React and FastAPI"
        for item in data["items"]:
            assert item["category"] == "FRAMEWORK", f"All items should be FRAMEWORK, got {item['category']}"

    def test_search_by_category_with_query(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_react_framework,
        skill_fastapi_framework,
    ):
        """AC-4: GET /skills?q=fast&category=FRAMEWORK → combined filter."""
        response = client.get(
            "/skills?q=fast&category=FRAMEWORK", headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 200
        data = response.json()

        # Should match FastAPI (FRAMEWORK category + "fast" in name_en)
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert item["category"] == "FRAMEWORK"


# ============================================================================
# AC-5: GET /skills?category=INVALID_ENUM → 422 (Pydantic validation)
# ============================================================================


class TestSkillSearchInvalidCategory:
    """AC-5: Invalid category enum value returns 422."""

    def test_invalid_category_returns_422(self, client, user_talent):
        """
        AC-5: GET /skills?category=INVALID → 422 + {code: "VALIDATION_ERROR", ...}.

        Pydantic enum validation catches invalid categories.
        """
        response = client.get("/skills?category=INVALIDCATEGORY", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        assert "code" in data
        assert data["code"] == "VALIDATION_ERROR"
        assert "message" in data
        assert "request_id" in data

    def test_invalid_category_with_query_returns_422(self, client, user_talent, skill_python_active):
        """AC-5: Invalid category is validated even with query parameter."""
        response = client.get(
            "/skills?q=python&category=BADCATEGORY", headers={"X-Debug-User-Id": str(user_talent.id)}
        )

        assert response.status_code == 422


# ============================================================================
# AC-6: GET /skills?limit=101 → 422 (exceeds max 100)
# ============================================================================


class TestSkillSearchLimitValidation:
    """AC-6: Limit parameter over 100 returns 422."""

    def test_limit_over_100_returns_422(self, client, user_talent):
        """
        AC-6: GET /skills?limit=101 → 422 + {code: "VALIDATION_ERROR", ...}.

        Max limit is 100.
        """
        response = client.get("/skills?limit=101", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

        data = response.json()
        assert "code" in data
        assert data["code"] == "VALIDATION_ERROR"

    def test_limit_exactly_100_is_valid(self, client, user_talent, skill_python_active):
        """AC-6: Limit of 100 (boundary) is valid."""
        response = client.get("/skills?limit=100", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200

    def test_limit_0_or_negative_returns_422(self, client, user_talent):
        """AC-6: Limit <= 0 should be invalid."""
        response = client.get("/skills?limit=0", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 422


# ============================================================================
# AC-7: MERGED/DEPRECATED skills never appear in results
# ============================================================================


class TestSkillSearchFiltersInactiveStatus:
    """AC-7: MERGED and DEPRECATED skills are always filtered out."""

    def test_merged_skill_never_in_results(
        self, client, user_talent, skill_python_active, skill_merged_into_python
    ):
        """
        AC-7: A MERGED skill should never appear, even in full list.

        GET /skills (or any filter) must exclude status != 'ACTIVE'.
        """
        # Merged skill exists in DB
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        slugs = [item["slug"] for item in data["items"]]
        assert "python2" not in slugs, "MERGED skill 'python2' should never appear"
        assert "python" in slugs, "ACTIVE skill 'python' should appear"

    def test_deprecated_skill_never_in_results(
        self, client, user_talent, skill_python_active, skill_deprecated
    ):
        """AC-7: A DEPRECATED skill should never appear."""
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        slugs = [item["slug"] for item in data["items"]]
        assert "deprecated-old" not in slugs, "DEPRECATED skill should never appear"

    def test_search_by_merged_skill_slug_returns_empty(
        self, client, user_talent, skill_python_active, skill_merged_into_python
    ):
        """AC-7: Searching for a MERGED skill by slug returns empty, not the skill."""
        response = client.get("/skills?q=python2", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == [], "Searching for MERGED skill should return empty list"

    def test_search_by_deprecated_skill_slug_returns_empty(
        self, client, user_talent, skill_deprecated
    ):
        """AC-7: Searching for a DEPRECATED skill by slug returns empty."""
        response = client.get("/skills?q=deprecated", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == [], "Searching for DEPRECATED skill should return empty list"


# ============================================================================
# AC-8: Unauthenticated request → 401
# ============================================================================


class TestSkillSearchAuthentication:
    """AC-8: Requests without authentication return 401."""

    def test_missing_auth_header_returns_401(self, client, skill_python_active):
        """
        AC-8: GET /skills without X-Debug-User-Id header → 401.

        This is a secured endpoint requiring authentication.
        """
        response = client.get("/skills")  # No X-Debug-User-Id header

        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    def test_invalid_user_id_returns_401(self, client):
        """AC-8: GET /skills with invalid user ID → 401."""
        response = client.get("/skills", headers={"X-Debug-User-Id": "invalid-uuid-123"})

        assert response.status_code == 401


# ============================================================================
# AC-9: Seed script produces representative skill set
# ============================================================================


class TestSkillSearchSeeded:
    """
    AC-9: Seed script populates a representative skill set.

    Note: This test verifies that skills are present in DB (fixture-created),
    not the seed script itself (which runs separately).
    The seed script implementation is tested in its own integration test.
    """

    def test_skill_distribution_across_categories(
        self,
        client,
        user_talent,
        skill_python_active,
        skill_javascript_active,
        skill_react_framework,
        skill_fastapi_framework,
        skill_docker_tool,
    ):
        """
        AC-9: Representative skill set includes examples from multiple categories.

        This fixture-based test ensures skill distribution (LANGUAGE, FRAMEWORK, TOOL, etc.).
        """
        response = client.get("/skills", headers={"X-Debug-User-Id": str(user_talent.id)})

        assert response.status_code == 200
        data = response.json()

        # Verify we have skills from multiple categories
        categories = {item["category"] for item in data["items"]}
        assert "LANGUAGE" in categories, "Should have LANGUAGE category skills"
        assert "FRAMEWORK" in categories, "Should have FRAMEWORK category skills"
        assert "TOOL" in categories, "Should have TOOL category skills"

        # Verify specific skills are seeded
        slugs = {item["slug"] for item in data["items"]}
        assert "python" in slugs
        assert "javascript" in slugs
        assert "react" in slugs
        assert "fastapi" in slugs
        assert "docker" in slugs
