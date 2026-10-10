"""
Authorization tests for the Keşfet directory (PLAN R.1, docs/kesfet-tasarim.md).

GET /discover/talents and GET /discover/organizations are open to every
authenticated, e-mail-verified user, so the boundary under test is not *who*
may call but *what* may come back: only data that is already public.
"""

from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models import OrganizationMember
from tests._discover_data import auth, make_org, make_skill, make_talent, make_user, seal_skill, slugs

TALENT_CARD_FIELDS = {
    "public_slug",
    "full_name",
    "headline",
    "department",
    "city",
    "institution_name",
    "sealed_skills",
    "verified_experience_count",
}
ORGANIZATION_CARD_FIELDS = {"id", "name", "verification_level", "domain"}


@pytest.fixture
def viewer(session):
    """A plain authenticated user: no talent profile, no membership."""
    return make_user(session, "viewer@example.com")


class TestWhoMayCall:
    @pytest.mark.parametrize("path", ["/discover/talents", "/discover/organizations"])
    def test_anonymous_gets_401(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", ["/discover/talents", "/discover/organizations"])
    def test_anonymous_gets_401_before_parameter_validation(self, client, path):
        assert client.get(path, params={"visibility": "PRIVATE", "limit": 999}).status_code == 401

    @pytest.mark.unverified_users
    @pytest.mark.parametrize("path", ["/discover/talents", "/discover/organizations"])
    def test_unverified_email_gets_401(self, client, session, path):
        user = make_user(session, "unverified@example.com")
        response = client.get(path, headers=auth(user))
        assert response.status_code == 401
        assert response.json()["code"] == "EMAIL_NOT_VERIFIED"

    def test_talent_without_membership_may_list_talents(self, client, session):
        make_talent(session, "listed")
        caller = make_talent(session, "caller", visibility="PRIVATE")
        response = client.get("/discover/talents", headers={"X-Debug-User-Id": str(caller.user_id)})
        assert response.status_code == 200
        assert slugs(response) == ["listed-slug"]

    def test_organization_member_may_list_talents(self, client, session):
        make_talent(session, "listed")
        member = make_user(session, "member@example.com")
        org = make_org(session, "Acme")
        session.add(OrganizationMember(organization_id=org.id, user_id=member.id, role="MEMBER", status="ACTIVE"))
        session.flush()
        response = client.get("/discover/talents", headers=auth(member))
        assert response.status_code == 200
        assert slugs(response) == ["listed-slug"]

    @pytest.mark.parametrize("path", ["/discover/talents", "/discover/organizations"])
    def test_feature_off_is_404_even_before_auth(self, client, session, viewer, monkeypatch, path):
        monkeypatch.setattr(settings, "discover_enabled", False)
        assert client.get(path).status_code == 404
        assert client.get(path, headers=auth(viewer)).status_code == 404


class TestOnlyPublicProfilesAreListed:
    @pytest.mark.parametrize("visibility", ["PRIVATE", "INSTITUTION", "ORGANIZATIONS"])
    def test_non_public_profile_is_never_listed(self, client, session, viewer, visibility):
        make_talent(session, "hidden", visibility=visibility)
        make_talent(session, "shown")
        response = client.get("/discover/talents", headers=auth(viewer))
        assert slugs(response) == ["shown-slug"]
        assert "hidden" not in response.text

    def test_non_public_profile_is_not_reachable_by_search(self, client, session, viewer):
        make_talent(session, "hidden", full_name="Gizli Kişi", visibility="ORGANIZATIONS")
        response = client.get("/discover/talents", params={"q": "Gizli"}, headers=auth(viewer))
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_public_profile_without_slug_is_not_listed(self, client, session, viewer):
        make_talent(session, "noslug", with_slug=False)
        assert slugs(client.get("/discover/talents", headers=auth(viewer))) == []

    def test_deleted_profile_is_not_listed(self, client, session, viewer):
        make_talent(session, "gone", deleted_at=datetime.now(timezone.utc))
        assert slugs(client.get("/discover/talents", headers=auth(viewer))) == []

    def test_profile_disappears_as_soon_as_visibility_is_closed(self, client, session, viewer):
        profile = make_talent(session, "flip")
        assert slugs(client.get("/discover/talents", headers=auth(viewer))) == ["flip-slug"]
        profile.visibility = "PRIVATE"
        session.flush()
        assert slugs(client.get("/discover/talents", headers=auth(viewer))) == []


class TestNothingBeyondThePublicProfileLeaks:
    def test_card_is_an_allowlist_without_pii_or_internal_ids(self, client, session, viewer):
        profile = make_talent(session, "alice", headline="Engineer", study_year=3)
        response = client.get("/discover/talents", headers=auth(viewer))
        (card,) = response.json()["items"]
        assert set(card) == TALENT_CARD_FIELDS
        assert "alice@example.com" not in response.text
        assert str(profile.id) not in response.text
        assert str(profile.user_id) not in response.text

    def test_skill_sealed_on_private_experience_is_hidden(self, client, session, viewer):
        talent = make_talent(session, "alice")
        org = make_org(session, "Acme")
        secret = make_skill(session, "secret-skill", "Gizli Yetkinlik")
        seal_skill(session, talent, org, secret, experience_visibility="PRIVATE")

        (card,) = client.get("/discover/talents", headers=auth(viewer)).json()["items"]
        assert card["sealed_skills"] == []
        assert card["verified_experience_count"] == 0

        filtered = client.get("/discover/talents", params={"skill_id": str(secret.id)}, headers=auth(viewer))
        assert filtered.json()["items"] == []

    def test_revoked_attestation_seals_nothing(self, client, session, viewer):
        talent = make_talent(session, "alice")
        org = make_org(session, "Acme")
        skill = make_skill(session, "revoked-skill", "İptal Edilen")
        seal_skill(session, talent, org, skill, revoked=True)

        (card,) = client.get("/discover/talents", headers=auth(viewer)).json()["items"]
        assert card["sealed_skills"] == []
        assert card["verified_experience_count"] == 0

    @pytest.mark.parametrize(
        "param",
        [{"visibility": "PRIVATE"}, {"organization_id": "x"}, {"role": "ADMIN"}, {"include_private": "true"}],
    )
    def test_client_cannot_widen_the_scope(self, client, session, viewer, param):
        make_talent(session, "hidden", visibility="PRIVATE")
        response = client.get("/discover/talents", params=param, headers=auth(viewer))
        assert response.status_code == 422
        assert "hidden" not in response.text


class TestOrganizationDirectory:
    def test_card_is_an_allowlist(self, client, session, viewer):
        make_org(session, "Acme", legal_id="1234567890", domain="acme.example")
        response = client.get("/discover/organizations", headers=auth(viewer))
        (card,) = response.json()["items"]
        assert set(card) == ORGANIZATION_CARD_FIELDS
        assert "1234567890" not in response.text

    def test_unverified_domain_is_not_shown(self, client, session, viewer):
        make_org(session, "Unverified", verification_level="T1", domain="attacker.example")
        make_org(session, "Verified", verification_level="T2", domain="verified.example")
        items = client.get("/discover/organizations", headers=auth(viewer)).json()["items"]
        assert {item["name"]: item["domain"] for item in items} == {
            "Unverified": None,
            "Verified": "verified.example",
        }

    def test_inactive_and_deleted_organizations_are_not_listed(self, client, session, viewer):
        make_org(session, "Active")
        make_org(session, "Suspended", status="SUSPENDED")
        make_org(session, "Deleted", deleted_at=datetime.now(timezone.utc))
        items = client.get("/discover/organizations", headers=auth(viewer)).json()["items"]
        assert [item["name"] for item in items] == ["Active"]

    def test_unknown_parameter_is_rejected(self, client, session, viewer):
        response = client.get("/discover/organizations", params={"status": "SUSPENDED"}, headers=auth(viewer))
        assert response.status_code == 422
