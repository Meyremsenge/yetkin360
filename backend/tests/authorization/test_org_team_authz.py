"""
SPRINT D2 — team list, unit labels, approver picker, showcase switch.

Attacker matrix (every out-of-scope case is 404, never 403):

| Endpoint                                   | outsider | MEMBER        | ADMIN of other org | ADMIN        |
|--------------------------------------------|----------|---------------|--------------------|--------------|
| GET   /organizations/{id}/members          | 404      | 200, no email | 404                | 200 + email  |
| PATCH /organizations/{id}/members/{uid}    | 404      | 404           | 404                | 200          |
| PATCH /organizations/{id} showcase_public  | 404      | 404           | 404                | 200          |
| GET   /organizations/{id}/approvers        | 200      | 200           | 200                | 200          |

Approvers is deliberately cross-tenant (a student picks an approver before any
membership exists) and therefore thin: name + unit only; missing, deleted and
non-ACTIVE organizations share one 404 body; rate-limited like Keşfet.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models import (
    AuditEvent,
    Engagement,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)
from app.services import rate_limit


def _auth(user: User) -> dict[str, str]:
    return {"X-Debug-User-Id": str(user.id)}


def _user(session, email: str, full_name: str | None, status: str = "ACTIVE") -> User:
    user = User(email=email, password_hash="x", status=status)
    session.add(user)
    session.flush()
    if full_name is not None:
        session.add(TalentProfile(user_id=user.id, full_name=full_name))
        session.flush()
    return user


def _org(session, name: str, **fields) -> Organization:
    org = Organization(name=name, verification_level="T1", status="ACTIVE", **fields)
    session.add(org)
    session.flush()
    return org


def _member(session, org, user, role="MEMBER", unit=None, status="ACTIVE") -> OrganizationMember:
    member = OrganizationMember(
        organization_id=org.id, user_id=user.id, role=role, unit=unit, status=status
    )
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def world(session):
    org_a = _org(session, "Lale Yazılım")
    org_b = _org(session, "Başka Kuruluş")
    admin_a = _user(session, "admin-a@lale.example", "Ayla Yönetici")
    member_a = _user(session, "member-a@lale.example", "Mehmet Kaya")
    admin_b = _user(session, "admin-b@baska.example", "Bora Yönetici")
    member_b = _user(session, "member-b@baska.example", "Berk Üye")
    outsider = _user(session, "student@uni.example", "Selin Öğrenci")
    _member(session, org_a, admin_a, role="ADMIN")
    _member(session, org_a, member_a, unit="Yazılım")
    _member(session, org_b, admin_b, role="ADMIN")
    _member(session, org_b, member_b)
    return {
        "org_a": org_a,
        "org_b": org_b,
        "admin_a": admin_a,
        "member_a": member_a,
        "admin_b": admin_b,
        "member_b": member_b,
        "outsider": outsider,
    }


def _assert_not_found(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "NOT_FOUND"


# ============================================================================
# GET /organizations/{id}/members
# ============================================================================


class TestListMembers:
    def test_admin_sees_members_with_emails(self, client, world):
        response = client.get(f"/organizations/{world['org_a'].id}/members", headers=_auth(world["admin_a"]))
        assert response.status_code == 200
        rows = {row["user_id"]: row for row in response.json()}
        assert set(rows) == {str(world["admin_a"].id), str(world["member_a"].id)}
        member = rows[str(world["member_a"].id)]
        assert member == {
            "user_id": str(world["member_a"].id),
            "display_name": "Mehmet Kaya",
            "role": "MEMBER",
            "unit": "Yazılım",
            "open_assigned_count": 0,
            "email": "member-a@lale.example",
        }

    def test_member_sees_team_without_emails(self, client, world):
        response = client.get(f"/organizations/{world['org_a'].id}/members", headers=_auth(world["member_a"]))
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(row["email"] is None for row in response.json())
        assert "lale.example" not in response.text

    @pytest.mark.parametrize("actor", ["outsider", "admin_b", "member_b"])
    def test_non_member_gets_404(self, client, world, actor):
        response = client.get(f"/organizations/{world['org_a'].id}/members", headers=_auth(world[actor]))
        _assert_not_found(response)
        assert "Mehmet" not in response.text

    def test_unknown_org_same_404(self, client, world):
        _assert_not_found(client.get(f"/organizations/{uuid.uuid4()}/members", headers=_auth(world["admin_a"])))

    def test_unauthenticated_401(self, client, world):
        assert client.get(f"/organizations/{world['org_a'].id}/members").status_code == 401

    def test_open_assigned_count_counts_open_engagements_in_this_org_only(self, client, session, world):
        talent = session.execute(
            select(TalentProfile).where(TalentProfile.user_id == world["outsider"].id)
        ).scalar_one()

        def engagement(org, status):
            session.add(
                Engagement(
                    talent_id=talent.id,
                    organization_id=org.id,
                    kind="INTERNSHIP",
                    title=f"{status} işi",
                    status=status,
                    version=1,
                    supervisor_user_id=world["member_a"].id,
                )
            )

        for status in ("ACTIVE", "PENDING_EVALUATION", "EVALUATED", "DRAFT", "VERIFIED", "CANCELLED"):
            engagement(world["org_a"], status)
        engagement(world["org_b"], "ACTIVE")  # another org's work does not count here
        session.flush()

        response = client.get(f"/organizations/{world['org_a'].id}/members", headers=_auth(world["admin_a"]))
        counts = {row["user_id"]: row["open_assigned_count"] for row in response.json()}
        assert counts[str(world["member_a"].id)] == 3
        assert counts[str(world["admin_a"].id)] == 0

    def test_deleted_user_is_not_listed(self, client, session, world):
        world["member_a"].deleted_at = datetime.now(timezone.utc)
        session.flush()
        response = client.get(f"/organizations/{world['org_a'].id}/members", headers=_auth(world["admin_a"]))
        assert [row["user_id"] for row in response.json()] == [str(world["admin_a"].id)]


# ============================================================================
# PATCH /organizations/{id}/members/{user_id}
# ============================================================================


class TestUpdateMemberUnit:
    def _patch(self, client, org, user_id, actor, unit):
        return client.patch(
            f"/organizations/{org.id}/members/{user_id}", json={"unit": unit}, headers=_auth(actor)
        )

    def test_admin_sets_and_clears_unit(self, client, session, world):
        response = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], "  Satış  ")
        assert response.status_code == 200
        assert response.json()["unit"] == "Satış"
        assert response.json()["email"] == "member-a@lale.example"

        response = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], None)
        assert response.status_code == 200
        assert response.json()["unit"] is None

        response = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], "   ")
        assert response.json()["unit"] is None

        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "ORG_MEMBER_UNIT_CHANGED")
        ).scalars().all()
        assert len(events) == 2  # the blank → null call changed nothing
        for event in events:
            assert set(event.event_metadata) == {"member_user_id", "cleared"}
            assert "lale.example" not in str(event.event_metadata)

    def test_unit_change_shows_in_approvers(self, client, world):
        self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], "Ar-Ge")
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(world["outsider"]))
        units = {row["user_id"]: row["unit"] for row in response.json()}
        assert units[str(world["member_a"].id)] == "Ar-Ge"

    def test_member_cannot_change_unit(self, client, world):
        _assert_not_found(self._patch(client, world["org_a"], world["member_a"].id, world["member_a"], "X"))

    def test_outsider_cannot_change_unit(self, client, world):
        _assert_not_found(self._patch(client, world["org_a"], world["member_a"].id, world["outsider"], "X"))

    def test_other_org_admin_cannot_change_unit_via_either_path(self, client, world):
        # B's admin against A's org...
        _assert_not_found(self._patch(client, world["org_a"], world["member_a"].id, world["admin_b"], "X"))
        # ...and A's admin against B's member through A's own org id
        _assert_not_found(self._patch(client, world["org_a"], world["member_b"].id, world["admin_a"], "X"))
        # ...and A's admin against B's org directly
        _assert_not_found(self._patch(client, world["org_b"], world["member_b"].id, world["admin_a"], "X"))

    def test_unknown_member_404(self, client, world):
        _assert_not_found(self._patch(client, world["org_a"], uuid.uuid4(), world["admin_a"], "X"))

    def test_61_characters_is_422(self, client, world):
        response = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], "x" * 61)
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_UNIT"
        ok = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], "x" * 60)
        assert ok.status_code == 200

    def test_markup_is_stored_verbatim(self, client, world):
        markup = "<script>alert(1)</script>"
        response = self._patch(client, world["org_a"], world["member_a"].id, world["admin_a"], markup)
        assert response.status_code == 200
        assert response.json()["unit"] == markup

    def test_missing_unit_key_is_422(self, client, world):
        response = client.patch(
            f"/organizations/{world['org_a'].id}/members/{world['member_a'].id}",
            json={},
            headers=_auth(world["admin_a"]),
        )
        assert response.status_code == 422

    def test_role_in_body_is_ignored(self, client, session, world):
        client.patch(
            f"/organizations/{world['org_a'].id}/members/{world['member_a'].id}",
            json={"unit": "X", "role": "ADMIN"},
            headers=_auth(world["admin_a"]),
        )
        role = session.execute(
            select(OrganizationMember.role).where(OrganizationMember.user_id == world["member_a"].id)
        ).scalar_one()
        assert role == "MEMBER"


# ============================================================================
# POST /organizations/{id}/members with unit
# ============================================================================


class TestInviteWithUnit:
    def test_invite_stores_unit(self, client, session, world):
        newcomer = _user(session, "new@lale.example", "Yeni Kişi")
        response = client.post(
            f"/organizations/{world['org_a'].id}/members",
            json={"email": newcomer.email, "role": "MEMBER", "unit": " Destek "},
            headers=_auth(world["admin_a"]),
        )
        assert response.status_code == 202
        unit = session.execute(
            select(OrganizationMember.unit).where(OrganizationMember.user_id == newcomer.id)
        ).scalar_one()
        assert unit == "Destek"

    def test_invite_without_unit_still_works(self, client, session, world):
        newcomer = _user(session, "new2@lale.example", "Yeni İki")
        response = client.post(
            f"/organizations/{world['org_a'].id}/members",
            json={"email": newcomer.email, "role": "MEMBER"},
            headers=_auth(world["admin_a"]),
        )
        assert response.status_code == 202

    def test_invite_long_unit_422(self, client, session, world):
        newcomer = _user(session, "new3@lale.example", "Yeni Üç")
        response = client.post(
            f"/organizations/{world['org_a'].id}/members",
            json={"email": newcomer.email, "role": "MEMBER", "unit": "y" * 61},
            headers=_auth(world["admin_a"]),
        )
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_UNIT"

    def test_member_invite_with_unit_still_404(self, client, session, world):
        newcomer = _user(session, "new4@lale.example", "Yeni Dört")
        response = client.post(
            f"/organizations/{world['org_a'].id}/members",
            json={"email": newcomer.email, "role": "MEMBER", "unit": "y" * 61},
            headers=_auth(world["member_a"]),
        )
        _assert_not_found(response)


# ============================================================================
# GET /organizations/{id}/approvers
# ============================================================================


class TestApprovers:
    @pytest.mark.parametrize("actor", ["outsider", "member_a", "admin_b"])
    def test_any_verified_user_lists_name_unit_and_masked_email_only(self, client, world, actor):
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(world[actor]))
        assert response.status_code == 200
        rows = response.json()
        assert all(set(row) == {"user_id", "display_name", "unit", "email_hint"} for row in rows)
        assert {row["email_hint"] for row in rows} == {"ad•••@lale.example", "me•••@lale.example"}
        assert "admin-a@" not in response.text
        assert "member-a@" not in response.text
        assert "ADMIN" not in response.text

    @pytest.mark.parametrize(
        ("email", "hint"),
        [("ik@acme.example", "i•••@acme.example"), ("a@acme.example", "•••@acme.example")],
    )
    def test_short_local_part_is_never_shown_whole(self, client, session, world, email, hint):
        _member(session, world["org_a"], _user(session, email, "Kısa Adres"))
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(world["outsider"]))
        row = next(row for row in response.json() if row["display_name"] == "Kısa Adres")
        assert row["email_hint"] == hint

    def test_order_is_unit_then_name_with_no_unit_last(self, client, session, world):
        zeynep = _user(session, "z@lale.example", "Zeynep Ar")
        ali = _user(session, "ali@lale.example", "Ali Ar")
        _member(session, world["org_a"], zeynep, unit="Ar-Ge")
        _member(session, world["org_a"], ali, unit="Ar-Ge")
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(world["outsider"]))
        assert [(row["display_name"], row["unit"]) for row in response.json()] == [
            ("Ali Ar", "Ar-Ge"),
            ("Zeynep Ar", "Ar-Ge"),
            ("Mehmet Kaya", "Yazılım"),
            ("Ayla Yönetici", None),
        ]

    def test_inactive_members_and_users_are_hidden(self, client, session, world):
        suspended = _user(session, "susp@lale.example", "Askıda Kişi", status="SUSPENDED")
        left = _user(session, "left@lale.example", "Ayrılan Kişi")
        deleted = _user(session, "del@lale.example", "Silinen Kişi")
        deleted.deleted_at = datetime.now(timezone.utc)
        _member(session, world["org_a"], suspended)
        _member(session, world["org_a"], left, status="REMOVED")
        _member(session, world["org_a"], deleted)
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(world["outsider"]))
        names = {row["display_name"] for row in response.json()}
        assert names == {"Ayla Yönetici", "Mehmet Kaya"}

    def test_missing_deleted_and_inactive_orgs_share_one_404(self, client, session, world):
        deleted = _org(session, "Silinmiş", deleted_at=datetime.now(timezone.utc))
        inactive = _org(session, "Askıda")
        inactive.status = "SUSPENDED"
        _member(session, deleted, _user(session, "x@del.example", "Gizli Ad"))
        session.flush()
        bodies = []
        for org_id in (uuid.uuid4(), deleted.id, inactive.id):
            response = client.get(f"/organizations/{org_id}/approvers", headers=_auth(world["outsider"]))
            _assert_not_found(response)
            body = response.json()
            body.pop("request_id", None)
            bodies.append(body)
        assert bodies[0] == bodies[1] == bodies[2]
        assert "Gizli" not in str(bodies)

    def test_unauthenticated_401(self, client, world):
        assert client.get(f"/organizations/{world['org_a'].id}/approvers").status_code == 401

    @pytest.mark.unverified_users
    def test_unverified_email_401(self, client, session, world):
        fresh = _user(session, "fresh@uni.example", "Taze Kullanıcı")
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=_auth(fresh))
        assert response.status_code == 401
        assert response.json()["code"] == "EMAIL_NOT_VERIFIED"

    @pytest.mark.rate_limited
    def test_rate_limit_shared_with_discover_and_counts_404_probes(self, client, world, monkeypatch):
        monkeypatch.setattr(rate_limit, "DISCOVER_USER", rate_limit.Rule("discover_user", 2, 60))
        headers = _auth(world["outsider"])
        assert client.get("/discover/organizations", headers=headers).status_code == 200
        _assert_not_found(client.get(f"/organizations/{uuid.uuid4()}/approvers", headers=headers))
        response = client.get(f"/organizations/{world['org_a'].id}/approvers", headers=headers)
        assert response.status_code == 429
        assert response.json()["code"] == "RATE_LIMITED"
        assert int(response.headers["Retry-After"]) >= 1
        assert "Mehmet" not in response.text


# ============================================================================
# PATCH /organizations/{id} — showcase_public
# ============================================================================


class TestShowcaseSwitch:
    def _patch(self, client, org, actor, body):
        return client.patch(f"/organizations/{org.id}", json=body, headers=_auth(actor))

    def test_admin_opens_and_closes_showcase(self, client, session, world):
        response = self._patch(client, world["org_a"], world["admin_a"], {"showcase_public": True})
        assert response.status_code == 200
        assert response.json()["showcase_public"] is True
        response = self._patch(client, world["org_a"], world["admin_a"], {"showcase_public": False})
        assert response.json()["showcase_public"] is False
        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "ORGANIZATION_SHOWCASE_CHANGED")
        ).scalars().all()
        assert [event.event_metadata for event in events] == [
            {"showcase_public": True},
            {"showcase_public": False},
        ]

    def test_same_value_is_noop_without_audit(self, client, session, world):
        response = self._patch(client, world["org_a"], world["admin_a"], {"showcase_public": False})
        assert response.status_code == 200
        assert not session.execute(
            select(AuditEvent).where(AuditEvent.action == "ORGANIZATION_SHOWCASE_CHANGED")
        ).first()

    @pytest.mark.parametrize("actor", ["member_a", "outsider", "admin_b"])
    def test_non_admin_cannot_switch(self, client, session, world, actor):
        _assert_not_found(self._patch(client, world["org_a"], world[actor], {"showcase_public": True}))
        session.refresh(world["org_a"])
        assert world["org_a"].showcase_public is False

    def test_empty_body_is_422(self, client, world):
        assert self._patch(client, world["org_a"], world["admin_a"], {}).status_code == 422

    def test_get_organization_returns_showcase_flag(self, client, world):
        response = client.get(f"/organizations/{world['org_a'].id}", headers=_auth(world["member_a"]))
        assert response.json()["showcase_public"] is False

    def test_failed_domain_change_does_not_switch_showcase(self, client, session, world):
        response = self._patch(
            client, world["org_a"], world["admin_a"], {"domain": "gmail.com", "showcase_public": True}
        )
        assert response.status_code == 400
        session.expire_all()
        assert session.get(Organization, world["org_a"].id).showcase_public is False
