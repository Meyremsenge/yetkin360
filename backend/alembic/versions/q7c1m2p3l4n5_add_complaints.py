"""Add complaints, complaint_events, complaint_attachments (sikayet-backend, C1).

- complaints: workflow row. DELETE forbidden; a terminal status
  (DISMISSED/RESOLVED/UPHELD) can never change again (AC-S14: an UPHELD decision
  is irreversible, a correction is a new event/complaint).
- complaint_events: append-only timeline, UPDATE/DELETE forbidden by trigger.
- complaint_attachments: documents shared with the platform admin.
- One open complaint per subject: partial UNIQUE indexes (AC-14 ALREADY_OPEN).

Row triggers also fire for ON DELETE CASCADE; TRUNCATE (scripts/reset_demo) does
not fire them, which is the intended demo-reset escape hatch.

Revision ID: q7c1m2p3l4n5
Revises: e7b1d9a3c604
Create Date: 2026-10-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q7c1m2p3l4n5"
down_revision: Union[str, None] = "e7b1d9a3c604"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OPEN = "status NOT IN ('DISMISSED','RESOLVED','UPHELD')"


def upgrade() -> None:
    op.create_table(
        "complaints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("talent_id", sa.UUID(), nullable=False),
        sa.Column("subject_type", sa.String(length=30), nullable=False),
        sa.Column("engagement_id", sa.UUID(), nullable=True),
        sa.Column("certificate_check_id", sa.UUID(), nullable=True),
        sa.Column("subject_state", sa.String(length=30), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_institution_id", sa.UUID(), nullable=True),
        sa.Column("target_organization_id", sa.UUID(), nullable=True),
        sa.Column("respondent_user_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="OPEN", nullable=False),
        sa.Column("request_note", sa.Text(), nullable=True),
        sa.Column("explanation_text", sa.Text(), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("explanation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('OPEN','UNDER_REVIEW','EXPLANATION_REQUESTED','EXPLANATION_SUBMITTED',"
            "'ESCALATED','DISMISSED','RESOLVED','UPHELD')",
            name="ck_complaints_status",
        ),
        sa.CheckConstraint(
            "(subject_type = 'ENGAGEMENT' AND engagement_id IS NOT NULL AND certificate_check_id IS NULL) OR "
            "(subject_type = 'CERTIFICATE_CHECK' AND certificate_check_id IS NOT NULL AND engagement_id IS NULL)",
            name="ck_complaints_subject",
        ),
        sa.CheckConstraint(
            "(target_type = 'INSTITUTION' AND target_institution_id IS NOT NULL AND target_organization_id IS NULL) OR "
            "(target_type = 'ORGANIZATION' AND target_organization_id IS NOT NULL AND target_institution_id IS NULL)",
            name="ck_complaints_target",
        ),
        sa.CheckConstraint("char_length(description) BETWEEN 10 AND 4000", name="ck_complaints_description_length"),
        sa.CheckConstraint(
            "(status IN ('DISMISSED','RESOLVED','UPHELD')) = (closed_at IS NOT NULL)", name="ck_complaints_closed_at"
        ),
        sa.CheckConstraint("status <> 'DISMISSED' OR resolution_reason IS NOT NULL", name="ck_complaints_dismiss_reason"),
        sa.CheckConstraint("version >= 1", name="ck_complaints_version"),
        sa.ForeignKeyConstraint(["talent_id"], ["talent_profiles.id"]),
        sa.ForeignKeyConstraint(["engagement_id"], ["engagements.id"]),
        sa.ForeignKeyConstraint(["certificate_check_id"], ["certificate_checks.id"]),
        sa.ForeignKeyConstraint(["target_institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["target_organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["respondent_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_complaints_open_engagement",
        "complaints",
        ["engagement_id"],
        unique=True,
        postgresql_where=sa.text(f"engagement_id IS NOT NULL AND {_OPEN}"),
    )
    op.create_index(
        "uq_complaints_open_certificate_check",
        "complaints",
        ["certificate_check_id"],
        unique=True,
        postgresql_where=sa.text(f"certificate_check_id IS NOT NULL AND {_OPEN}"),
    )
    op.create_index("ix_complaints_status_created_at", "complaints", ["status", "created_at"])
    op.create_index("ix_complaints_talent_created_at", "complaints", ["talent_id", "created_at"])
    op.create_index("ix_complaints_respondent_user_id", "complaints", ["respondent_user_id"])
    op.create_index(
        "ix_complaints_upheld_institution",
        "complaints",
        ["target_institution_id"],
        postgresql_where=sa.text("status = 'UPHELD'"),
    )
    op.create_index(
        "ix_complaints_upheld_organization",
        "complaints",
        ["target_organization_id"],
        postgresql_where=sa.text("status = 'UPHELD'"),
    )

    op.create_table(
        "complaint_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("complaint_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("actor_role", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("actor_role IN ('TALENT','ADMIN','RESPONDENT')", name="ck_complaint_events_actor_role"),
        sa.CheckConstraint(
            "event_type IN ('CREATED','REVIEW_STARTED','DISMISSED','EXPLANATION_REQUESTED','EXPLANATION_SUBMITTED',"
            "'EXPLANATION_ACCEPTED','EXPLANATION_REJECTED','RESOLVED','UPHELD','ATTACHMENT_ADDED')",
            name="ck_complaint_events_event_type",
        ),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_complaint_events_complaint_created_at", "complaint_events", ["complaint_id", "created_at"])

    op.create_table(
        "complaint_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("complaint_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_etag", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "mime_type IN ('application/pdf','image/jpeg','image/png')", name="ck_complaint_attachments_mime_type"
        ),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="ck_complaint_attachments_size"),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_complaint_attachments_storage_key", "complaint_attachments", ["storage_key"], unique=True)
    op.create_index("ix_complaint_attachments_complaint_id", "complaint_attachments", ["complaint_id"])

    op.execute(
        """
        CREATE FUNCTION complaint_events_before_update_delete() RETURNS TRIGGER AS $$
        BEGIN
          RAISE EXCEPTION 'complaint_events is append-only (% forbidden)', lower(TG_OP)
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER complaint_events_immutable
          BEFORE UPDATE OR DELETE ON complaint_events
          FOR EACH ROW
          EXECUTE FUNCTION complaint_events_before_update_delete();
        """
    )
    op.execute(
        """
        CREATE FUNCTION complaints_guard() RETURNS TRIGGER AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'complaints rows are never deleted'
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          IF OLD.status IN ('DISMISSED','RESOLVED','UPHELD') AND NEW.status IS DISTINCT FROM OLD.status THEN
            RAISE EXCEPTION 'complaint decision is final (status % cannot change)', OLD.status
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER complaints_guard
          BEFORE UPDATE OR DELETE ON complaints
          FOR EACH ROW
          EXECUTE FUNCTION complaints_guard();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS complaints_guard ON complaints;")
    op.execute("DROP FUNCTION IF EXISTS complaints_guard();")
    op.execute("DROP TRIGGER IF EXISTS complaint_events_immutable ON complaint_events;")
    op.execute("DROP FUNCTION IF EXISTS complaint_events_before_update_delete();")
    op.drop_index("ix_complaint_attachments_complaint_id", table_name="complaint_attachments")
    op.drop_index("uq_complaint_attachments_storage_key", table_name="complaint_attachments")
    op.drop_table("complaint_attachments")
    op.drop_index("ix_complaint_events_complaint_created_at", table_name="complaint_events")
    op.drop_table("complaint_events")
    op.drop_index("ix_complaints_upheld_organization", table_name="complaints")
    op.drop_index("ix_complaints_upheld_institution", table_name="complaints")
    op.drop_index("ix_complaints_respondent_user_id", table_name="complaints")
    op.drop_index("ix_complaints_talent_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_created_at", table_name="complaints")
    op.drop_index("uq_complaints_open_certificate_check", table_name="complaints")
    op.drop_index("uq_complaints_open_engagement", table_name="complaints")
    op.drop_table("complaints")
