"""
Certificate check authorization tests (PLAN 3.55).

- POST /evidence/{id}/request-certificate-check: yalnız sahibi, yalnız
  CERTIFICATE+CLEAN, tekrar istek 409.
- GET /engagements/{id}/certificate-checks: scoped_evidence()'ın dar istisnası
  — ilgili talent + engagement'ın org admin'i (koordinatör-eşdeğeri) görür;
  plain ORG_MEMBER boş liste alır; scope dışı 404.
- POST /certificate-checks/{id}/resolve: yalnız org admin karar verebilir
  (AI asla), talent/ilgisiz kullanıcı 404, tekrar karar 409.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models import (
    AuditEvent,
    CertificateCheck,
    Deliverable,
    Engagement,
    Evidence,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)


@pytest.fixture
def talent_user_cc(session):
    user = User(email="cc-talent@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def other_talent_user_cc(session):
    user = User(email="cc-other-talent@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_admin_user_cc(session):
    user = User(email="cc-org-admin@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_member_user_cc(session):
    user = User(email="cc-org-member@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def unrelated_user_cc(session):
    user = User(email="cc-unrelated@example.com", password_hash="hash")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def org_cc(session):
    org = Organization(name="Cert Authz Org", verification_level="T2")
    session.add(org)
    session.flush()
    return org


@pytest.fixture
def org_admin_membership_cc(session, org_cc, org_admin_user_cc):
    member = OrganizationMember(organization_id=org_cc.id, user_id=org_admin_user_cc.id, role="ADMIN")
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def org_member_membership_cc(session, org_cc, org_member_user_cc):
    member = OrganizationMember(organization_id=org_cc.id, user_id=org_member_user_cc.id, role="MEMBER")
    session.add(member)
    session.flush()
    return member


@pytest.fixture
def talent_profile_cc(session, talent_user_cc):
    profile = TalentProfile(user_id=talent_user_cc.id, full_name="Cert Test Talent", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def other_talent_profile_cc(session, other_talent_user_cc):
    profile = TalentProfile(user_id=other_talent_user_cc.id, full_name="Other Talent", visibility="PRIVATE")
    session.add(profile)
    session.flush()
    return profile


@pytest.fixture
def engagement_cc(session, talent_profile_cc, org_cc):
    engagement = Engagement(
        talent_id=talent_profile_cc.id,
        organization_id=org_cc.id,
        institution_id=None,
        kind="SHORT_PROJECT",
        title="Cert Authz Engagement",
        status="ACTIVE",
        version=1,
    )
    session.add(engagement)
    session.flush()
    return engagement


@pytest.fixture
def deliverable_cc(session, engagement_cc, talent_user_cc):
    deliverable = Deliverable(
        engagement_id=engagement_cc.id,
        title="Cert Deliverable",
        submitted_by_user_id=talent_user_cc.id,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(deliverable)
    session.flush()
    return deliverable


@pytest.fixture
def certificate_evidence_cc(session, talent_profile_cc, deliverable_cc):
    ev = Evidence(
        owner_talent_id=talent_profile_cc.id,
        kind="CERTIFICATE",
        storage_key=f"evidence/{talent_profile_cc.id}/{uuid.uuid4()}.png",
        mime_type="image/png",
        size_bytes=100,
        scan_status="CLEAN",
        deliverable_id=deliverable_cc.id,
    )
    session.add(ev)
    session.flush()
    return ev


@pytest.fixture
def pending_evidence_cc(session, talent_profile_cc, deliverable_cc):
    """Henüz CLEAN olmamış evidence — 409 EVIDENCE_NOT_CLEAN senaryosu için."""
    ev = Evidence(
        owner_talent_id=talent_profile_cc.id,
        kind="CERTIFICATE",
        storage_key=f"evidence/{talent_profile_cc.id}/{uuid.uuid4()}.png",
        mime_type="image/png",
        size_bytes=100,
        scan_status="PENDING",
        deliverable_id=deliverable_cc.id,
    )
    session.add(ev)
    session.flush()
    return ev


@pytest.fixture
def document_evidence_cc(session, talent_profile_cc, deliverable_cc):
    """CERTIFICATE olmayan bir evidence — 422 NOT_CERTIFICATE_KIND senaryosu için."""
    ev = Evidence(
        owner_talent_id=talent_profile_cc.id,
        kind="DOCUMENT",
        storage_key=f"evidence/{talent_profile_cc.id}/{uuid.uuid4()}.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        scan_status="CLEAN",
        deliverable_id=deliverable_cc.id,
    )
    session.add(ev)
    session.flush()
    return ev


@pytest.fixture
def existing_check_cc(session, certificate_evidence_cc):
    check = CertificateCheck(evidence_id=certificate_evidence_cc.id)
    session.add(check)
    session.flush()
    return check


class TestRequestCertificateCheck:
    def test_owner_can_request_201(self, client, talent_user_cc, certificate_evidence_cc):
        response = client.post(
            f"/evidence/{certificate_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["evidence_id"] == str(certificate_evidence_cc.id)
        assert data["decision"] == "PENDING"
        assert data["status"] == "PENDING"

    def test_non_owner_gets_404(self, client, other_talent_user_cc, certificate_evidence_cc):
        response = client.post(
            f"/evidence/{certificate_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(other_talent_user_cc.id)},
        )
        assert response.status_code == 404, response.text

    def test_non_certificate_kind_gets_422(self, client, talent_user_cc, document_evidence_cc):
        response = client.post(
            f"/evidence/{document_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "NOT_CERTIFICATE_KIND"

    def test_not_clean_evidence_gets_409(self, client, talent_user_cc, pending_evidence_cc):
        response = client.post(
            f"/evidence/{pending_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "EVIDENCE_NOT_CLEAN"

    def test_repeated_request_gets_409(self, client, talent_user_cc, certificate_evidence_cc):
        first = client.post(
            f"/evidence/{certificate_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert first.status_code == 201

        second = client.post(
            f"/evidence/{certificate_evidence_cc.id}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert second.status_code == 409, second.text
        assert second.json()["code"] == "ALREADY_REQUESTED"

    def test_unknown_evidence_gets_404(self, client, talent_user_cc):
        response = client.post(
            f"/evidence/{uuid.uuid4()}/request-certificate-check",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 404, response.text


class TestListEngagementCertificateChecks:
    def test_subject_talent_sees_own_check(
        self, client, talent_user_cc, engagement_cc, existing_check_cc
    ):
        response = client.get(
            f"/engagements/{engagement_cc.id}/certificate-checks",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["items"]}
        assert str(existing_check_cc.id) in ids

    def test_org_admin_sees_the_check(
        self, client, org_admin_user_cc, org_admin_membership_cc, engagement_cc, existing_check_cc
    ):
        response = client.get(
            f"/engagements/{engagement_cc.id}/certificate-checks",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
        )
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()["items"]}
        assert str(existing_check_cc.id) in ids

    def test_plain_org_member_sees_empty_list(
        self, client, org_member_user_cc, org_member_membership_cc, engagement_cc, existing_check_cc
    ):
        response = client.get(
            f"/engagements/{engagement_cc.id}/certificate-checks",
            headers={"X-Debug-User-Id": str(org_member_user_cc.id)},
        )
        assert response.status_code == 200, response.text
        assert response.json()["items"] == []

    def test_unrelated_user_gets_404(self, client, unrelated_user_cc, engagement_cc, existing_check_cc):
        response = client.get(
            f"/engagements/{engagement_cc.id}/certificate-checks",
            headers={"X-Debug-User-Id": str(unrelated_user_cc.id)},
        )
        assert response.status_code == 404, response.text

    def test_unknown_engagement_gets_404(self, client, talent_user_cc):
        response = client.get(
            f"/engagements/{uuid.uuid4()}/certificate-checks",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
        )
        assert response.status_code == 404, response.text


class TestResolveCertificateCheck:
    def test_org_admin_confirms_and_audit_logged(
        self, client, session, org_admin_user_cc, org_admin_membership_cc, engagement_cc, existing_check_cc
    ):
        response = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "CONFIRMED"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["decision"] == "CONFIRMED"

        session.refresh(existing_check_cc)
        assert existing_check_cc.decision == "CONFIRMED"
        assert existing_check_cc.decided_by_user_id == org_admin_user_cc.id
        assert existing_check_cc.decided_at is not None

        event = (
            session.query(AuditEvent)
            .filter_by(action="CERTIFICATE_CHECK_RESOLVED", subject_id=existing_check_cc.id)
            .first()
        )
        assert event is not None

    def test_org_admin_rejects(
        self, client, session, org_admin_user_cc, org_admin_membership_cc, engagement_cc, existing_check_cc
    ):
        response = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "REJECTED"},
        )
        assert response.status_code == 200, response.text
        session.refresh(existing_check_cc)
        assert existing_check_cc.decision == "REJECTED"

    def test_subject_talent_cannot_decide_404(
        self, client, talent_user_cc, engagement_cc, existing_check_cc
    ):
        """Talent kendi talebini GÖRÜR ama KARAR VEREMEZ — AI de karar vermez, yalnız koordinatör."""
        response = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(talent_user_cc.id)},
            json={"decision": "CONFIRMED"},
        )
        assert response.status_code == 404, response.text

    def test_unrelated_user_gets_404(self, client, unrelated_user_cc, existing_check_cc):
        response = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(unrelated_user_cc.id)},
            json={"decision": "CONFIRMED"},
        )
        assert response.status_code == 404, response.text

    def test_already_resolved_gets_409(
        self, client, org_admin_user_cc, org_admin_membership_cc, engagement_cc, existing_check_cc
    ):
        first = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "CONFIRMED"},
        )
        assert first.status_code == 200

        second = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "REJECTED"},
        )
        assert second.status_code == 409, second.text

    def test_invalid_decision_value_gets_422(
        self, client, org_admin_user_cc, org_admin_membership_cc, engagement_cc, existing_check_cc
    ):
        response = client.post(
            f"/certificate-checks/{existing_check_cc.id}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "MAYBE"},
        )
        assert response.status_code == 422, response.text

    def test_unknown_check_id_gets_404(self, client, org_admin_user_cc, org_admin_membership_cc):
        response = client.post(
            f"/certificate-checks/{uuid.uuid4()}/resolve",
            headers={"X-Debug-User-Id": str(org_admin_user_cc.id)},
            json={"decision": "CONFIRMED"},
        )
        assert response.status_code == 404, response.text
