"""Complaint (Şikayet) backend behaviour — sikayet-backend, AC-13…AC-21, AC-S11…AC-S14."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.models import AuditEvent, Complaint, ComplaintEvent, OrganizationMember, Outbox
from app.workers import outbox_worker
from tests._complaint_data import (
    EXE_BYTES,
    add_attachment,
    add_engagement,
    fake_storage,
    h,
    make_world,
    open_complaint,
    to_escalated,
    to_explanation_requested,
    transition,
)


@pytest.fixture
def w(session):
    return make_world(session)


def _complaint(session, complaint_id) -> Complaint:
    session.expire_all()
    return session.get(Complaint, uuid.UUID(complaint_id))


def _topics(session, complaint_id) -> list[dict]:
    rows = session.execute(select(Outbox).where(Outbox.topic.like("complaint.%"))).scalars().all()
    return [{"topic": r.topic, **r.payload} for r in rows if r.payload.get("complaint_id") == complaint_id]


# ---------------------------------------------------------------------------
# AC-13 / AC-14 / AC-S11 / AC-S12 — opening a complaint
# ---------------------------------------------------------------------------


class TestOpenComplaint:
    def test_happy_path_returns_201_and_derives_target_and_respondent(self, client, session, w):
        body = open_complaint(client, w)

        assert body["status"] == "OPEN"
        assert body["status_label"] == "IN_PROGRESS"
        assert body["subject_type"] == "ENGAGEMENT"
        assert body["subject_id"] == str(w.engagement.id)
        assert {"id", "created_at"} <= set(body)

        row = _complaint(session, body["id"])
        assert row.talent_id == w.talent_a.id
        assert row.target_type == "INSTITUTION"
        assert row.target_institution_id == w.institution.id
        assert row.respondent_user_id == w.coord.id
        events = session.execute(select(ComplaintEvent).where(ComplaintEvent.complaint_id == row.id)).scalars().all()
        assert [e.event_type for e in events] == ["CREATED"]
        audit = session.execute(
            select(AuditEvent).where(AuditEvent.action == "complaint.created", AuditEvent.subject_id == row.id)
        ).scalars().all()
        assert len(audit) == 1
        assert "description" not in (audit[0].event_metadata or {})

    def test_pending_evaluation_targets_the_organization_and_its_supervisor(self, client, session, w):
        engagement = add_engagement(session, w, w.talent_a, status="PENDING_EVALUATION", supervisor_user_id=w.org_admin.id)
        body = open_complaint(client, w, engagement=engagement)
        row = _complaint(session, body["id"])
        assert row.target_type == "ORGANIZATION"
        assert row.target_organization_id == w.org.id
        assert row.respondent_user_id == w.org_admin.id

    def test_too_early_returns_409(self, client, session, w):
        fresh = add_engagement(session, w, w.talent_a, days_ago=2)
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(fresh.id), "description": "Henüz erken bir şikayet."},
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "TOO_EARLY"

    def test_wait_starts_at_the_transition_into_the_pending_status(self, client, session, w):
        """An old engagement that only recently entered PENDING_APPROVAL is still too early."""
        session.add(
            AuditEvent(
                actor_user_id=w.user_a.id,
                action="ENGAGEMENT_TRANSITIONED",
                subject_type="engagement",
                subject_id=w.engagement.id,
                result="SUCCESS",
                event_metadata={"from_status": "DRAFT", "to_status": "PENDING_APPROVAL"},
            )
        )
        session.flush()
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(w.engagement.id), "description": "Bekliyorum uzun süredir."},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "TOO_EARLY"

    def test_second_open_complaint_for_same_subject_returns_409(self, client, w):
        open_complaint(client, w)
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(w.engagement.id), "description": "Tekrar şikayet ediyorum."},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "ALREADY_OPEN"

    def test_closed_complaint_allows_a_new_one(self, client, w):
        first = open_complaint(client, w)
        assert transition(client, w, first["id"], "DISMISS", reason="Yetersiz bilgi.").status_code == 200
        open_complaint(client, w)

    def test_subject_not_pending_returns_409(self, client, session, w):
        active = add_engagement(session, w, w.talent_a, status="ACTIVE")
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(active.id), "description": "Aktif çalışma şikayeti."},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "NOT_PENDING"

    def test_pending_approval_without_institution_returns_409_not_pending(self, client, session, w):
        lone = add_engagement(session, w, w.talent_a, institution_id=None)
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(lone.id), "description": "Kurumsuz çalışma şikayeti."},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "NOT_PENDING"

    def test_someone_elses_subject_returns_404(self, client, w):
        r = client.post(
            "/complaints",
            headers=h(w.user_b),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(w.engagement.id), "description": "Başkasının stajı."},
        )
        assert r.status_code == 404

    def test_unknown_subject_returns_404(self, client, w):
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(uuid.uuid4()), "description": "Olmayan staj şikayeti."},
        )
        assert r.status_code == 404

    @pytest.mark.parametrize(
        "extra",
        [
            {"organization_id": str(uuid.uuid4())},
            {"respondent_user_id": str(uuid.uuid4())},
            {"status": "UPHELD"},
            {"talent_id": str(uuid.uuid4())},
        ],
    )
    def test_server_owned_fields_in_body_are_rejected_422(self, client, session, w, extra):
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={
                "subject_type": "ENGAGEMENT",
                "subject_id": str(w.engagement.id),
                "description": "Sunucu alanları denemesi.",
                **extra,
            },
        )
        assert r.status_code == 422
        assert session.execute(select(Complaint)).scalars().first() is None

    @pytest.mark.parametrize("description", ["", "kısa", "x" * 4001])
    def test_description_length_is_validated(self, client, w, description):
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(w.engagement.id), "description": description},
        )
        assert r.status_code == 422

    def test_fourth_complaint_in_24_hours_returns_429(self, client, session, w):
        for _ in range(3):
            open_complaint(client, w, engagement=add_engagement(session, w, w.talent_a))
        fourth = add_engagement(session, w, w.talent_a)
        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "ENGAGEMENT", "subject_id": str(fourth.id), "description": "Dördüncü şikayetim bu."},
        )
        assert r.status_code == 429
        assert r.json()["code"] == "RATE_LIMITED"

    def test_certificate_check_subject(self, client, session, w):
        from app.models import CertificateCheck, Deliverable, Evidence

        engagement = add_engagement(session, w, w.talent_a, status="ACTIVE")
        deliverable = Deliverable(
            engagement_id=engagement.id,
            title="Sertifika",
            submitted_by_user_id=w.user_a.id,
            submitted_at=datetime.now(timezone.utc),
        )
        session.add(deliverable)
        session.flush()
        evidence = Evidence(
            owner_talent_id=w.talent_a.id,
            deliverable_id=deliverable.id,
            kind="CERTIFICATE",
            provenance="SELF_UPLOADED",
            visibility="PRIVATE",
            scan_status="CLEAN",
            storage_key=f"evidence/{w.talent_a.id}/{uuid.uuid4()}.pdf",
            mime_type="application/pdf",
            size_bytes=10,
        )
        session.add(evidence)
        session.flush()
        check = CertificateCheck(
            evidence_id=evidence.id,
            status="DONE",
            requested_by_talent_at=datetime.now(timezone.utc) - timedelta(days=9),
        )
        session.add(check)
        session.flush()

        r = client.post(
            "/complaints",
            headers=h(w.user_a),
            json={"subject_type": "CERTIFICATE_CHECK", "subject_id": str(check.id), "description": "Sertifikam bekliyor."},
        )
        assert r.status_code == 201, r.text
        row = _complaint(session, r.json()["id"])
        assert row.target_type == "INSTITUTION"
        assert row.respondent_user_id == w.coord.id

        other = client.post(
            "/complaints",
            headers=h(w.user_b),
            json={"subject_type": "CERTIFICATE_CHECK", "subject_id": str(check.id), "description": "Başkasının sertifikası."},
        )
        assert other.status_code == 404


# ---------------------------------------------------------------------------
# AC-19 — student view never shows internal state
# ---------------------------------------------------------------------------


class TestStudentView:
    def test_list_envelope_and_in_progress_label(self, client, w):
        created = open_complaint(client, w)
        to_explanation_requested(client, w, created["id"])

        r = client.get("/complaints", headers=h(w.user_a))
        assert r.status_code == 200
        body = r.json()
        assert body["limit"] == 50 and body["offset"] == 0 and body["has_more"] is False
        item = body["items"][0]
        assert item["status_label"] == "IN_PROGRESS"
        assert "status" not in item
        assert item["resolution_reason"] is None
        assert item["closed_at"] is None
        assert "Lütfen gecikmeyi" not in r.text  # admin note never reaches the student

    def test_empty_list(self, client, w):
        r = client.get("/complaints", headers=h(w.user_b))
        assert r.json() == {"items": [], "limit": 50, "offset": 0, "has_more": False}

    def test_has_more_uses_limit_plus_one(self, client, session, w):
        open_complaint(client, w)
        open_complaint(client, w, engagement=add_engagement(session, w, w.talent_a))
        r = client.get("/complaints?limit=1", headers=h(w.user_a))
        assert len(r.json()["items"]) == 1
        assert r.json()["has_more"] is True

    def test_terminal_shows_outcome_and_reason(self, client, w):
        created = open_complaint(client, w)
        transition(client, w, created["id"], "DISMISS", reason="Süre henüz makul.")
        r = client.get(f"/complaints/{created['id']}", headers=h(w.user_a))
        assert r.status_code == 200
        assert r.json()["status_label"] == "DISMISSED"
        assert r.json()["resolution_reason"] == "Süre henüz makul."
        assert r.json()["closed_at"] is not None


# ---------------------------------------------------------------------------
# AC-16 / AC-17 / AC-18 / AC-20 / AC-21 — admin state machine
# ---------------------------------------------------------------------------


class TestStateMachine:
    def test_request_explanation_from_open_records_review_started_and_notifies_respondent(self, client, session, w):
        created = open_complaint(client, w)
        r = transition(client, w, created["id"], "REQUEST_EXPLANATION", note="Lütfen açıklayın.")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "EXPLANATION_REQUESTED"
        assert r.json()["explanation_due_at"] is not None
        assert [e["event_type"] for e in r.json()["events"]] == ["CREATED", "REVIEW_STARTED", "EXPLANATION_REQUESTED"]
        topics = _topics(session, created["id"])
        assert topics == [
            {"topic": "complaint.explanation_requested", "complaint_id": created["id"], "respondent_user_id": str(w.coord.id)}
        ]

    def test_respondent_sees_note_not_description_then_explains(self, client, w):
        created = open_complaint(client, w)
        to_explanation_requested(client, w, created["id"])

        r = client.get(f"/complaints/{created['id']}", headers=h(w.coord))
        assert r.status_code == 200
        body = r.json()
        assert body["viewer_role"] == "RESPONDENT"
        assert body["request_note"] == "Lütfen gecikmeyi açıklayın."
        assert "description" not in body and "attachments" not in body
        assert "10 gündür" not in r.text

        assigned = client.get("/complaints/assigned", headers=h(w.coord))
        assert [i["id"] for i in assigned.json()["items"]] == [created["id"]]

        r = client.post(f"/complaints/{created['id']}/explanation", headers=h(w.coord), json={"text": "Yoğunluk vardı."})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "EXPLANATION_SUBMITTED"

        again = client.post(f"/complaints/{created['id']}/explanation", headers=h(w.coord), json={"text": "Ek açıklama."})
        assert again.status_code == 409
        assert again.json()["code"] == "INVALID_TRANSITION"

    def test_accept_explanation_resolves(self, client, session, w):
        created = open_complaint(client, w)
        to_explanation_requested(client, w, created["id"])
        client.post(f"/complaints/{created['id']}/explanation", headers=h(w.coord), json={"text": "Onayladım."})
        r = transition(client, w, created["id"], "ACCEPT_EXPLANATION", reason="Gerekçe yeterli.")
        assert r.status_code == 200
        assert r.json()["status"] == "RESOLVED"
        assert {"topic": "complaint.closed", "complaint_id": created["id"], "talent_id": str(w.talent_a.id), "outcome": "RESOLVED"} in _topics(session, created["id"])

    def test_dismiss_requires_reason(self, client, w):
        created = open_complaint(client, w)
        assert transition(client, w, created["id"], "DISMISS").status_code == 422
        assert transition(client, w, created["id"], "DISMISS", reason="").status_code == 422

    def test_request_explanation_requires_note(self, client, w):
        created = open_complaint(client, w)
        assert transition(client, w, created["id"], "REQUEST_EXPLANATION").status_code == 422

    def test_dismiss_closes_and_notifies_student(self, client, session, w):
        created = open_complaint(client, w)
        r = transition(client, w, created["id"], "DISMISS", reason="Asılsız.")
        assert r.status_code == 200
        assert r.json()["status"] == "DISMISSED"
        assert r.json()["closed_at"] is not None
        assert any(t["topic"] == "complaint.closed" and t["outcome"] == "DISMISSED" for t in _topics(session, created["id"]))

    def test_reject_escalates_notifies_others_and_uphold_counts(self, client, session, w):
        created = open_complaint(client, w)
        to_escalated(client, w, created["id"])
        assert _complaint(session, created["id"]).status == "ESCALATED"
        escalations = [t for t in _topics(session, created["id"]) if t["topic"] == "complaint.escalated"]
        assert escalations == [
            {
                "topic": "complaint.escalated",
                "complaint_id": created["id"],
                "target_type": "INSTITUTION",
                "target_id": str(w.institution.id),
                "excluded_user_id": str(w.coord.id),
            }
        ]

        # Other coordinators of the same institution may now read it.
        assert client.get(f"/complaints/{created['id']}", headers=h(w.coord2)).status_code == 200

        dash = client.get(f"/institutions/{w.institution.id}/dashboard", headers=h(w.coord2))
        assert dash.json()["upheld_complaint_count"] == 0

        r = transition(client, w, created["id"], "UPHOLD", reason="Yanıtsız bırakıldı.")
        assert r.status_code == 200
        assert r.json()["status"] == "UPHELD"
        dash = client.get(f"/institutions/{w.institution.id}/dashboard", headers=h(w.coord2))
        assert dash.json()["upheld_complaint_count"] == 1

    def test_upheld_organization_count_on_discover_and_profile(self, client, session, w):
        engagement = add_engagement(session, w, w.talent_a, status="PENDING_EVALUATION", supervisor_user_id=w.org_admin.id)
        created = open_complaint(client, w, engagement=engagement)

        def org_card():
            r = client.get("/discover/organizations", headers=h(w.user_b))
            assert r.status_code == 200, r.text
            return next(i for i in r.json()["items"] if i["id"] == str(w.org.id))

        assert org_card()["upheld_complaint_count"] == 0
        transition(client, w, created["id"], "REQUEST_EXPLANATION", note="Açıklayın.")
        client.post(f"/complaints/{created['id']}/explanation", headers=h(w.org_admin), json={"text": "Bakamadık."})
        transition(client, w, created["id"], "REJECT_EXPLANATION")
        transition(client, w, created["id"], "UPHOLD")

        card = org_card()
        assert card["upheld_complaint_count"] == 1
        assert set(card) == {"id", "name", "verification_level", "domain", "upheld_complaint_count"}
        directory = client.get("/organizations/", headers=h(w.user_b)).json()["items"]
        assert next(i for i in directory if i["id"] == str(w.org.id))["upheld_complaint_count"] == 1
        detail = client.get(f"/organizations/{w.org.id}", headers=h(w.org_admin))
        assert detail.json()["upheld_complaint_count"] == 1

    def test_invalid_transitions_return_409_and_change_nothing(self, client, session, w):
        created = open_complaint(client, w)
        r = transition(client, w, created["id"], "UPHOLD")
        assert r.status_code == 409
        assert r.json()["code"] == "INVALID_TRANSITION"
        assert _complaint(session, created["id"]).status == "OPEN"

        transition(client, w, created["id"], "DISMISS", reason="Kapandı.")
        for action, extra in [("START_REVIEW", {}), ("REQUEST_EXPLANATION", {"note": "x"}), ("RESOLVE", {}), ("UPHOLD", {})]:
            r = transition(client, w, created["id"], action, **extra)
            assert r.status_code == 409, action
        assert _complaint(session, created["id"]).status == "DISMISSED"

    def test_version_conflict(self, client, w):
        created = open_complaint(client, w)
        r = transition(client, w, created["id"], "START_REVIEW", version=99)
        assert r.status_code == 409
        assert r.json()["code"] == "VERSION_CONFLICT"
        ok = transition(client, w, created["id"], "START_REVIEW", version=1)
        assert ok.status_code == 200
        assert ok.json()["version"] == 2

    def test_reject_before_deadline_without_explanation_is_409_after_deadline_escalates(self, client, session, w):
        created = open_complaint(client, w)
        to_explanation_requested(client, w, created["id"])
        r = transition(client, w, created["id"], "REJECT_EXPLANATION")
        assert r.status_code == 409
        assert r.json()["code"] == "DEADLINE_NOT_REACHED"

        session.execute(
            text("UPDATE complaints SET explanation_due_at = now() - interval '1 day' WHERE id = :id"),
            {"id": created["id"]},
        )
        r = transition(client, w, created["id"], "REJECT_EXPLANATION")
        assert r.status_code == 200
        assert r.json()["status"] == "ESCALATED"

    def test_resolve_requires_subject_no_longer_pending_unless_escalated(self, client, session, w):
        created = open_complaint(client, w)
        transition(client, w, created["id"], "START_REVIEW")
        r = transition(client, w, created["id"], "RESOLVE")
        assert r.status_code == 409

        w.engagement.status = "ACTIVE"
        session.flush()
        detail = client.get(f"/admin/complaints/{created['id']}", headers=h(w.admin))
        assert detail.json()["subject_pending"] is False
        # AC-21: the complaint did not close by itself.
        assert detail.json()["status"] == "UNDER_REVIEW"
        r = transition(client, w, created["id"], "RESOLVE", reason="Onay verildi.")
        assert r.status_code == 200
        assert r.json()["status"] == "RESOLVED"

    def test_request_explanation_without_respondent_returns_409(self, client, session, w):
        from app.models import Institution

        empty = Institution(name="Üyesiz Kurum")
        session.add(empty)
        session.flush()
        engagement = add_engagement(session, w, w.talent_a, institution_id=empty.id)
        created = open_complaint(client, w, engagement=engagement)
        r = transition(client, w, created["id"], "REQUEST_EXPLANATION", note="Açıklayın.")
        assert r.status_code == 409
        assert r.json()["code"] == "NO_RESPONDENT"

    def test_every_transition_is_audited_with_actor(self, client, session, w):
        created = open_complaint(client, w)
        to_escalated(client, w, created["id"])
        actions = session.execute(
            select(AuditEvent.action, AuditEvent.actor_user_id).where(AuditEvent.subject_id == uuid.UUID(created["id"]))
        ).all()
        names = [a for a, _ in actions]
        assert names.count("complaint.transitioned") == 4  # review_started, requested, submitted, rejected
        assert all(actor is not None for _, actor in actions)


# ---------------------------------------------------------------------------
# Admin list / detail
# ---------------------------------------------------------------------------


class TestAdminQueue:
    def test_default_queue_excludes_closed_and_paginates(self, client, session, w):
        a = open_complaint(client, w)
        b = open_complaint(client, w, engagement=add_engagement(session, w, w.talent_a))
        transition(client, w, b["id"], "DISMISS", reason="Kapandı.")

        r = client.get("/admin/complaints", headers=h(w.admin))
        assert r.status_code == 200
        body = r.json()
        assert [i["id"] for i in body["items"]] == [a["id"]]
        assert body["has_more"] is False
        item = body["items"][0]
        assert item["target_name"] == "Şikayet Üniversitesi"
        assert item["subject_pending"] is True
        assert item["attachment_count"] == 0

        closed = client.get("/admin/complaints?status=DISMISSED", headers=h(w.admin)).json()["items"]
        assert [i["id"] for i in closed] == [b["id"]]

    def test_has_more(self, client, session, w):
        open_complaint(client, w)
        open_complaint(client, w, engagement=add_engagement(session, w, w.talent_a))
        r = client.get("/admin/complaints?limit=1", headers=h(w.admin))
        assert len(r.json()["items"]) == 1 and r.json()["has_more"] is True

    @pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "status=NOPE"])
    def test_invalid_paging_422(self, client, w, query):
        assert client.get(f"/admin/complaints?{query}", headers=h(w.admin)).status_code == 422

    def test_detail_contains_timeline_and_texts(self, client, w):
        created = open_complaint(client, w)
        to_escalated(client, w, created["id"])
        r = client.get(f"/admin/complaints/{created['id']}", headers=h(w.admin))
        body = r.json()
        assert body["description"].startswith("Stajım")
        assert body["explanation_text"] == "Yoğunluk vardı."
        assert body["talent_name"] == "Ayşe Öğrenci"
        assert body["respondent_user_id"] == str(w.coord.id)
        assert [e["event_type"] for e in body["events"]][-1] == "EXPLANATION_REJECTED"

    def test_unknown_id_404(self, client, w):
        assert client.get(f"/admin/complaints/{uuid.uuid4()}", headers=h(w.admin)).status_code == 404
        r = transition(client, w, str(uuid.uuid4()), "START_REVIEW")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# AC-15 / AC-S12 — attachments
# ---------------------------------------------------------------------------


class TestAttachments:
    def test_upload_register_and_download_by_owner_and_admin(self, client, session, w, monkeypatch):
        fake_storage(monkeypatch)
        created = open_complaint(client, w)

        url = client.post(
            f"/complaints/{created['id']}/attachments/upload-url",
            headers=h(w.user_a),
            json={"filename": "../../etc/passwd.pdf", "content_type": "application/pdf", "size_bytes": 209},
        )
        assert url.status_code == 200, url.text
        key = url.json()["object_key"]
        assert key.startswith(f"complaints/{created['id']}/") and key.endswith(".pdf")
        assert "passwd" not in key
        assert url.json()["expires_in"] == settings.s3_presigned_url_ttl_seconds

        r = add_attachment(client, w, created["id"])
        assert r.status_code == 201, r.text
        attachment_id = r.json()["id"]
        assert set(r.json()) == {"id", "mime_type", "size_bytes", "created_at"}

        own = client.get(f"/complaints/{created['id']}/attachments/{attachment_id}", headers=h(w.user_a))
        assert own.status_code == 200, own.text
        assert own.json()["expires_in"] == settings.evidence_download_url_ttl_seconds

        admin = client.get(f"/admin/complaints/{created['id']}/attachments/{attachment_id}", headers=h(w.admin))
        assert admin.status_code == 200, admin.text
        downloads = session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "complaint.attachment_downloaded", AuditEvent.subject_id == uuid.UUID(attachment_id)
            )
        ).scalars().all()
        assert {d.actor_user_id for d in downloads} == {w.user_a.id, w.admin.id}

        student = client.get(f"/complaints/{created['id']}", headers=h(w.user_a)).json()
        assert [a["id"] for a in student["attachments"]] == [attachment_id]

    def test_exe_disguised_as_pdf_is_rejected_422(self, client, w, monkeypatch):
        fake_storage(monkeypatch, data=EXE_BYTES)
        created = open_complaint(client, w)
        r = add_attachment(client, w, created["id"], data=EXE_BYTES)
        assert r.status_code == 422
        assert r.json()["code"] == "INVALID_FILE_CONTENT"

    def test_missing_object_is_422(self, client, w, monkeypatch):
        state = fake_storage(monkeypatch)
        created = open_complaint(client, w)
        state["data"] = None
        r = add_attachment(client, w, created["id"])
        assert r.status_code == 422
        assert r.json()["code"] == "UPLOAD_NOT_FOUND"

    def test_unsupported_type_and_size(self, client, w, monkeypatch):
        fake_storage(monkeypatch)
        created = open_complaint(client, w)
        r = client.post(
            f"/complaints/{created['id']}/attachments/upload-url",
            headers=h(w.user_a),
            json={"filename": "a.docx", "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "size_bytes": 10},
        )
        assert r.status_code == 422
        assert r.json()["code"] == "UNSUPPORTED_CONTENT_TYPE"
        r = client.post(
            f"/complaints/{created['id']}/attachments/upload-url",
            headers=h(w.user_a),
            json={"filename": "a.pdf", "content_type": "application/pdf", "size_bytes": settings.evidence_max_size_bytes + 1},
        )
        assert r.status_code == 422
        assert r.json()["code"] == "FILE_TOO_LARGE"

    def test_foreign_storage_key_is_404(self, client, w, monkeypatch):
        fake_storage(monkeypatch)
        created = open_complaint(client, w)
        r = client.post(
            f"/complaints/{created['id']}/attachments",
            headers=h(w.user_a),
            json={"storage_key": f"evidence/{w.talent_b.id}/{uuid.uuid4()}.pdf", "mime_type": "application/pdf", "size_bytes": 209},
        )
        assert r.status_code == 404

    def test_sixth_attachment_is_409(self, client, w, monkeypatch):
        fake_storage(monkeypatch)
        created = open_complaint(client, w)
        for _ in range(5):
            assert add_attachment(client, w, created["id"]).status_code == 201
        r = add_attachment(client, w, created["id"])
        assert r.status_code == 409
        assert r.json()["code"] == "ATTACHMENT_LIMIT_REACHED"

    def test_closed_complaint_rejects_attachments(self, client, w, monkeypatch):
        fake_storage(monkeypatch)
        created = open_complaint(client, w)
        transition(client, w, created["id"], "DISMISS", reason="Kapandı.")
        r = client.post(
            f"/complaints/{created['id']}/attachments/upload-url",
            headers=h(w.user_a),
            json={"filename": "a.pdf", "content_type": "application/pdf", "size_bytes": 10},
        )
        assert r.status_code == 409
        assert r.json()["code"] == "COMPLAINT_CLOSED"

    def test_content_changed_after_registration_blocks_download(self, client, session, w, monkeypatch):
        state = fake_storage(monkeypatch)
        created = open_complaint(client, w)
        attachment_id = add_attachment(client, w, created["id"]).json()["id"]
        state["etag"] = "swapped"
        r = client.get(f"/admin/complaints/{created['id']}/attachments/{attachment_id}", headers=h(w.admin))
        assert r.status_code == 409
        assert r.json()["code"] == "ATTACHMENT_CONTENT_CHANGED"

    def test_attachments_are_not_evidence_rows(self, client, session, w, monkeypatch):
        """AC-S10: sharing a document with the admin never widens evidence access."""
        from app.models import Evidence

        fake_storage(monkeypatch)
        created = open_complaint(client, w)
        add_attachment(client, w, created["id"])
        assert session.execute(select(Evidence)).scalars().first() is None


# ---------------------------------------------------------------------------
# AC-S14 — database guarantees
# ---------------------------------------------------------------------------


class TestDatabaseGuards:
    def _events(self, session, client, w):
        created = open_complaint(client, w)
        return created["id"]

    def test_complaint_events_update_forbidden(self, session, client, w):
        cid = self._events(session, client, w)
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("UPDATE complaint_events SET note = 'x' WHERE complaint_id = :id"), {"id": cid})

    def test_complaint_events_delete_forbidden(self, session, client, w):
        cid = self._events(session, client, w)
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("DELETE FROM complaint_events WHERE complaint_id = :id"), {"id": cid})

    def test_complaint_delete_forbidden(self, session, client, w):
        cid = self._events(session, client, w)
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("DELETE FROM complaints WHERE id = :id"), {"id": cid})

    def test_upheld_cannot_be_reopened(self, session, client, w):
        cid = self._events(session, client, w)
        to_escalated(client, w, cid)
        transition(client, w, cid, "UPHOLD")
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(text("UPDATE complaints SET status = 'OPEN', closed_at = NULL WHERE id = :id"), {"id": cid})

    def test_partial_unique_blocks_second_open_complaint(self, session, client, w):
        cid = self._events(session, client, w)
        row = _complaint(session, cid)
        with pytest.raises(DBAPIError):
            with session.begin_nested():
                session.execute(
                    text(
                        "INSERT INTO complaints (id, talent_id, subject_type, engagement_id, subject_state, target_type, "
                        "target_institution_id, description, status, version) VALUES "
                        "(:id, :t, 'ENGAGEMENT', :e, 'PENDING_APPROVAL', 'INSTITUTION', :i, 'ikinci açık şikayet', 'OPEN', 1)"
                    ),
                    {"id": str(uuid.uuid4()), "t": str(row.talent_id), "e": str(row.engagement_id), "i": str(row.target_institution_id)},
                )


# ---------------------------------------------------------------------------
# C6 / AC-S13 — outbox handlers
# ---------------------------------------------------------------------------


class TestOutboxHandlers:
    def test_handlers_registered(self):
        assert outbox_worker.DEFAULT_HANDLERS["complaint.explanation_requested"] is outbox_worker.complaint_explanation_requested_handler
        assert outbox_worker.DEFAULT_HANDLERS["complaint.escalated"] is outbox_worker.complaint_escalated_handler
        assert outbox_worker.DEFAULT_HANDLERS["complaint.closed"] is outbox_worker.complaint_closed_handler

    def _smtp(self, monkeypatch) -> list[dict]:
        monkeypatch.setattr(settings, "frontend_origin", "https://app.example.test")
        monkeypatch.setattr(settings, "email_backend", "smtp")
        sent: list[dict] = []
        monkeypatch.setattr(outbox_worker, "_send_smtp_email", lambda to_email, subject, body: sent.append(
            {"to": to_email, "subject": subject, "body": body}
        ))
        return sent

    def test_explanation_requested_mail_has_only_a_link(self, monkeypatch):
        sent = self._smtp(monkeypatch)
        monkeypatch.setattr(outbox_worker, "_resolve_user_email", lambda user_id: "coord@example.test")
        outbox_worker.complaint_explanation_requested_handler(
            {"complaint_id": "c-1", "respondent_user_id": "u-1"}, outbox_id=1
        )
        assert len(sent) == 1
        assert sent[0]["to"] == "coord@example.test"
        assert "https://app.example.test/sikayetlerim/c-1" in sent[0]["body"]

    def test_escalated_mail_goes_to_resolved_members(self, monkeypatch):
        sent = self._smtp(monkeypatch)
        calls = []
        monkeypatch.setattr(
            outbox_worker,
            "_resolve_complaint_escalation_emails",
            lambda target_type, target_id, excluded_user_id: calls.append((target_type, target_id, excluded_user_id))
            or ["a@example.test", "b@example.test"],
        )
        outbox_worker.complaint_escalated_handler(
            {"complaint_id": "c-2", "target_type": "INSTITUTION", "target_id": "i-1", "excluded_user_id": "u-1"}, outbox_id=2
        )
        assert calls == [("INSTITUTION", "i-1", "u-1")]
        assert [m["to"] for m in sent] == ["a@example.test", "b@example.test"]

    def test_closed_mail_goes_to_talent(self, monkeypatch):
        sent = self._smtp(monkeypatch)
        monkeypatch.setattr(outbox_worker, "_resolve_talent_user_email", lambda talent_id: "talent@example.test")
        outbox_worker.complaint_closed_handler(
            {"complaint_id": "c-3", "talent_id": "t-1", "outcome": "UPHELD"}, outbox_id=3
        )
        assert sent[0]["to"] == "talent@example.test"
        assert "c-3" in sent[0]["body"]

    def test_escalation_recipients_exclude_respondent(self, client, session, w):
        """Real query: other COORDINATOR/ADMIN members of the institution, not the respondent."""
        # The resolver opens its own connection; its statement is run here on the test session.
        stmt = outbox_worker._complaint_escalation_emails_stmt("INSTITUTION", str(w.institution.id), str(w.coord.id))
        emails = session.execute(stmt).scalars().all()
        assert sorted(emails) == sorted([w.coord2.email, w.inst_admin.email])

        session.add(
            OrganizationMember(organization_id=w.org.id, user_id=w.coord2.id, role="MEMBER", status="ACTIVE")
        )
        session.flush()
        stmt = outbox_worker._complaint_escalation_emails_stmt("ORGANIZATION", str(w.org.id), str(uuid.uuid4()))
        assert session.execute(stmt).scalars().all() == [w.org_admin.email]

    def test_payloads_carry_no_text(self, client, session, w):
        created = open_complaint(client, w)
        to_escalated(client, w, created["id"])
        transition(client, w, created["id"], "UPHOLD", reason="Gizli gerekçe metni.")
        for row in _topics(session, created["id"]):
            flat = str(row)
            assert "Stajım" not in flat and "Yoğunluk" not in flat and "Gizli gerekçe" not in flat
