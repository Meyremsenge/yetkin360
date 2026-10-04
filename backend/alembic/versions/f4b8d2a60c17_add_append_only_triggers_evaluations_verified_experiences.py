"""Add append-only triggers for evaluations, evaluation_items, verified_experiences.

YET-214 (VER-01): CLAUDE.md lists these tables as append-only, but only
attestations, skill_signals and audit_events had a DB-level trigger.

- evaluations, evaluation_items: UPDATE and DELETE forbidden.
- verified_experiences: DELETE forbidden; UPDATE allowed only for `visibility`
  (CLAUDE.md exception). Every other column is protected with IS DISTINCT FROM,
  following the attestations trigger (l3m4n5o6p7q8).

Row triggers also fire for ON DELETE CASCADE, so deleting an engagement cannot
silently erase evaluations or verified experiences.

Revision ID: f4b8d2a60c17
Revises: e2a7c4d91b38
Create Date: 2026-10-02

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "f4b8d2a60c17"
down_revision = "e2a7c4d91b38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # evaluations: fully append-only
    op.execute(
        """
        CREATE FUNCTION evaluations_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'evaluations is append-only (% forbidden)', lower(TG_OP)
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluations_immutable
          BEFORE UPDATE OR DELETE ON evaluations
          FOR EACH ROW
          EXECUTE FUNCTION evaluations_before_update_delete();
        """
    )

    # evaluation_items: fully append-only
    op.execute(
        """
        CREATE FUNCTION evaluation_items_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'evaluation_items is append-only (% forbidden)', lower(TG_OP)
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER evaluation_items_immutable
          BEFORE UPDATE OR DELETE ON evaluation_items
          FOR EACH ROW
          EXECUTE FUNCTION evaluation_items_before_update_delete();
        """
    )

    # verified_experiences: append-only except visibility
    op.execute(
        """
        CREATE FUNCTION verified_experiences_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'verified_experiences is append-only (delete forbidden)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          -- Allow only visibility to change
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.talent_id IS DISTINCT FROM OLD.talent_id
             OR NEW.engagement_id IS DISTINCT FROM OLD.engagement_id
             OR NEW.organization_name_snapshot IS DISTINCT FROM OLD.organization_name_snapshot
             OR NEW.role_snapshot IS DISTINCT FROM OLD.role_snapshot
             OR NEW.started_on_snapshot IS DISTINCT FROM OLD.started_on_snapshot
             OR NEW.ended_on_snapshot IS DISTINCT FROM OLD.ended_on_snapshot
             OR NEW.institution_name_snapshot IS DISTINCT FROM OLD.institution_name_snapshot
             OR NEW.claim_type IS DISTINCT FROM OLD.claim_type
             OR NEW.public_token IS DISTINCT FROM OLD.public_token
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
          THEN
            RAISE EXCEPTION 'verified_experiences is append-only (only visibility may be updated)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER verified_experiences_immutable
          BEFORE UPDATE OR DELETE ON verified_experiences
          FOR EACH ROW
          EXECUTE FUNCTION verified_experiences_before_update_delete();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS verified_experiences_immutable ON verified_experiences;")
    op.execute("DROP FUNCTION IF EXISTS verified_experiences_before_update_delete();")
    op.execute("DROP TRIGGER IF EXISTS evaluation_items_immutable ON evaluation_items;")
    op.execute("DROP FUNCTION IF EXISTS evaluation_items_before_update_delete();")
    op.execute("DROP TRIGGER IF EXISTS evaluations_immutable ON evaluations;")
    op.execute("DROP FUNCTION IF EXISTS evaluations_before_update_delete();")
