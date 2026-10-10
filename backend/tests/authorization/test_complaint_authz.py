"""
Student complaints: who may open, read and decide.

- Only the engagement's talent opens/reads complaints on it: an organization
  member or coordinator in scope gets 403, anyone outside the scope 404.
- Only the platform admin sees the queue and decides (non-admin → 404).
- The organization's "deliberate non-verification" count is its UPHELD complaints.
- The student's statement never reaches audit or outbox.
"""

from datetime import datetime, timezone

import pytest

from app.models import (
    AuditEvent,
    Complaint,
    Deliverable,
    Engagement,
    Evidence,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    Outbox,
    TalentProfile,
    User,
)

STATEMENT = "Görevlerim üç haftadır onaylanmıyor, kuruluş mesajlarıma yanıt vermiyor."


def _h(user) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


def _user(session, email: str, **extra) -> User:
    user = User(email=email, password_hash="hash", **extra)
    session.add(user)
    session.flush()
    return user


def _talent(session, user: User, name: str, institution: Institution | None = None) -> TalentProfile:
    talent = TalentProfile(
        user_id=user.id,
        full_name=name,
        visibility="PRIVATE",
        institution_id=institution.id if institution else None,
    )
    session.add(talent)
    session.flush()
    return talent


def _engagement(session, talent, organization, institution=None, status="ACTIVE", title="Backend Stajı") -> Engagement:
    engagement = Engagement(
        talent_id=talent.id,
        organization_id=organization.id,
        institution_id=institution.id if institution else None,
        kind="INTERNSHIP",
        title=title,
        status=status,
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


def _evidence(session, talent, engagement, user, scan_status="CLEAN", deleted=False) -> Evidence:
    deliverable = Deliverable(
        engagement_id=engagement.id,
        title="Rapor",
        submitted_by_user_id=user.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    evidence = Evidence(
        owner_talent_id=talent.id,
        deliverable_id=deliverable.id,
        kind="DOCUMENT",
        scan_status=scan_status,
        storage_key=f"evidence/{deliverable.id}.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_etag="etag-scanned",
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    session.add(evidence)
    session.flush()
    return evidence


@pytest.fixture
def world(session):
    """Two organizations with a student engagement each, an institution, and an admin."""
    institution = Institution(name="Kurum A", domain="kurum-a.example.com", verification_level="T1", status="ACTIVE")
    org_a = Organization(name="Kuruluş A", verification_level="T2", legal_id="CMP-A")
    org_b = Organization(name="Kuruluş B", verification_level="T1")
    session.add_all([institution, org_a, org_b])
    session.flush()

    alice_user = _user(session, "alice@example.com")
    bob_user = _user(session, "bob@example.com")
    member_a = _user(session, "member-a@example.com")
    member_b = _user(session, "member-b@example.com")
    coordinator = _user(session, "coordinator@example.com")
    admin = _user(session, "admin@example.com", is_platform_admin=True)
    session.add_all(
        [
            OrganizationMember(organization_id=org_a.id, user_id=member_a.id, role="ADMIN"),
            OrganizationMember(organization_id=org_b.id, user_id=member_b.id, role="MEMBER"),
            InstitutionMember(institution_id=institution.id, user_id=coordinator.id, role="COORDINATOR"),
        ]
    )
    alice = _talent(session, alice_user, "Alice Öğrenci", institution)
    bob = _talent(session, bob_user, "Bob Öğrenci")
    session.flush()

    class World:
        pass

    w = World()
    w.institution, w.org_a, w.org_b = institution, org_a, org_b
    w.alice_user, w.bob_user, w.alice, w.bob = alice_user, bob_user, alice, bob
    w.member_a, w.member_b, w.coordinator, w.admin = member_a, member_b, coordinator, admin
    w.engagement = _engagement(session, alice, org_a, institution)
    w.bob_engagement = _engagement(session, bob, org_b, title="Bob'un Stajı")
    return w


def _open(client, user, engagement, **body):
    payload = {"category": "TASK_APPROVAL", "description": STATEMENT, **body}
    return client.post(f"/engagements/{engagement.id}/complaints", json=payload, headers=_h(user))


class TestOpenComplaint:
    def test_student_opens_complaint_and_organization_is_notified(self, client, session, world):
        response = _open(client, world.alice_user, world.engagement)

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "OPEN"
        assert body["category"] == "TASK_APPROVAL"
        assert body["description"] == STATEMENT
        assert body["decided_at"] is None

        complaint = session.query(Complaint).one()
        assert complaint.organization_id == world.org_a.id
        assert complaint.talent_id == world.alice.id
        assert complaint.created_by_user_id == world.alice_user.id

        outbox = session.query(Outbox).filter_by(topic="complaint.opened").one()
        assert outbox.payload == {
            "complaint_id": str(complaint.id),
            "engagement_id": str(world.engagement.id),
            "organization_id": str(world.org_a.id),
        }
        audit = session.query(AuditEvent).filter_by(action="COMPLAINT_OPENED").one()
        # The statement is personal: it stays in the complaint row only.
        assert STATEMENT not in str(outbox.payload)
        assert STATEMENT not in str(audit.event_metadata)

    @pytest.mark.parametrize("actor", ["member_a", "coordinator"])
    def test_other_side_in_scope_cannot_open_403(self, actor, client, session, world):
        response = _open(client, getattr(world, actor), world.engagement)

        assert response.status_code == 403, response.text
        assert session.query(Complaint).count() == 0

    @pytest.mark.parametrize("actor", ["bob_user", "member_b", "admin"])
    def test_outside_scope_cannot_open_404(self, actor, client, session, world):
        response = _open(client, getattr(world, actor), world.engagement)

        assert response.status_code == 404, response.text
        assert session.query(Complaint).count() == 0

    def test_anonymous_401(self, client, world):
        response = client.post(
            f"/engagements/{world.engagement.id}/complaints",
            json={"category": "PERSONAL", "description": STATEMENT},
        )
        assert response.status_code == 401

    def test_draft_engagement_422(self, client, session, world):
        draft = _engagement(session, world.alice, world.org_a, world.institution, status="DRAFT", title="Taslak")

        response = _open(client, world.alice_user, draft)

        assert response.status_code == 422, response.text
        assert response.json()["code"] == "PRECONDITION_FAILED"

    def test_second_open_complaint_on_same_engagement_409(self, client, session, world):
        assert _open(client, world.alice_user, world.engagement).status_code == 201

        response = _open(client, world.alice_user, world.engagement, category="PERSONAL")

        assert response.status_code == 409, response.text
        assert response.json()["code"] == "COMPLAINT_ALREADY_OPEN"
        assert session.query(Complaint).count() == 1

    @pytest.mark.parametrize(
        "body",
        [
            {"description": "kısa"},
            {"description": "x" * 2001},
            {"category": "SOMETHING_ELSE"},
        ],
        ids=["too_short", "too_long", "unknown_category"],
    )
    def test_invalid_input_rejected(self, body, client, session, world):
        response = _open(client, world.alice_user, world.engagement, **body)

        assert response.status_code in (400, 422), response.text
        assert session.query(Complaint).count() == 0


class TestComplaintEvidence:
    def test_own_clean_evidence_of_the_engagement_can_be_attached(self, client, session, world):
        evidence = _evidence(session, world.alice, world.engagement, world.alice_user)

        response = _open(client, world.alice_user, world.engagement, evidence_id=str(evidence.id))

        assert response.status_code == 201, response.text
        assert response.json()["evidence_id"] == str(evidence.id)

    @pytest.mark.parametrize("case", ["someone_elses", "other_engagement", "not_scanned", "deleted", "unknown"])
    def test_any_other_evidence_is_rejected_422(self, case, client, session, world):
        if case == "someone_elses":
            evidence_id = _evidence(session, world.bob, world.bob_engagement, world.bob_user).id
        elif case == "other_engagement":
            other = _engagement(session, world.alice, world.org_b, title="Diğer Çalışma")
            evidence_id = _evidence(session, world.alice, other, world.alice_user).id
        elif case == "not_scanned":
            evidence_id = _evidence(session, world.alice, world.engagement, world.alice_user, scan_status="PENDING").id
        elif case == "deleted":
            evidence_id = _evidence(session, world.alice, world.engagement, world.alice_user, deleted=True).id
        else:
            evidence_id = world.engagement.id  # a UUID that is not an evidence

        response = _open(client, world.alice_user, world.engagement, evidence_id=str(evidence_id))

        assert response.status_code == 422, response.text
        # One answer for every case: the caller learns nothing about others' files.
        assert response.json()["code"] == "INVALID_EVIDENCE"
        assert session.query(Complaint).count() == 0


class TestReadOwnComplaints:
    def test_student_reads_own_complaints(self, client, world):
        _open(client, world.alice_user, world.engagement)

        response = client.get(f"/engagements/{world.engagement.id}/complaints", headers=_h(world.alice_user))

        assert response.status_code == 200
        assert [item["description"] for item in response.json()["items"]] == [STATEMENT]

    @pytest.mark.parametrize(
        "actor, expected", [("member_a", 403), ("coordinator", 403), ("bob_user", 404), ("member_b", 404), ("admin", 404)]
    )
    def test_nobody_else_reads_them_here(self, actor, expected, client, world):
        _open(client, world.alice_user, world.engagement)

        response = client.get(f"/engagements/{world.engagement.id}/complaints", headers=_h(getattr(world, actor)))

        assert response.status_code == expected, response.text
        assert STATEMENT not in response.text


class TestAdminQueue:
    @pytest.mark.parametrize("actor", ["alice_user", "member_a", "coordinator"])
    def test_non_admin_cannot_see_queue_404(self, actor, client, world):
        _open(client, world.alice_user, world.engagement)

        response = client.get("/admin/complaints", headers=_h(getattr(world, actor)))

        assert response.status_code == 404
        assert STATEMENT not in response.text

    @pytest.mark.parametrize("actor", ["alice_user", "member_a", "coordinator"])
    def test_non_admin_cannot_decide_404(self, actor, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]

        response = client.post(
            f"/admin/complaints/{complaint_id}/resolve",
            json={"outcome": "DISMISSED"},
            headers=_h(getattr(world, actor)),
        )

        assert response.status_code == 404
        assert session.query(Complaint).one().status == "OPEN"

    def test_admin_sees_open_complaints_with_labels(self, client, world):
        _open(client, world.alice_user, world.engagement)

        response = client.get("/admin/complaints", headers=_h(world.admin))

        assert response.status_code == 200, response.text
        (item,) = response.json()["items"]
        assert item["talent_name"] == "Alice Öğrenci"
        assert item["organization_name"] == "Kuruluş A"
        assert item["engagement_title"] == "Backend Stajı"
        assert item["engagement_status"] == "ACTIVE"
        assert item["description"] == STATEMENT
        assert item["has_evidence"] is False
        assert item["organization_upheld_count"] == 0
        assert item["status"] == "OPEN"

    def test_upheld_decision_counts_against_the_organization_and_notifies_the_student(self, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]

        response = client.post(
            f"/admin/complaints/{complaint_id}/resolve",
            json={"outcome": "UPHELD", "note": "Kuruluş üç hatırlatmaya rağmen işlem yapmadı."},
            headers=_h(world.admin),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "UPHELD"
        assert body["organization_upheld_count"] == 1
        assert body["decision_note"] == "Kuruluş üç hatırlatmaya rağmen işlem yapmadı."

        complaint = session.query(Complaint).one()
        assert complaint.decided_by_user_id == world.admin.id
        assert complaint.decided_at is not None

        outbox = session.query(Outbox).filter_by(topic="complaint.resolved").one()
        assert outbox.payload["outcome"] == "UPHELD"
        assert outbox.payload["talent_id"] == str(world.alice.id)
        audit = session.query(AuditEvent).filter_by(action="ADMIN_RESOLVE_COMPLAINT").one()
        assert audit.event_metadata["outcome"] == "UPHELD"
        assert "hatırlatma" not in str(audit.event_metadata)

        assert client.get("/admin/complaints", headers=_h(world.admin)).json()["items"] == []
        upheld = client.get("/admin/complaints?status=UPHELD", headers=_h(world.admin)).json()["items"]
        assert [item["id"] for item in upheld] == [complaint_id]

    def test_dismissed_decision_does_not_count(self, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]

        response = client.post(
            f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "DISMISSED"}, headers=_h(world.admin)
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "DISMISSED"
        assert response.json()["organization_upheld_count"] == 0

    def test_count_is_per_organization(self, client, session, world):
        first = _open(client, world.alice_user, world.engagement).json()["id"]
        other = _open(client, world.bob_user, world.bob_engagement).json()["id"]
        client.post(f"/admin/complaints/{first}/resolve", json={"outcome": "UPHELD"}, headers=_h(world.admin))

        items = client.get("/admin/complaints", headers=_h(world.admin)).json()["items"]

        assert [(item["id"], item["organization_upheld_count"]) for item in items] == [(other, 0)]

    def test_decision_is_final_409(self, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]
        client.post(f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "DISMISSED"}, headers=_h(world.admin))

        response = client.post(
            f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "UPHELD"}, headers=_h(world.admin)
        )

        assert response.status_code == 409, response.text
        assert response.json()["code"] == "NOT_OPEN"
        assert session.query(Complaint).one().status == "DISMISSED"

    def test_unknown_complaint_404(self, client, world):
        response = client.post(
            f"/admin/complaints/{world.engagement.id}/resolve", json={"outcome": "UPHELD"}, headers=_h(world.admin)
        )
        assert response.status_code == 404

    def test_student_can_complain_again_after_a_decision(self, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]
        client.post(f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "DISMISSED"}, headers=_h(world.admin))

        assert _open(client, world.alice_user, world.engagement, category="PERSONAL").status_code == 201

    def test_verification_queue_shows_the_count(self, client, session, world):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]
        client.post(f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "UPHELD"}, headers=_h(world.admin))

        items = client.get("/admin/verification-queue", headers=_h(world.admin)).json()["items"]

        assert [(item["name"], item["upheld_complaint_count"]) for item in items] == [("Kuruluş A", 1)]


