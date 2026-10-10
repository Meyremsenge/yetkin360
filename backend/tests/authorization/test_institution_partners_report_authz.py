"""
GET /institutions/{id}/partners, GET /institutions/{id}/report.csv and the enriched
dashboard (authorization + export safety).

Who may call: members of THE institution (COORDINATOR, ADMIN). Everyone else -> 404
(another institution's coordinator, a student, an organization member, unknown id);
unauthenticated -> 401.
Scope: linked (approved) and non-PRIVATE students only; only this institution's
engagements. CSV cells that start with a formula character are neutralised.
"""

import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models import (
    AuditEvent,
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
    VerifiedExperience,
)


def _user(session, email: str) -> User:
    user = User(email=email, password_hash="hash")
    session.add(user)
    session.flush()
    return user


def _institution(session, name: str) -> Institution:
    inst = Institution(name=name, verification_level="T1", status="ACTIVE")
    session.add(inst)
    session.flush()
    return inst


def _member(session, institution: Institution, email: str, role: str) -> User:
    user = _user(session, email)
    session.add(InstitutionMember(institution_id=institution.id, user_id=user.id, role=role))
    session.flush()
    return user


def _student(session, email, full_name, institution, visibility) -> TalentProfile:
    user = _user(session, email)
    profile = TalentProfile(
        user_id=user.id,
        full_name=full_name,
        department="Bilgisayar Mühendisliği",
        study_year=3,
        visibility=visibility,
        institution_id=institution.id if institution else None,
    )
    session.add(profile)
    session.flush()
    return profile


def _org(session, name: str) -> Organization:
    org = Organization(name=name, legal_id=f"ORG-{uuid.uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _engagement(session, talent, org, institution, status, title="Staj", kind="INTERNSHIP"):
    eng = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        institution_id=institution.id if institution else None,
        kind=kind,
        title=title,
        status=status,
        started_on=date(2026, 7, 1),
        ended_on=date(2026, 8, 30),
    )
    session.add(eng)
    session.flush()
    return eng


def _verified(session, eng, talent, visibility) -> VerifiedExperience:
    ve = VerifiedExperience(
        talent_id=talent.id,
        engagement_id=eng.id,
        organization_name_snapshot="Snap",
        role_snapshot="Stajyer",
        claim_type="COMPETENCE",
        visibility=visibility,
    )
    session.add(ve)
    session.flush()
    return ve


def _get(client, path: str, user: User | None):
    headers = {"X-Debug-User-Id": str(user.id)} if user else {}
    return client.get(path, headers=headers)


def _rows(response) -> list[list[str]]:
    text = response.content.decode("utf-8")
    assert text.startswith("﻿")
    return list(csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";"))


@pytest.fixture
def world(session):
    inst_a = _institution(session, "Kurum A")
    inst_b = _institution(session, "Kurum B")
    org1 = _org(session, "Şişli Yazılım")
    org2 = _org(session, "Güneş Ajansı")

    linked = _student(session, "linked@example.com", "Ayşe Bağlı", inst_a, "INSTITUTION")
    public = _student(session, "public@example.com", "Can Herkese", inst_a, "PUBLIC")
    private = _student(session, "private@example.com", "Gizli Öğrenci", inst_a, "PRIVATE")
    other = _student(session, "other@example.com", "Başka Kurumlu", inst_b, "INSTITUTION")

    e_pub = _engagement(session, linked, org1, inst_a, "VERIFIED", title="Herkese açık staj")
    e_inst = _engagement(session, linked, org1, inst_a, "VERIFIED", title="Kuruma açık staj")
    e_active = _engagement(session, public, org2, inst_a, "ACTIVE", title="Devam eden")
    _engagement(session, private, org1, inst_a, "VERIFIED", title="Gizli çalışma")
    _engagement(session, other, org1, inst_b, "VERIFIED", title="Başka kurum çalışması")
    _engagement(session, linked, org2, inst_b, "VERIFIED", title="Kurum B ile")
    ve_pub = _verified(session, e_pub, linked, "PUBLIC")
    _verified(session, e_inst, linked, "INSTITUTION")

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "org1": org1,
        "org2": org2,
        "linked": linked,
        "public": public,
        "private": private,
        "e_active": e_active,
        "ve_pub": ve_pub,
        "coord_a": _member(session, inst_a, "coord-a@example.com", "COORDINATOR"),
        "admin_a": _member(session, inst_a, "admin-a@example.com", "ADMIN"),
        "coord_b": _member(session, inst_b, "coord-b@example.com", "COORDINATOR"),
    }


