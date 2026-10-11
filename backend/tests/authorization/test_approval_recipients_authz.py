"""
Approval request recipients — who a DRAFT engagement can be sent to for approval.

Attacker matrix for GET /engagements/{id}/approval-recipients (out of scope is
always 404, never 403; every 404 shares one body):

| Caller                                   | DRAFT | PENDING_APPROVAL | DRAFT, no institution |
|------------------------------------------|-------|------------------|-----------------------|
| the student (subject)                    | 200   | 404              | 404                   |
| member of the engagement's organization  | 200   | 404              | 404                   |
| coordinator of the institution           | 404   | 404              | 404                   |
| another student                          | 404   | 404              | 404                   |
| coordinator of another institution       | 404   | 404              | 404                   |
| member of another organization           | 404   | 404              | 404                   |

200 lists the institution's ACTIVE coordinators only (no admins, no other
institution), with a masked e-mail. The ids then go to the transition as
notify_user_ids; ids of anyone else are ignored without an error.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import (
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    Outbox,
    TalentProfile,
    User,
)


def _auth(user: User) -> dict[str, str]:
    return {"X-Debug-User-Id": str(user.id)}


def _user(session, email: str, full_name: str, status: str = "ACTIVE") -> User:
    user = User(email=email, password_hash="x", status=status)
    session.add(user)
    session.flush()
    session.add(TalentProfile(user_id=user.id, full_name=full_name))
    session.flush()
    return user


def _institution(session, name: str) -> Institution:
    inst = Institution(name=name, verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


def _org(session, name: str) -> Organization:
    org = Organization(name=name, verification_level="T1", status="ACTIVE")
    session.add(org)
    session.flush()
    return org


def _engagement(
    session, talent: User, org: Organization, inst: Institution | None, status="DRAFT"
) -> Engagement:
    profile = session.query(TalentProfile).filter_by(user_id=talent.id).one()
    engagement = Engagement(
        talent_id=profile.id,
        organization_id=org.id,
        institution_id=inst.id if inst else None,
        kind="INTERNSHIP",
        title="Staj",
        status=status,
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def world(session):
    inst = _institution(session, "Çınaraltı Üniversitesi")
    other_inst = _institution(session, "Başka Üniversite")
    org = _org(session, "Yelkovan Yazılım")
    other_org = _org(session, "Başka Kuruluş")

    student = _user(session, "ayse@posta.example", "Ayşe Öğrenci")
    session.query(TalentProfile).filter_by(user_id=student.id).one().institution_id = inst.id
    other_student = _user(session, "ali@posta.example", "Ali Öğrenci")
    kerem = _user(session, "kerem.taskin@cinaralti.example", "Kerem Taşkın")
    nermin = _user(session, "nermin@cinaralti.example", "Nermin Başaran")
    inst_admin = _user(session, "admin@cinaralti.example", "Kurum Yönetici")
    suspended = _user(session, "susp@cinaralti.example", "Askıda Koordinatör", status="SUSPENDED")
    deleted = _user(session, "del@cinaralti.example", "Silinen Koordinatör")
    deleted.deleted_at = datetime.now(timezone.utc)
    foreign_coord = _user(session, "fiona@baska.example", "Fiona Koordinatör")
    org_member = _user(session, "mehmet@yelkovan.example", "Mehmet Karaca")
    other_org_member = _user(session, "berk@baska.example", "Berk Üye")

    for user in (kerem, nermin, suspended, deleted):
        session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="COORDINATOR"))
    session.add(InstitutionMember(institution_id=inst.id, user_id=inst_admin.id, role="ADMIN"))
    session.add(
        InstitutionMember(
            institution_id=other_inst.id, user_id=foreign_coord.id, role="COORDINATOR"
        )
    )
    session.add(
        OrganizationMember(
            organization_id=org.id, user_id=org_member.id, role="MEMBER", status="ACTIVE"
        )
    )
    session.add(
        OrganizationMember(
            organization_id=other_org.id,
            user_id=other_org_member.id,
            role="MEMBER",
            status="ACTIVE",
        )
    )
    session.flush()

    return {
        "inst": inst,
        "org": org,
        "student": student,
        "other_student": other_student,
        "kerem": kerem,
        "nermin": nermin,
        "inst_admin": inst_admin,
        "foreign_coord": foreign_coord,
        "org_member": org_member,
        "other_org_member": other_org_member,
        "draft": _engagement(session, student, org, inst),
    }


def _get(client, engagement_id, user):
    return client.get(f"/engagements/{engagement_id}/approval-recipients", headers=_auth(user))


def _assert_not_found(response) -> None:
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "NOT_FOUND"


class TestApprovalRecipientsList:
    @pytest.mark.parametrize("actor", ["student", "org_member"])
    def test_sender_sees_only_the_institutions_active_coordinators_masked(
        self, client, world, actor
    ):
        response = _get(client, world["draft"].id, world[actor])

        assert response.status_code == 200, response.text
        rows = response.json()
        assert all(set(row) == {"user_id", "display_name", "email_hint"} for row in rows)
        assert [(row["display_name"], row["email_hint"]) for row in rows] == [
            ("Kerem Taşkın", "ke•••@cinaralti.example"),
            ("Nermin Başaran", "ne•••@cinaralti.example"),
        ]
        assert "kerem.taskin@" not in response.text
        assert "Fiona" not in response.text
        assert "Kurum Yönetici" not in response.text

    @pytest.mark.parametrize(
        "actor", ["kerem", "inst_admin", "other_student", "foreign_coord", "other_org_member"]
    )
    def test_anyone_who_cannot_send_it_gets_404(self, client, world, actor):
        _assert_not_found(_get(client, world["draft"].id, world[actor]))

    @pytest.mark.parametrize("actor", ["student", "org_member"])
    def test_not_draft_or_without_institution_is_404(self, client, session, world, actor):
        pending = _engagement(
            session, world["student"], world["org"], world["inst"], status="PENDING_APPROVAL"
        )
        no_institution = _engagement(session, world["student"], world["org"], None)

        bodies = []
        for engagement_id in (pending.id, no_institution.id, uuid.uuid4()):
            response = _get(client, engagement_id, world[actor])
            _assert_not_found(response)
            body = response.json()
            body.pop("request_id", None)
            bodies.append(body)
        assert bodies[0] == bodies[1] == bodies[2]

    def test_unauthenticated_401(self, client, world):
        response = client.get(f"/engagements/{world['draft'].id}/approval-recipients")
        assert response.status_code == 401


class TestNotifyUserIds:
    def _send(self, client, world, body):
        return client.post(
            f"/engagements/{world['draft'].id}/transitions",
            json={"to_status": "PENDING_APPROVAL", "version": 1, **body},
            headers=_auth(world["student"]),
        )

    def _payload(self, session):
        return session.query(Outbox).filter_by(topic="engagement.pending_approval").one().payload

    def test_picked_coordinator_alone_receives_the_request(self, client, session, world):
        response = self._send(client, world, {"notify_user_ids": [str(world["nermin"].id)]})

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "PENDING_APPROVAL"
        assert self._payload(session)["notify_user_ids"] == [str(world["nermin"].id)]

    @pytest.mark.parametrize(
        "actor", ["org_member", "foreign_coord", "inst_admin", "other_student"]
    )
    def test_id_of_anyone_but_the_institutions_coordinators_is_ignored(
        self, client, session, world, actor
    ):
        response = self._send(
            client, world, {"notify_user_ids": [str(world[actor].id), str(uuid.uuid4())]}
        )

        # Same answer as a matching id: no membership oracle; every coordinator is notified.
        assert response.status_code == 200, response.text
        assert "notify_user_ids" not in self._payload(session)

    @pytest.mark.parametrize("body", [{}, {"notify_user_ids": []}, {"notify_user_ids": None}])
    def test_without_a_pick_every_coordinator_is_notified(self, client, session, world, body):
        response = self._send(client, world, body)

        assert response.status_code == 200, response.text
        assert "notify_user_ids" not in self._payload(session)

    def test_more_than_five_ids_is_rejected_and_nothing_changes(self, client, session, world):
        response = self._send(
            client, world, {"notify_user_ids": [str(uuid.uuid4()) for _ in range(6)]}
        )

        assert response.status_code in (400, 422), response.text
        session.refresh(world["draft"])
        assert world["draft"].status == "DRAFT"
        assert session.query(Outbox).filter_by(topic="engagement.pending_approval").count() == 0


# ============================================================================
# GET /engagements/approval-recipients — the caller's own school, before the
# engagement exists ("Yeni çalışma" sends it for approval right after creating).
# Student with a school → 200; no school, no talent profile → 404.
# ============================================================================


class TestOwnSchoolRecipients:
    def test_student_sees_own_schools_active_coordinators_masked(self, client, world):
        response = client.get("/engagements/approval-recipients", headers=_auth(world["student"]))

        assert response.status_code == 200, response.text
        assert [(row["display_name"], row["email_hint"]) for row in response.json()] == [
            ("Kerem Taşkın", "ke•••@cinaralti.example"),
            ("Nermin Başaran", "ne•••@cinaralti.example"),
        ]
        assert "kerem.taskin@" not in response.text
        assert "Fiona" not in response.text

    @pytest.mark.parametrize("actor", ["other_student", "org_member", "foreign_coord"])
    def test_without_a_school_of_ones_own_is_404(self, client, world, actor):
        # other_student has no school; org_member/foreign_coord have a profile but no school
        # (a coordinator's membership is not their own school as a student).
        _assert_not_found(
            client.get("/engagements/approval-recipients", headers=_auth(world[actor]))
        )

    def test_unauthenticated_401(self, client):
        assert client.get("/engagements/approval-recipients").status_code == 401


# ============================================================================
# POST /engagements — internships and capstones keep the student's school
# ============================================================================


class TestSchoolBoundKinds:
    @pytest.mark.parametrize(
        ("kind", "attached"),
        [("INTERNSHIP", True), ("CAPSTONE", True), ("PART_TIME", False), ("SHORT_PROJECT", False)],
    )
    def test_school_is_attached_to_internships_even_if_omitted(
        self, client, session, world, kind, attached
    ):
        profile = session.query(TalentProfile).filter_by(user_id=world["student"].id).one()

        response = client.post(
            "/engagements",
            json={
                "talent_id": str(profile.id),
                "organization_id": str(world["org"].id),
                "kind": kind,
                "title": "İş",
            },
            headers=_auth(world["student"]),
        )

        assert response.status_code == 201, response.text
        assert response.json()["institution_id"] == (str(world["inst"].id) if attached else None)

    def test_internship_cannot_skip_the_school_to_self_activate(self, client, session, world):
        profile = session.query(TalentProfile).filter_by(user_id=world["student"].id).one()
        created = client.post(
            "/engagements",
            json={
                "talent_id": str(profile.id),
                "organization_id": str(world["org"].id),
                "kind": "INTERNSHIP",
                "title": "Staj",
            },
            headers=_auth(world["student"]),
        ).json()

        response = client.post(
            f"/engagements/{created['id']}/transitions",
            json={"to_status": "ACTIVE", "version": created["version"]},
            headers=_auth(world["student"]),
        )

        assert response.status_code in (403, 404, 422), response.text
        session.refresh(session.get(Engagement, uuid.UUID(created["id"])))
        assert session.get(Engagement, uuid.UUID(created["id"])).status == "DRAFT"

    def test_part_time_without_school_starts_right_away(self, client, session, world):
        profile = session.query(TalentProfile).filter_by(user_id=world["student"].id).one()
        created = client.post(
            "/engagements",
            json={
                "talent_id": str(profile.id),
                "organization_id": str(world["org"].id),
                "kind": "PART_TIME",
                "title": "Kafe",
            },
            headers=_auth(world["student"]),
        ).json()

        response = client.post(
            f"/engagements/{created['id']}/transitions",
            json={"to_status": "ACTIVE", "version": created["version"]},
            headers=_auth(world["student"]),
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ACTIVE"