class TestComplaintEvidenceAccess:
    """
    PRIVATE evidence is closed to admins — except the one document a student
    attached to a complaint, and only through the complaint.
    """

    @pytest.fixture
    def storage(self, monkeypatch):
        state = {"etag": "etag-scanned"}
        monkeypatch.setattr("app.services.evidence.head_object_etag", lambda bucket, key: state["etag"])
        monkeypatch.setattr(
            "app.services.evidence.generate_presigned_get_url",
            lambda bucket, object_key, ttl: f"https://storage.example.test/{object_key}?sig=x",
        )
        return state

    def _complaint_with_evidence(self, client, session, world):
        evidence = _evidence(session, world.alice, world.engagement, world.alice_user)
        complaint_id = _open(client, world.alice_user, world.engagement, evidence_id=str(evidence.id)).json()["id"]
        return complaint_id, evidence

    def test_admin_gets_short_lived_url_and_the_access_is_audited(self, client, session, world, storage):
        complaint_id, evidence = self._complaint_with_evidence(client, session, world)

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(world.admin))

        assert response.status_code == 200, response.text
        assert response.json()["download_url"].startswith("https://storage.example.test/")
        assert response.json()["expires_in"] > 0
        audit = session.query(AuditEvent).filter_by(action="complaint.evidence_downloaded").one()
        assert audit.actor_user_id == world.admin.id
        assert audit.subject_id == evidence.id
        assert audit.event_metadata == {"complaint_id": complaint_id}

    @pytest.mark.parametrize("actor", ["alice_user", "member_a", "coordinator", "bob_user"])
    def test_nobody_but_the_admin_uses_this_path_404(self, actor, client, session, world, storage):
        complaint_id, _ = self._complaint_with_evidence(client, session, world)

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(getattr(world, actor)))

        assert response.status_code == 404
        assert "download_url" not in response.text

    def test_admin_still_cannot_read_the_evidence_outside_the_complaint(self, client, session, world, storage):
        _, attached = self._complaint_with_evidence(client, session, world)
        other = _engagement(session, world.alice, world.org_b, title="Diğer Çalışma")
        not_attached = _evidence(session, world.alice, other, world.alice_user)

        for evidence in (attached, not_attached):
            response = client.get(f"/evidence/{evidence.id}/download-url", headers=_h(world.admin))
            assert response.status_code == 403, response.text
            assert "download_url" not in response.text

    def test_complaint_without_document_404(self, client, session, world, storage):
        complaint_id = _open(client, world.alice_user, world.engagement).json()["id"]

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(world.admin))

        assert response.status_code == 404

    def test_unknown_complaint_404(self, client, world, storage):
        response = client.get(f"/admin/complaints/{world.engagement.id}/evidence-url", headers=_h(world.admin))
        assert response.status_code == 404

    def test_document_deleted_after_attaching_404(self, client, session, world, storage):
        complaint_id, evidence = self._complaint_with_evidence(client, session, world)
        evidence.deleted_at = datetime.now(timezone.utc)
        session.flush()

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(world.admin))

        assert response.status_code == 404

    def test_content_changed_since_scan_is_blocked_409(self, client, session, world, storage):
        complaint_id, _ = self._complaint_with_evidence(client, session, world)
        storage["etag"] = "etag-tampered"

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(world.admin))

        assert response.status_code == 409, response.text
        assert response.json()["code"] == "EVIDENCE_CONTENT_CHANGED"
        assert "download_url" not in response.text

    def test_document_stays_readable_after_the_decision(self, client, session, world, storage):
        complaint_id, _ = self._complaint_with_evidence(client, session, world)
        client.post(f"/admin/complaints/{complaint_id}/resolve", json={"outcome": "UPHELD"}, headers=_h(world.admin))

        response = client.get(f"/admin/complaints/{complaint_id}/evidence-url", headers=_h(world.admin))

        assert response.status_code == 200, response.text

