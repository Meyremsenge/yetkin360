"""
DB-level append-only guarantees for evaluations, evaluation_items and
verified_experiences (YET-214 / VER-01).

CLAUDE.md: append-only tables forbid UPDATE/DELETE. The only exceptions are
attestations.revoked_at/revoke_reason and verified_experiences.visibility.
These tests talk to real PostgreSQL and bypass the application layer on purpose:
the rule must hold even when a service (or a person with psql) tries to break it.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Engagement,
    Evaluation,
    EvaluationItem,
    Organization,
    TalentProfile,
    User,
    VerifiedExperience,
)


# ---------------------------------------------------------------------------
# Fixtures: one engagement with one evaluation, one item and one verified experience
# ---------------------------------------------------------------------------


@pytest.fixture
def append_only_rows(session):
    org = Organization(name="Append Only Corp", verification_level="T2", status="ACTIVE")
    talent_user = User(email=f"ao-talent-{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    evaluator = User(email=f"ao-eval-{uuid.uuid4().hex[:8]}@example.com", password_hash="h")
    session.add_all([org, talent_user, evaluator])
    session.flush()

    talent = TalentProfile(user_id=talent_user.id, full_name="Append Only Talent", visibility="PRIVATE")
    session.add(talent)
    session.flush()

    engagement = Engagement(
        talent_id=talent.id,
        organization_id=org.id,
        kind="INTERNSHIP",
        title="Append Only Intern",
        status="VERIFIED",
        confidential=False,
    )
    session.add(engagement)
    session.flush()

    evaluation = Evaluation(
        engagement_id=engagement.id,
        evaluator_user_id=evaluator.id,
        direction="ORG_TO_TALENT",
        submitted_at=datetime.now(timezone.utc),
        private_note="original note",
    )
    session.add(evaluation)
    session.flush()

    item = EvaluationItem(
        evaluation_id=evaluation.id,
        criterion="Communication",
        rating="MEETS",
        comment="original comment",
    )
    session.add(item)

    ve = VerifiedExperience(
        talent_id=talent.id,
        engagement_id=engagement.id,
        organization_name_snapshot="Append Only Corp",
        role_snapshot="Append Only Intern",
        started_on_snapshot=date(2025, 6, 1),
        ended_on_snapshot=date(2025, 8, 31),
        claim_type="PARTICIPATION",
        visibility="PRIVATE",
        public_token="tok-" + uuid.uuid4().hex,
    )
    session.add(ve)
    session.flush()

    return {
        "engagement": engagement,
        "evaluation": evaluation,
        "item": item,
        "ve": ve,
    }


def _assert_blocked(session, sql: str, params: dict, table: str) -> None:
    """The statement must be rejected by the immutability trigger of `table`."""
    with pytest.raises(IntegrityError) as exc:
        with session.begin_nested():
            session.execute(text(sql), params)
    assert f"{table} is append-only" in str(exc.value.orig)


# ---------------------------------------------------------------------------
# evaluations
# ---------------------------------------------------------------------------


class TestEvaluationsAppendOnly:
    @pytest.mark.parametrize(
        "set_clause, extra",
        [
            ("private_note = 'tampered'", {}),
            ("direction = 'TALENT_TO_ORG'", {}),
            ("submitted_at = now() - interval '1 year'", {}),
            ("updated_at = now()", {}),
        ],
    )
    def test_update_is_blocked(self, session, append_only_rows, set_clause, extra):
        _assert_blocked(
            session,
            f"UPDATE evaluations SET {set_clause} WHERE id = :id",
            {"id": append_only_rows["evaluation"].id, **extra},
            "evaluations",
        )

    def test_delete_is_blocked(self, session, append_only_rows):
        _assert_blocked(
            session,
            "DELETE FROM evaluations WHERE id = :id",
            {"id": append_only_rows["evaluation"].id},
            "evaluations",
        )

    def test_insert_still_works(self, session, append_only_rows):
        # Append-only means INSERT stays open: a second direction is a new row.
        session.execute(
            text(
                "INSERT INTO evaluations (id, engagement_id, evaluator_user_id, direction, submitted_at) "
                "VALUES (:id, :eng, :usr, 'TALENT_TO_ORG', now())"
            ),
            {
                "id": uuid.uuid4(),
                "eng": append_only_rows["engagement"].id,
                "usr": append_only_rows["evaluation"].evaluator_user_id,
            },
        )


# ---------------------------------------------------------------------------
# evaluation_items
# ---------------------------------------------------------------------------


class TestEvaluationItemsAppendOnly:
    @pytest.mark.parametrize(
        "set_clause",
        ["rating = 'EXCEEDS'", "comment = 'tampered'", "criterion = 'tampered'"],
    )
    def test_update_is_blocked(self, session, append_only_rows, set_clause):
        _assert_blocked(
            session,
            f"UPDATE evaluation_items SET {set_clause} WHERE id = :id",
            {"id": append_only_rows["item"].id},
            "evaluation_items",
        )

    def test_delete_is_blocked(self, session, append_only_rows):
        _assert_blocked(
            session,
            "DELETE FROM evaluation_items WHERE id = :id",
            {"id": append_only_rows["item"].id},
            "evaluation_items",
        )


# ---------------------------------------------------------------------------
# verified_experiences
# ---------------------------------------------------------------------------


class TestVerifiedExperiencesAppendOnly:
    @pytest.mark.parametrize(
        "set_clause",
        [
            "organization_name_snapshot = 'tampered'",
            "role_snapshot = 'tampered'",
            "started_on_snapshot = '2000-01-01'",
            "ended_on_snapshot = '2000-01-01'",
            "institution_name_snapshot = 'tampered'",
            "claim_type = 'COMPETENCE'",
            "public_token = 'tampered'",
            "public_token = NULL",
            "created_at = now() - interval '1 year'",
            "id = gen_random_uuid()",
        ],
    )
    def test_snapshot_columns_are_immutable(self, session, append_only_rows, set_clause):
        _assert_blocked(
            session,
            f"UPDATE verified_experiences SET {set_clause} WHERE id = :id",
            {"id": append_only_rows["ve"].id},
            "verified_experiences",
        )

    def test_visibility_together_with_other_column_is_blocked(self, session, append_only_rows):
        # The visibility exception must not become a side door for other columns.
        _assert_blocked(
            session,
            "UPDATE verified_experiences SET visibility = 'PUBLIC', claim_type = 'COMPETENCE' WHERE id = :id",
            {"id": append_only_rows["ve"].id},
            "verified_experiences",
        )

    def test_delete_is_blocked(self, session, append_only_rows):
        _assert_blocked(
            session,
            "DELETE FROM verified_experiences WHERE id = :id",
            {"id": append_only_rows["ve"].id},
            "verified_experiences",
        )

    def test_visibility_update_is_allowed(self, session, append_only_rows):
        ve_id = append_only_rows["ve"].id
        result = session.execute(
            text("UPDATE verified_experiences SET visibility = 'PUBLIC' WHERE id = :id"),
            {"id": ve_id},
        )
        assert result.rowcount == 1
        stored = session.execute(
            text("SELECT visibility FROM verified_experiences WHERE id = :id"), {"id": ve_id}
        ).scalar_one()
        assert stored == "PUBLIC"

    def test_visibility_check_constraint_still_applies(self, session, append_only_rows):
        # The exception only relaxes the trigger; the CHECK constraint must still reject bad values.
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.execute(
                    text("UPDATE verified_experiences SET visibility = 'EVERYONE' WHERE id = :id"),
                    {"id": append_only_rows["ve"].id},
                )


class TestCascadeCannotEraseHistory:
    def test_deleting_engagement_does_not_wipe_evaluations_or_verified_experiences(
        self, session, append_only_rows
    ):
        # FK is ON DELETE CASCADE; the row triggers must still fire for cascaded deletes.
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.execute(
                    text("DELETE FROM engagements WHERE id = :id"),
                    {"id": append_only_rows["engagement"].id},
                )
