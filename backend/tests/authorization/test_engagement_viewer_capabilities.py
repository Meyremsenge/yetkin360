"""
SPRINT A — viewer capabilities on GET /engagements/{id} and roles on GET /me.

The detail response's `viewer` block must advertise exactly what the write
endpoints accept, so the UI never renders a button the server refuses:

- AC-2: for 6 actors x every status (with and without an institution):
        to in viewer.allowed_transitions  <=>  POST /transitions is 2xx
- AC-3: can_evaluate <=> POST /evaluation (ORG_TO_TALENT) is 2xx,
        can_attest <=> POST /attestations is 2xx
        (plus can_add_task / can_add_deliverable against their endpoints)
- AC-S1: a talent who is also an org member sees relation=SUBJECT, no org actions
- AC-S2: out-of-scope engagement is 404 and the body carries no viewer
- AC-S3: /me never returns another member's role or unit
- threat-model additions: attest_blocker only for a viewer who may seal;
  an unverified e-mail gets no actions (every write endpoint would 401).

Each write is probed on a fresh engagement so one success never changes the
state another probe sees.
"""

from datetime import date, datetime, timezone

import pytest

from app.models import (
    Deliverable,
    Engagement,
    Institution,
    InstitutionMember,
    Organization,
    OrganizationMember,
    TalentProfile,
    User,
)

ACTORS = ["talent", "org_admin", "org_member", "coordinator", "inst_admin", "outsider"]
# (status, has_deliverable)
STATES = [
    ("DRAFT", False),
    ("PENDING_APPROVAL", False),
    ("ACTIVE", False),
    ("ACTIVE", True),
    ("PENDING_EVALUATION", True),
    ("EVALUATED", True),
    ("REJECTED", False),
    ("CANCELLED", False),
    ("VERIFIED", True),
]
TARGETS = ["PENDING_APPROVAL", "ACTIVE", "REJECTED", "CANCELLED", "PENDING_EVALUATION", "EVALUATED", "VERIFIED"]


def _user(session, email: str) -> User:
    user = User(email=email, password_hash="x")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def world(session):
    """One institution, one organization (T2), one actor per relation, plus an outsider org."""
    inst = Institution(name="Galata Teknik", verification_level="T2")
    org = Organization(name="Lale Yazılım", verification_level="T2")
    other_org = Organization(name="Başka A.Ş.", verification_level="T2")
    session.add_all([inst, org, other_org])
    session.flush()

    users = {name: _user(session, f"{name}@viewer.test") for name in ACTORS}
    talent = TalentProfile(user_id=users["talent"].id, full_name="Ayşe Yılmaz", institution_id=inst.id)
    session.add_all(
        [
            talent,
            OrganizationMember(organization_id=org.id, user_id=users["org_admin"].id, role="ADMIN"),
            OrganizationMember(
                organization_id=org.id, user_id=users["org_member"].id, role="MEMBER", unit="Yazılım"
            ),
            InstitutionMember(institution_id=inst.id, user_id=users["coordinator"].id, role="COORDINATOR"),
            InstitutionMember(institution_id=inst.id, user_id=users["inst_admin"].id, role="ADMIN"),
            OrganizationMember(organization_id=other_org.id, user_id=users["outsider"].id, role="ADMIN"),
        ]
    )
    session.flush()
    return {"inst": inst, "org": org, "talent": talent, "users": users}


def _engagement(session, world, status: str, with_institution: bool, has_deliverable: bool) -> Engagement:
    engagement = Engagement(
        talent_id=world["talent"].id,
        organization_id=world["org"].id,
        institution_id=world["inst"].id if with_institution else None,
        kind="INTERNSHIP",
        title="Staj",
        status=status,
        started_on=date(2026, 6, 1),
        ended_on=date(2026, 8, 31),
    )
    session.add(engagement)
    session.flush()
    if has_deliverable:
        session.add(
            Deliverable(
                engagement_id=engagement.id,
                title="Rapor",
                submitted_by_user_id=world["users"]["talent"].id,
                submitted_at=datetime.now(timezone.utc),
            )
        )
        session.flush()
    return engagement


def _headers(user: User) -> dict:
    return {"X-Debug-User-Id": str(user.id)}


def _viewer(client, engagement: Engagement, user: User) -> dict | None:
    response = client.get(f"/engagements/{engagement.id}", headers=_headers(user))
    if response.status_code == 404:
        assert "viewer" not in response.text  # AC-S2: nothing beyond the 404
        return None
    assert response.status_code == 200, response.text
    return response.json()["viewer"]


def _ok(response) -> bool:
    return 200 <= response.status_code < 300