def _paths(world):
    iid = world["inst_a"].id
    return [f"/institutions/{iid}/partners", f"/institutions/{iid}/report.csv"]


class TestPartners:
    @pytest.mark.parametrize("actor", ["coord_a", "admin_a"])
    def test_member_sees_partner_counts(self, client, world, actor):
        response = _get(client, f"/institutions/{world['inst_a'].id}/partners", world[actor])

        assert response.status_code == 200
        items = {i["organization_name"]: i for i in response.json()["items"]}
        # org1: linked student only (private student excluded), Kurum B work excluded.
        assert items["Şişli Yazılım"]["student_count"] == 1
        assert items["Şişli Yazılım"]["engagement_count"] == 2
        assert items["Şişli Yazılım"]["verified_count"] == 2
        assert items["Şişli Yazılım"]["verification_level"] == "T1"
        assert items["Güneş Ajansı"]["student_count"] == 1
        assert items["Güneş Ajansı"]["engagement_count"] == 1
        assert items["Güneş Ajansı"]["verified_count"] == 0
        assert "Gizli Öğrenci" not in response.text
        assert "@example.com" not in response.text

    def test_private_student_never_counted(self, client, world):
        items = _get(client, f"/institutions/{world['inst_a'].id}/partners", world["coord_a"]).json()["items"]
        assert sum(i["engagement_count"] for i in items) == 3


class TestReport:
    def test_headers_bom_delimiter_and_filename(self, client, world):
        response = _get(client, f"/institutions/{world['inst_a'].id}/report.csv", world["coord_a"])

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "charset=utf-8" in response.headers["content-type"]
        disposition = response.headers["content-disposition"]
        assert disposition.startswith('attachment; filename="yetkin360-rapor-')
        assert disposition.endswith('.csv"')
        assert response.content.startswith(b"\xef\xbb\xbf")
        rows = _rows(response)
        assert rows[0][:3] == ["Ad Soyad", "Bölüm", "Sınıf"]
        assert len(rows[0]) == 11
        assert "Bilgisayar Mühendisliği" in rows[1]  # Turkish chars survive

    def test_scope_excludes_private_and_other_institution(self, client, world):
        response = _get(client, f"/institutions/{world['inst_a'].id}/report.csv", world["admin_a"])
        body = response.content.decode("utf-8")

        assert "Gizli Öğrenci" not in body
        assert "Gizli çalışma" not in body
        assert "Başka Kurumlu" not in body
        assert "Kurum B ile" not in body
        assert "@example.com" not in body
        titles = {r[4] for r in _rows(response)[1:]}
        assert titles == {"Herkese açık staj", "Kuruma açık staj", "Devam eden"}

    def test_verification_link_only_for_public_experience(self, client, world):
        rows = _rows(_get(client, f"/institutions/{world['inst_a'].id}/report.csv", world["coord_a"]))
        by_title = {r[4]: r for r in rows[1:]}

        assert by_title["Herkese açık staj"][10].endswith(f"/v/{world['ve_pub'].public_token}")
        assert by_title["Herkese açık staj"][9] != ""
        assert by_title["Kuruma açık staj"][10] == ""  # not PUBLIC: no link
        assert by_title["Kuruma açık staj"][9] != ""  # date still shown
        assert by_title["Devam eden"][9:] == ["", ""]

    @pytest.mark.parametrize(
        "payload",
        ['=HYPERLINK("http://evil","x")', "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"],
    )
    def test_formula_cells_are_neutralised(self, client, session, world, payload):
        world["e_active"].title = payload
        world["public"].full_name = payload
        session.flush()

        rows = _rows(_get(client, f"/institutions/{world['inst_a'].id}/report.csv", world["coord_a"]))
        row = next(r for r in rows[1:] if r[3] == "Güneş Ajansı")
        assert row[4] == "'" + payload
        assert row[0] == "'" + payload
        for r in rows[1:]:
            for cell in r:
                assert not cell.startswith(("=", "+", "-", "@", "\t", "\r"))

    def test_export_is_audited_without_pii(self, client, session, world):
        response = _get(client, f"/institutions/{world['inst_a'].id}/report.csv", world["coord_a"])
        assert response.status_code == 200
        session.expire_all()

        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "INSTITUTION_REPORT_EXPORTED")
        ).scalars().all()
        assert len(events) == 1
        event = events[0]
        assert event.actor_user_id == world["coord_a"].id
        assert event.subject_id == world["inst_a"].id
        assert event.event_metadata["row_count"] == 3
        serialized = str(event.event_metadata)
        assert "@" not in serialized and "Ayşe" not in serialized


