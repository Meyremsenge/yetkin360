"""Add attestations immutability trigger and skill_signals revoke exception.

PLAN 2.10 (YET-72): Attestation revoke feature requires:
1. New trigger on attestations table: prevent UPDATE/DELETE except revoked_at/revoke_reason
2. Updated trigger on skill_signals: allow superseded_by_id update (set-once pattern)

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-09-24

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add attestations trigger + update skill_signals trigger."""
    # Create attestations immutability trigger function
    op.execute(
        """
        CREATE FUNCTION attestations_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'attestations is append-only (delete forbidden)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          -- Allow only revoked_at and revoke_reason to change
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.engagement_id IS DISTINCT FROM OLD.engagement_id
             OR NEW.talent_id IS DISTINCT FROM OLD.talent_id
             OR NEW.subject_type IS DISTINCT FROM OLD.subject_type
             OR NEW.subject_id IS DISTINCT FROM OLD.subject_id
             OR NEW.claim_type IS DISTINCT FROM OLD.claim_type
             OR NEW.requested_claim_type IS DISTINCT FROM OLD.requested_claim_type
             OR NEW.attestor_user_id IS DISTINCT FROM OLD.attestor_user_id
             OR NEW.attestor_org_id IS DISTINCT FROM OLD.attestor_org_id
             OR NEW.skill_id IS DISTINCT FROM OLD.skill_id
             OR NEW.statement IS DISTINCT FROM OLD.statement
             OR NEW.downgrade_reasons IS DISTINCT FROM OLD.downgrade_reasons
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
          THEN
            RAISE EXCEPTION 'attestations: only revoked_at/revoke_reason may be updated (append-only exception)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger on attestations
    op.execute(
        """
        CREATE TRIGGER attestations_immutable
          BEFORE UPDATE OR DELETE ON attestations
          FOR EACH ROW
          EXECUTE FUNCTION attestations_before_update_delete();
        """
    )

    # Update skill_signals trigger: allow superseded_by_id change (set-once pattern)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION skill_signals_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'skill_signals is append-only (immutable trigger)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          -- Allow only superseded_by_id to change (set-once: NULL → value, not value → another value)
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.talent_id IS DISTINCT FROM OLD.talent_id
             OR NEW.skill_id IS DISTINCT FROM OLD.skill_id
             OR NEW.source_type IS DISTINCT FROM OLD.source_type
             OR NEW.source_id IS DISTINCT FROM OLD.source_id
             OR NEW.strength IS DISTINCT FROM OLD.strength
             OR NEW.attested_by_org_id IS DISTINCT FROM OLD.attested_by_org_id
             OR NEW.occurred_at IS DISTINCT FROM OLD.occurred_at
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR (OLD.superseded_by_id IS NOT NULL AND NEW.superseded_by_id IS DISTINCT FROM OLD.superseded_by_id)
          THEN
            RAISE EXCEPTION 'skill_signals is append-only (immutable trigger) except superseded_by_id (set-once)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    """Downgrade: Remove attestations trigger + restore skill_signals original trigger."""
    # Drop attestations trigger and function
    op.execute("DROP TRIGGER IF EXISTS attestations_immutable ON attestations;")
    op.execute("DROP FUNCTION IF EXISTS attestations_before_update_delete();")

    # Restore skill_signals trigger to original (no superseded_by_id exception)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION skill_signals_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'skill_signals is append-only (immutable trigger)'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RAISE EXCEPTION 'skill_signals is append-only (immutable trigger)'
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
