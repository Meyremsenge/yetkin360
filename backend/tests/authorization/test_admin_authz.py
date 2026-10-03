"""
Admin authorization tests (PLAN 3.6 — YET-110/136/137/138/139).

Threat-model security tests for /admin/*:
- YET-139: sadece ADMIN rolü erişebilir — non-admin principal'lar (TALENT,
  ORG_ADMIN, anonymous) her /admin/* uçtan 404 alır (403 değil — CLAUDE.md:
  403 ucun/kaynağın varlığını sızdırır), app/api/organizations.py'deki
  ORG:ADMIN kontrolüyle aynı desen.
- Pozitif senaryolar: platform admin kuyruğu görebilir, kurum seviyesini
  güncelleyebilir, skill CRUD yapabilir.
- Her admin aksiyonu audit_events üretir (docs/DOMAIN.md §3.4).
"""

import uuid

import pytest

from app.models import AuditEvent, Organization, Skill, User


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def platform_admin(session):
    user = User(email="platform-admin@example.com", password_hash="hash_admin", is_platform_admin=True)
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def non_admin_talent(session):
    user = User(email="non-admin-talent@example.com", password_hash="hash_talent")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_pending_t3(session):
    """T2 org with legal_id — appears in the verification queue."""
    org = Organization(
        name="Pending T3 A.Ş.",
        legal_id="PENDING-T3-001",
        domain="pending-t3.example.com",
        verification_level="T2",
    )
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def org_t1_no_legal_id(session):
    """T1 org without legal_id — must NOT appear in the queue."""
    org = Organization(name="Yeni Kurum", verification_level="T1")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def sample_skill(session):
    skill = Skill(slug="rust-authz-test", name_tr="Rust", category="LANGUAGE")
    session.add(skill)
    session.flush()
    return skill


# ============================================================================
# YET-139: yalnız ADMIN erişebilir (negatif senaryolar)
# ============================================================================


class TestAdminOnlyAccess:
    def test_non_admin_cannot_read_verification_queue_404(self, client, non_admin_talent):
        response = client.get(
            "/admin/verification-queue",
            headers={"X-Debug-User-Id": str(non_admin_talent.id)},
        )
        assert response.status_code == 404, response.text

    def test_non_admin_cannot_set_verification_level_404(self, client, non_admin_talent, org_pending_t3):
        response = client.post(
            f"/admin/organizations/{org_pending_t3.id}/verification-level",
            headers={"X-Debug-User-Id": str(non_admin_talent.id)},
            json={"verification_level": "T3"},
        )
        assert response.status_code == 404, response.text

    def test_non_admin_cannot_list_skills_404(self, client, non_admin_talent):
        response = client.get(
            "/admin/skills",
            headers={"X-Debug-User-Id": str(non_admin_talent.id)},
        )
        assert response.status_code == 404, response.text

    def test_non_admin_cannot_create_skill_404(self, client, non_admin_talent):
        response = client.post(
            "/admin/skills",
            headers={"X-Debug-User-Id": str(non_admin_talent.id)},
            json={"slug": "should-not-exist", "name_tr": "Olmamalı", "category": "TOOL"},
        )
        assert response.status_code == 404, response.text

    def test_non_admin_cannot_deprecate_skill_404(self, client, non_admin_talent, sample_skill):
        response = client.post(
            f"/admin/skills/{sample_skill.id}/deprecate",
            headers={"X-Debug-User-Id": str(non_admin_talent.id)},
        )
        assert response.status_code == 404, response.text

    def test_anonymous_gets_401_not_404(self, client):
        """No X-Debug-User-Id at all → 401 at the auth layer, before the admin gate."""
        response = client.get("/admin/verification-queue")
        assert response.status_code == 401, response.text


# ============================================================================
# Pozitif senaryolar: kurum doğrulama kuyruğu
# ============================================================================