class TestNegative:
    @pytest.mark.parametrize("index", [0, 1])
    def test_other_institution_coordinator_gets_404(self, client, world, index):
        response = _get(client, _paths(world)[index], world["coord_b"])
        assert response.status_code == 404
        assert "Ayşe" not in response.text and "Şişli" not in response.text

    @pytest.mark.parametrize("index", [0, 1])
    def test_student_gets_404(self, client, session, world, index):
        student_user = session.get(User, world["linked"].user_id)
        assert _get(client, _paths(world)[index], student_user).status_code == 404

    @pytest.mark.parametrize("index", [0, 1])
    def test_organization_member_gets_404(self, client, session, world, index):
        org_user = _user(session, "org-member@example.com")
        session.add(OrganizationMember(organization_id=world["org1"].id, user_id=org_user.id, role="ADMIN"))
        session.flush()
        assert _get(client, _paths(world)[index], org_user).status_code == 404

    @pytest.mark.parametrize("suffix", ["partners", "report.csv"])
    def test_unknown_institution_gets_404(self, client, world, suffix):
        assert _get(client, f"/institutions/{uuid.uuid4()}/{suffix}", world["coord_a"]).status_code == 404

    @pytest.mark.parametrize("index", [0, 1])
    def test_unauthenticated_gets_401(self, client, world, index):
        assert _get(client, _paths(world)[index], None).status_code == 401

    def test_denied_export_writes_no_audit_event(self, client, session, world):
        _get(client, _paths(world)[1], world["coord_b"])
        session.expire_all()
        events = session.execute(
            select(AuditEvent).where(AuditEvent.action == "INSTITUTION_REPORT_EXPORTED")
        ).scalars().all()
        assert events == []


class TestDashboardEnrichment:
    def test_rows_carry_names_and_pending_attestation(self, client, session, world):
        evaluated = _engagement(
            session, world["linked"], world["org2"], world["inst_a"], "EVALUATED", title="Değerlendirildi"
        )
        pending = _engagement(
            session, world["public"], world["org1"], world["inst_a"], "PENDING_APPROVAL", title="Onay"
        )

        response = _get(client, f"/institutions/{world['inst_a'].id}/dashboard", world["coord_a"])
        assert response.status_code == 200
        body = response.json()

        assert body["summary"]["pending_attestation"] == 1
        item = body["pending_attestation"][0]
        assert item["id"] == str(evaluated.id)
        assert item["talent_full_name"] == "Ayşe Bağlı"
        assert item["organization_name"] == "Güneş Ajansı"
        assert item["kind"] == "INTERNSHIP"
        assert item["version"] == evaluated.version
        approval = body["pending_approval"][0]
        assert approval["id"] == str(pending.id)
        assert approval["talent_full_name"] == "Can Herkese"
        assert approval["organization_name"] == "Şişli Yazılım"

    def test_other_institution_dashboard_still_404(self, client, world):
        response = _get(client, f"/institutions/{world['inst_a'].id}/dashboard", world["coord_b"])
        assert response.status_code == 404