@pytest.mark.parametrize("with_institution", [True, False], ids=["kurumlu", "kurumsuz"])
@pytest.mark.parametrize("status,has_deliverable", STATES, ids=[f"{s}{'+teslim' if d else ''}" for s, d in STATES])
@pytest.mark.parametrize("actor", ACTORS)
def test_viewer_matches_write_endpoints(client, session, world, actor, status, has_deliverable, with_institution):
    """AC-2 + AC-3: every advertised capability is exactly what the server accepts."""
    user = world["users"][actor]

    def fresh() -> Engagement:
        return _engagement(session, world, status, with_institution, has_deliverable)

    probe = fresh()
    viewer = _viewer(client, probe, user)
    # Out of scope: a foreign org, or institution staff on an engagement without an institution.
    out_of_scope = actor == "outsider" or (actor in ("coordinator", "inst_admin") and not with_institution)
    if out_of_scope:
        assert viewer is None
        return
    assert viewer is not None

    # AC-2: transitions (reason and recipient supplied, as the UI asks for them)
    for target in TARGETS:
        engagement = fresh()
        response = client.post(
            f"/engagements/{engagement.id}/transitions",
            json={
                "to_status": target,
                "version": engagement.version,
                "reason": "Test gerekçesi",
                "notify_emails": ["coordinator@viewer.test"],
            },
            headers=_headers(user),
        )
        assert (target in viewer["allowed_transitions"]) == _ok(response), (
            f"{actor} {status}->{target}: viewer={viewer['allowed_transitions']} "
            f"POST={response.status_code} {response.text}"
        )
    assert "VERIFIED" not in viewer["allowed_transitions"]
    assert set(viewer["reason_required"]) <= set(viewer["allowed_transitions"])
    assert set(viewer["reason_required"]) == set(viewer["allowed_transitions"]) & {"REJECTED", "CANCELLED"}

    # AC-3: organization-side evaluation
    engagement = fresh()
    response = client.post(
        f"/engagements/{engagement.id}/evaluation",
        json={"direction": "ORG_TO_TALENT", "items": [{"criterion": "İletişim", "rating": "MEETS"}]},
        headers=_headers(user),
    )
    assert viewer["can_evaluate"] == _ok(response), f"{actor} {status} evaluation={response.status_code}"

    # AC-3: seal
    engagement = fresh()
    response = client.post(
        f"/engagements/{engagement.id}/attestations",
        json={"claim_type": "PARTICIPATION", "version": engagement.version},
        headers=_headers(user),
    )
    assert viewer["can_attest"] == _ok(response), f"{actor} {status} attestation={response.status_code}"

    # AC-4 backing: task and deliverable forms
    engagement = fresh()
    response = client.post(
        f"/engagements/{engagement.id}/tasks", json={"title": "Görev"}, headers=_headers(user)
    )
    assert viewer["can_add_task"] == _ok(response), f"{actor} {status} task={response.status_code}"

    engagement = fresh()
    response = client.post(
        f"/engagements/{engagement.id}/deliverables", json={"title": "Teslim"}, headers=_headers(user)
    )
    assert viewer["can_add_deliverable"] == _ok(response), f"{actor} {status} deliverable={response.status_code}"


@pytest.mark.parametrize(
    "actor,expected",
    [
        ("talent", "SUBJECT"),
        ("org_admin", "ORG_ADMIN"),
        ("org_member", "ORG_MEMBER"),
        ("coordinator", "COORDINATOR"),
        ("inst_admin", "INSTITUTION_ADMIN"),
    ],
)
def test_viewer_relation(client, session, world, actor, expected):
    engagement = _engagement(session, world, "DRAFT", True, False)
    assert _viewer(client, engagement, world["users"][actor])["relation"] == expected


def test_subject_who_is_also_org_member_gets_no_org_actions(client, session, world):
    """AC-S1: self-dealing mask — the talent is SUBJECT even as an org admin."""
    session.add(
        OrganizationMember(organization_id=world["org"].id, user_id=world["users"]["talent"].id, role="ADMIN")
    )
    session.flush()
    talent = world["users"]["talent"]

    active = _engagement(session, world, "ACTIVE", True, True)
    viewer = _viewer(client, active, talent)
    assert viewer["relation"] == "SUBJECT"
    assert "CANCELLED" not in viewer["allowed_transitions"]
    assert "PENDING_EVALUATION" not in viewer["allowed_transitions"]
    assert viewer["can_add_deliverable"] is True

    for status in ("PENDING_EVALUATION", "EVALUATED"):
        viewer = _viewer(client, _engagement(session, world, status, False, True), talent)
        assert viewer["can_evaluate"] is False
        assert viewer["can_attest"] is False