class TestVerificationQueue:
    def test_admin_sees_only_t2_with_legal_id(
        self, client, platform_admin, org_pending_t3, org_t1_no_legal_id
    ):
        response = client.get(
            "/admin/verification-queue",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["items"]}
        assert str(org_pending_t3.id) in ids
        assert str(org_t1_no_legal_id.id) not in ids

    def test_admin_approves_verification_level_and_audit_logged(
        self, client, session, platform_admin, org_pending_t3
    ):
        response = client.post(
            f"/admin/organizations/{org_pending_t3.id}/verification-level",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"verification_level": "T3", "note": "MERSİS doğrulandı"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["verification_level"] == "T3"

        session.refresh(org_pending_t3)
        assert org_pending_t3.verification_level == "T3"
        assert org_pending_t3.verified_by_user_id == platform_admin.id

        event = (
            session.query(AuditEvent)
            .filter_by(action="ADMIN_SET_VERIFICATION_LEVEL", subject_id=org_pending_t3.id)
            .first()
        )
        assert event is not None

    def test_admin_verification_level_nonexistent_org_404(self, client, platform_admin):
        response = client.post(
            f"/admin/organizations/{uuid.uuid4()}/verification-level",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"verification_level": "T3"},
        )
        assert response.status_code == 404, response.text


# ============================================================================
# Pozitif senaryolar: skill CRUD
# ============================================================================


class TestSkillManagement:
    def test_admin_lists_all_skills_including_non_active(
        self, client, session, platform_admin, sample_skill
    ):
        from app.services.skill import deprecate_skill

        deprecate_skill(session, sample_skill.id)
        session.commit()

        response = client.get(
            "/admin/skills",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
        )
        assert response.status_code == 200, response.text
        slugs = [s["slug"] for s in response.json()["items"]]
        assert sample_skill.slug in slugs

    def test_admin_creates_skill(self, client, platform_admin):
        response = client.post(
            "/admin/skills",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"slug": "elixir-authz-test", "name_tr": "Elixir", "category": "LANGUAGE"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["slug"] == "elixir-authz-test"

    def test_admin_duplicate_slug_409(self, client, platform_admin, sample_skill):
        response = client.post(
            "/admin/skills",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"slug": sample_skill.slug, "name_tr": "Yinelenen", "category": "TOOL"},
        )
        assert response.status_code == 409, response.text

    def test_admin_updates_skill(self, client, platform_admin, sample_skill):
        response = client.patch(
            f"/admin/skills/{sample_skill.id}",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"name_tr": "Rust (güncellendi)"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["name_tr"] == "Rust (güncellendi)"

    def test_admin_deprecates_skill(self, client, platform_admin, sample_skill):
        response = client.post(
            f"/admin/skills/{sample_skill.id}/deprecate",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "DEPRECATED"

    def test_admin_merges_skill_into_active_target(self, client, session, platform_admin, sample_skill):
        target = Skill(slug="rustlang-authz-test", name_tr="Rust Lang", category="LANGUAGE")
        session.add(target)
        session.flush()

        response = client.post(
            f"/admin/skills/{sample_skill.id}/merge",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"merged_into_id": str(target.id)},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "MERGED"
        assert body["merged_into_id"] == str(target.id)

    def test_admin_cannot_merge_skill_into_itself_422(self, client, platform_admin, sample_skill):
        response = client.post(
            f"/admin/skills/{sample_skill.id}/merge",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"merged_into_id": str(sample_skill.id)},
        )
        assert response.status_code == 422, response.text

    def test_admin_cannot_merge_into_nonexistent_target_422(self, client, platform_admin, sample_skill):
        response = client.post(
            f"/admin/skills/{sample_skill.id}/merge",
            headers={"X-Debug-User-Id": str(platform_admin.id)},
            json={"merged_into_id": str(uuid.uuid4())},
        )
        assert response.status_code == 422, response.text


# ============================================================================
# YET-231: limit/offset sınırları
# ============================================================================


class TestPaginationBounds:
    @pytest.mark.parametrize("path", ["/admin/verification-queue", "/admin/skills"])
    @pytest.mark.parametrize(
        "query", ["limit=1000000", "limit=201", "limit=0", "limit=-1", "offset=-1"]
    )
    def test_out_of_range_pagination_422(self, client, platform_admin, path, query):
        response = client.get(
            f"{path}?{query}", headers={"X-Debug-User-Id": str(platform_admin.id)}
        )
        assert response.status_code == 422, response.text

    @pytest.mark.parametrize("path", ["/admin/verification-queue", "/admin/skills"])
    def test_max_limit_accepted(self, client, platform_admin, path):
        response = client.get(
            f"{path}?limit=200&offset=0", headers={"X-Debug-User-Id": str(platform_admin.id)}
        )
        assert response.status_code == 200, response.text
