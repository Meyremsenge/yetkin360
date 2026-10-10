"""Shared world for the complaint tests (sikayet-backend).

One institution with two coordinators (the earliest one is the derived respondent)
and an ADMIN, an unrelated institution, one organization with an ADMIN, two
talents and an engagement that has been PENDING_APPROVAL for 10 days.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models import (
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)

PDF_BYTES = b"%PDF-1.7\n" + b"0" * 200
EXE_BYTES = b"MZ\x90\x00" + b"0" * 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(session, tag: str, **kw) -> User:
    user = User(email=f"{tag}-{uuid.uuid4().hex[:8]}@example.com", password_hash="h", **kw)
    session.add(user)
    session.flush()
    return user


def make_world(session) -> SimpleNamespace:
    w = SimpleNamespace()
    w.institution = Institution(name="Şikayet Üniversitesi")
    w.other_institution = Institution(name="İlgisiz Üniversite")
    w.org = Organization(name="Şikayet Yazılım A.Ş.", legal_id=f"CMP-{uuid.uuid4().hex[:8]}")
    session.add_all([w.institution, w.other_institution, w.org])
    session.flush()

    w.coord = _user(session, "coord")  # derived respondent (earliest coordinator)
    w.coord2 = _user(session, "coord2")
    w.inst_admin = _user(session, "instadmin")
    w.unrelated_coord = _user(session, "unrel")
    w.org_admin = _user(session, "orgadmin")
    w.admin = _user(session, "padmin", is_platform_admin=True)
    w.user_a = _user(session, "talenta")
    w.user_b = _user(session, "talentb")

    base = _now() - timedelta(days=30)
    session.add_all(
        [
            InstitutionMember(institution_id=w.institution.id, user_id=w.coord.id, role="COORDINATOR", created_at=base),
            InstitutionMember(
                institution_id=w.institution.id, user_id=w.coord2.id, role="COORDINATOR", created_at=base + timedelta(days=1)
            ),
            InstitutionMember(
                institution_id=w.institution.id, user_id=w.inst_admin.id, role="ADMIN", created_at=base + timedelta(days=2)
            ),
            InstitutionMember(institution_id=w.other_institution.id, user_id=w.unrelated_coord.id, role="COORDINATOR"),
            OrganizationMember(organization_id=w.org.id, user_id=w.org_admin.id, role="ADMIN", status="ACTIVE"),
        ]
    )
    w.talent_a = TalentProfile(user_id=w.user_a.id, full_name="Ayşe Öğrenci", institution_id=w.institution.id)
    w.talent_b = TalentProfile(user_id=w.user_b.id, full_name="Burak Öğrenci", institution_id=w.institution.id)
    session.add_all([w.talent_a, w.talent_b])
    session.flush()

    w.engagement = add_engagement(session, w, w.talent_a, status="PENDING_APPROVAL", days_ago=10)
    return w


def add_engagement(session, w, talent, status: str = "PENDING_APPROVAL", days_ago: int = 10, **kw) -> Engagement:
    values = dict(
        talent_id=talent.id,
        organization_id=w.org.id,
        institution_id=w.institution.id,
        kind="INTERNSHIP",
        title="Yaz stajı",
        status=status,
        created_at=_now() - timedelta(days=days_ago),
    )
    values.update(kw)
    engagement = Engagement(**values)
    session.add(engagement)
    session.flush()
    return engagement


def h(user: User) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


def open_complaint(client, w, engagement=None, user=None) -> dict:
    engagement = engagement or w.engagement
    response = client.post(
        "/complaints",
        headers=h(user or w.user_a),
        json={
            "subject_type": "ENGAGEMENT",
            "subject_id": str(engagement.id),
            "description": "Stajım 10 gündür onay bekliyor, yanıt alamadım.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def transition(client, w, complaint_id: str, action: str, **body):
    return client.post(
        f"/admin/complaints/{complaint_id}/transitions", headers=h(w.admin), json={"action": action, **body}
    )


def to_explanation_requested(client, w, complaint_id: str) -> None:
    r = transition(client, w, complaint_id, "REQUEST_EXPLANATION", note="Lütfen gecikmeyi açıklayın.")
    assert r.status_code == 200, r.text


def to_escalated(client, w, complaint_id: str) -> None:
    to_explanation_requested(client, w, complaint_id)
    r = client.post(f"/complaints/{complaint_id}/explanation", headers=h(w.coord), json={"text": "Yoğunluk vardı."})
    assert r.status_code == 200, r.text
    r = transition(client, w, complaint_id, "REJECT_EXPLANATION")
    assert r.status_code == 200, r.text


def fake_storage(monkeypatch, data: bytes = PDF_BYTES, etag: str = "etag-1") -> dict:
    """Replace every network call the complaint service makes with an in-memory fake."""
    from app.services import complaint as svc
    from app.services.storage import StoredObject

    state = {"data": data, "etag": etag}
    monkeypatch.setattr(
        svc,
        "generate_presigned_post",
        lambda bucket, object_key, content_type, size_bytes, ttl: {"url": "https://s3.test/b", "fields": {"key": object_key}},
    )
    monkeypatch.setattr(
        svc,
        "fetch_object",
        lambda bucket, object_key, max_bytes: None
        if state["data"] is None
        else StoredObject(data=state["data"], etag=state["etag"]),
    )
    monkeypatch.setattr(svc, "head_object_etag", lambda bucket, object_key: state["etag"])
    monkeypatch.setattr(
        svc, "generate_presigned_get_url", lambda bucket, object_key, ttl: f"https://s3.test/get/{object_key}"
    )
    return state


def add_attachment(client, w, complaint_id: str, user=None, data: bytes = PDF_BYTES, mime: str = "application/pdf"):
    user = user or w.user_a
    r = client.post(
        f"/complaints/{complaint_id}/attachments/upload-url",
        headers=h(user),
        json={"filename": "kanit.pdf", "content_type": mime, "size_bytes": len(data)},
    )
    assert r.status_code == 200, r.text
    key = r.json()["object_key"]
    return client.post(
        f"/complaints/{complaint_id}/attachments",
        headers=h(user),
        json={"storage_key": key, "mime_type": mime, "size_bytes": len(data)},
    )