def test_out_of_scope_is_404_without_viewer(client, session, world):
    """AC-S2."""
    engagement = _engagement(session, world, "EVALUATED", True, True)
    response = client.get(f"/engagements/{engagement.id}", headers=_headers(world["users"]["outsider"]))
    assert response.status_code == 404
    assert "viewer" not in response.text
    assert "Staj" not in response.text


def test_attest_blocker_only_for_viewer_who_may_seal(client, session, world):
    world["org"].verification_level = "T1"
    session.flush()
    engagement = _engagement(session, world, "EVALUATED", True, True)

    coordinator_view = _viewer(client, engagement, world["users"]["coordinator"])
    assert coordinator_view["can_attest"] is True
    assert coordinator_view["attest_blocker"] == "ORG_NOT_VERIFIED"

    for actor in ("talent", "org_admin", "org_member", "inst_admin"):
        assert _viewer(client, engagement, world["users"][actor])["attest_blocker"] is None


def test_verified_org_has_no_attest_blocker(client, session, world):
    engagement = _engagement(session, world, "EVALUATED", False, True)
    viewer = _viewer(client, engagement, world["users"]["org_admin"])
    assert viewer["can_attest"] is True
    assert viewer["attest_blocker"] is None


def test_evaluation_already_submitted_hides_can_evaluate(client, session, world):
    """Same evaluator, same direction: a second POST would conflict, so no button."""
    from app.models import Evaluation

    engagement = _engagement(session, world, "PENDING_EVALUATION", True, True)
    session.add(
        Evaluation(
            engagement_id=engagement.id,
            evaluator_user_id=world["users"]["org_member"].id,
            direction="ORG_TO_TALENT",
            submitted_at=datetime.now(timezone.utc),
        )
    )
    session.flush()
    assert _viewer(client, engagement, world["users"]["org_member"])["can_evaluate"] is False
    assert _viewer(client, engagement, world["users"]["org_admin"])["can_evaluate"] is True


@pytest.mark.unverified_users
def test_unverified_email_gets_no_actions(client, session, world):
    """Every write endpoint answers 401 EMAIL_NOT_VERIFIED, so nothing is advertised."""
    engagement = _engagement(session, world, "PENDING_APPROVAL", True, False)
    viewer = _viewer(client, engagement, world["users"]["coordinator"])
    assert viewer["relation"] == "COORDINATOR"
    assert viewer["allowed_transitions"] == []
    assert not any(
        viewer[key] for key in ("can_add_task", "can_add_deliverable", "can_evaluate", "can_attest")
    )


# ============================================================================
# GET /me — memberships with role and unit (AC-1, AC-S3)
# ============================================================================


def test_me_returns_every_membership_with_its_role(client, session, world):
    """AC-1: a multi-membership user gets each membership's own role (and org unit)."""
    user = world["users"]["org_member"]
    second_org = Organization(name="Akdeniz Lojistik")
    session.add(second_org)
    session.flush()
    session.add_all(
        [
            OrganizationMember(organization_id=second_org.id, user_id=user.id, role="ADMIN"),
            InstitutionMember(institution_id=world["inst"].id, user_id=user.id, role="SUPERVISOR"),
        ]
    )
    session.flush()

    body = client.get("/me", headers=_headers(user)).json()
    orgs = {o["name"]: o for o in body["organizations"]}
    assert orgs["Lale Yazılım"]["role"] == "MEMBER"
    assert orgs["Lale Yazılım"]["unit"] == "Yazılım"
    assert orgs["Akdeniz Lojistik"]["role"] == "ADMIN"
    assert orgs["Akdeniz Lojistik"]["unit"] is None
    assert body["institutions"] == [{"id": str(world["inst"].id), "name": "Galata Teknik", "role": "SUPERVISOR"}]


def test_me_never_returns_another_members_role_or_unit(client, session, world):
    """AC-S3: the org admin sees their own ADMIN role, not the member's unit; no foreign org."""
    body = client.get("/me", headers=_headers(world["users"]["org_admin"])).json()
    assert body["organizations"] == [
        {"id": str(world["org"].id), "name": "Lale Yazılım", "role": "ADMIN", "unit": None}
    ]
    assert body["institutions"] == []
    assert "Başka A.Ş." not in str(body)

    coordinator = client.get("/me", headers=_headers(world["users"]["coordinator"])).json()
    assert coordinator["organizations"] == []
    assert coordinator["institutions"][0]["role"] == "COORDINATOR"
