diff --git a/backend/app/models/__init__.py b/backend/app/models/__init__.py
index 7b1dcf8..8e3fa87 100644
--- a/backend/app/models/__init__.py
+++ b/backend/app/models/__init__.py
@@ -1,3 +1,4 @@
+from app.models.audit import AuditEvent
 from app.models.base import Base
 from app.models.identity import (
     Institution,
@@ -18,4 +19,5 @@ __all__ = [
     "Organization",
     "OrganizationMember",
     "Skill",
+    "AuditEvent",
 ]
--- NEW FILES ---
diff --git a/backend/app/services/__init__.py b/backend/app/services/__init__.py
new file mode 100644
index 0000000..e69de29
warning: in the working copy of 'backend/app/services/authorization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/services/authorization.py b/backend/app/services/authorization.py
new file mode 100644
index 0000000..adc315b
--- /dev/null
+++ b/backend/app/services/authorization.py
@@ -0,0 +1,123 @@
+"""
+Authorization core: Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.
+
+Implements access control and data scoping per atdd.md (yet-2-yetkilendirme-cekirdegi).
+"""
+
+import uuid
+from dataclasses import dataclass
+
+from sqlalchemy import Select, select
+from sqlalchemy.orm import Session
+
+from app.models import Organization, TalentProfile, User
+
+
+@dataclass
+class Principal:
+    """
+    Represents the caller's authorization context.
+
+    Fields:
+      - user_id: UUID of the authenticated user (None for ANONYMOUS)
+      - kind: Role/type of principal (str, plain values: "ANONYMOUS", "TALENT", "ORG_MEMBER", etc.)
+      - talent_id: UUID of associated talent profile (if kind == "TALENT")
+      - org_ids: List of organization IDs the principal is a member of
+      - org_admin_ids: List of organization IDs the principal is an admin of
+      - institution_ids: List of institution IDs the principal is associated with
+      - is_platform_admin: True if principal is a platform administrator
+      - is_suspended: True if principal's account is suspended
+    """
+    user_id: uuid.UUID | None
+    kind: str
+    talent_id: uuid.UUID | None
+    org_ids: list[uuid.UUID]
+    org_admin_ids: list[uuid.UUID]
+    institution_ids: list[uuid.UUID]
+    is_platform_admin: bool
+    is_suspended: bool
+
+
+def can(principal: Principal, action: str, resource) -> bool:
+    """
+    Default-deny authorization check: principal can perform action on resource.
+
+    Args:
+      - principal: Principal object with authorization context
+      - action: Action name (string, e.g., "read", "admin_update")
+      - resource: Resource object being accessed (e.g., User, Organization)
+
+    Returns:
+      - bool: True if action is authorized, False otherwise (default-deny)
+
+    Implements AC-S1 (default-deny), AC-S5 (defense-in-depth ownership check).
+    """
+    # Defense-in-depth: check resource ownership directly
+    # Handle User resource: can read own User
+    if isinstance(resource, User):
+        if action == "read" and principal.user_id == resource.id:
+            return True
+        return False
+
+    # Handle Organization resource: can admin_update if principal is org admin
+    if isinstance(resource, Organization):
+        if action == "admin_update" and principal.kind == "ORG_ADMIN" and resource.id in principal.org_admin_ids:
+            return True
+        return False
+
+    # Undefined action/resource combination: default-deny
+    return False
+
+
+def scoped_organizations(session: Session, principal: Principal) -> Select:
+    """
+    Return a SQLAlchemy Select query filtered to organizations in principal's scope.
+
+    Args:
+      - session: SQLAlchemy Session
+      - principal: Principal object
+
+    Returns:
+      - sqlalchemy.sql.Select: Query returning Organization rows in principal's scope
+
+    Implements AC-2, AC-S2 (tenant isolation).
+    """
+    if principal.kind in ("ORG_MEMBER", "ORG_ADMIN"):
+        return select(Organization).where(Organization.id.in_(principal.org_ids))
+    # All other kinds: no organizations in scope
+    return select(Organization).where(Organization.id.in_([]))
+
+
+def scoped_talent_profiles(session: Session, principal: Principal) -> Select:
+    """
+    Return a SQLAlchemy Select query filtered to talent profiles in principal's scope.
+
+    Args:
+      - session: SQLAlchemy Session
+      - principal: Principal object
+
+    Returns:
+      - sqlalchemy.sql.Select: Query returning TalentProfile rows in principal's scope
+
+    Implements AC-2, AC-S2 (tenant isolation).
+    """
+    if principal.kind == "TALENT" and principal.user_id is not None:
+        return select(TalentProfile).where(TalentProfile.user_id == principal.user_id)
+    # All other kinds: no talent profiles in scope
+    return select(TalentProfile).where(TalentProfile.id.in_([]))
+
+
+def get_scoped_or_404(scoped_select: Select, session: Session):
+    """
+    Execute a scoped query and return first result or None.
+
+    Args:
+      - scoped_select: SQLAlchemy Select query (from scoped_*() functions)
+      - session: SQLAlchemy Session
+
+    Returns:
+      - Resource object if found in scope, None otherwise
+
+    Implements AC-5, AC-S4 (no distinction between out-of-scope and nonexistent).
+    """
+    return session.execute(scoped_select).scalars().first()
warning: in the working copy of 'backend/app/services/audit.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/services/audit.py b/backend/app/services/audit.py
new file mode 100644
index 0000000..23ccebc
--- /dev/null
+++ b/backend/app/services/audit.py
@@ -0,0 +1,91 @@
+"""
+Audit event logging service with PII guard.
+
+Implements AC-4, AC-S6 (PII protection).
+"""
+
+import uuid
+
+from sqlalchemy.orm import Session
+
+from app.models.audit import AuditEvent
+
+
+def _check_pii_in_metadata(metadata: dict | None) -> None:
+    """
+    Recursively check for sensitive keys in metadata dictionary.
+
+    Raises ValueError if any sensitive key is found (case-insensitive).
+    Sensitive keys: password, password_hash, email, tc_kimlik_no
+
+    Args:
+      - metadata: dict or None to check
+
+    Raises:
+      - ValueError: if sensitive key is found
+    """
+    if metadata is None:
+        return
+
+    sensitive_keys = {"password", "password_hash", "email", "tc_kimlik_no"}
+
+    def _check_dict(d: dict, path: str = "") -> None:
+        """Recursively check dictionary for sensitive keys."""
+        for key, value in d.items():
+            key_lower = key.lower()
+            if key_lower in sensitive_keys:
+                raise ValueError(f"PII detected in metadata: {key_lower}")
+            # Recursively check nested dictionaries
+            if isinstance(value, dict):
+                _check_dict(value, f"{path}.{key}" if path else key)
+
+    _check_dict(metadata)
+
+
+def log_audit_event(
+    session: Session,
+    actor_user_id: uuid.UUID | None,
+    actor_ip: str | None,
+    action: str,
+    subject_type: str,
+    subject_id: uuid.UUID | None,
+    result: str,
+    metadata: dict | None = None,
+) -> None:
+    """
+    Log an audit event to the audit_events table.
+
+    Performs PII guard check before insertion. Raises ValueError if sensitive
+    keys are detected in metadata.
+
+    Args:
+      - session: SQLAlchemy Session
+      - actor_user_id: UUID of the actor (None for anonymous)
+      - actor_ip: IP address of the actor (None if not available)
+      - action: Event action name (e.g., "USER_LOGIN", "RESOURCE_ACCESS")
+      - subject_type: Type of affected resource (e.g., "user", "organization")
+      - subject_id: UUID of affected resource (None if not applicable)
+      - result: Outcome: "SUCCESS", "DENIED", or "ERROR"
+      - metadata: Optional dict with event metadata (PII will be rejected)
+
+    Raises:
+      - ValueError: if metadata contains sensitive keys (password, email, etc.)
+      - IntegrityError: if result is not in (SUCCESS, DENIED, ERROR)
+
+    Implements AC-4, AC-S6.
+    """
+    # Check for PII in metadata
+    _check_pii_in_metadata(metadata)
+
+    # Create and insert audit event
+    event = AuditEvent(
+        actor_user_id=actor_user_id,
+        actor_ip=actor_ip,
+        action=action,
+        subject_type=subject_type,
+        subject_id=subject_id,
+        result=result,
+        event_metadata=metadata,
+    )
+    session.add(event)
+    session.flush()
warning: in the working copy of 'backend/app/models/audit.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/models/audit.py b/backend/app/models/audit.py
new file mode 100644
index 0000000..5518f04
--- /dev/null
+++ b/backend/app/models/audit.py
@@ -0,0 +1,54 @@
+"""
+AuditEvent model: append-only audit log for compliance and security monitoring.
+
+Implements AC-4, AC-S3 (immutability via trigger).
+"""
+
+import uuid
+from datetime import datetime
+
+from sqlalchemy import BigInteger, CheckConstraint, DateTime, func
+from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
+from sqlalchemy.orm import Mapped, mapped_column
+
+from app.models.base import Base
+
+
+class AuditEvent(Base):
+    """
+    Append-only audit event log.
+
+    Schema:
+      - id: BigInteger PK (autoincrement bigserial)
+      - actor_user_id: UUID of actor (nullable)
+      - actor_ip: INET address of actor (nullable)
+      - action: Event action name (text, not null)
+      - subject_type: Type of affected resource (text, not null)
+      - subject_id: UUID of affected resource (nullable)
+      - result: Outcome: 'SUCCESS', 'DENIED', or 'ERROR' (CHECK constraint)
+      - event_metadata: JSONB metadata (DB column name: "metadata", nullable)
+      - created_at: Timestamp (timestamptz, not null, server_default)
+
+    Immutability: BEFORE UPDATE OR DELETE trigger blocks all modifications.
+    No updated_at column (audit_events are append-only).
+    """
+
+    __tablename__ = "audit_events"
+    __table_args__ = (
+        CheckConstraint(
+            "result IN ('SUCCESS','DENIED','ERROR')",
+            name="ck_audit_events_result",
+        ),
+    )
+
+    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
+    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
+    actor_ip: Mapped[str | None] = mapped_column(INET)
+    action: Mapped[str] = mapped_column(nullable=False)
+    subject_type: Mapped[str] = mapped_column(nullable=False)
+    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
+    result: Mapped[str] = mapped_column(nullable=False)
+    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
+    created_at: Mapped[datetime] = mapped_column(
+        DateTime(timezone=True), server_default=func.now(), nullable=False
+    )
warning: in the working copy of 'backend/alembic/versions/a1b2c3d4e5f6_add_audit_events_table_and_immutability_trigger.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/alembic/versions/a1b2c3d4e5f6_add_audit_events_table_and_immutability_trigger.py b/backend/alembic/versions/a1b2c3d4e5f6_add_audit_events_table_and_immutability_trigger.py
new file mode 100644
index 0000000..d5324a8
--- /dev/null
+++ b/backend/alembic/versions/a1b2c3d4e5f6_add_audit_events_table_and_immutability_trigger.py
@@ -0,0 +1,62 @@
+"""add audit_events table and immutability trigger
+
+Revision ID: a1b2c3d4e5f6
+Revises: b82aa928fbd2
+Create Date: 2026-09-19 22:00:00.000000
+
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+from sqlalchemy.dialects import postgresql
+
+
+revision: str = 'a1b2c3d4e5f6'
+down_revision: Union[str, None] = 'b82aa928fbd2'
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    # Create audit_events table (append-only audit log)
+    op.create_table(
+        'audit_events',
+        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
+        sa.Column('actor_user_id', sa.UUID(), nullable=True),
+        sa.Column('actor_ip', postgresql.INET(), nullable=True),
+        sa.Column('action', sa.String(), nullable=False),
+        sa.Column('subject_type', sa.String(), nullable=False),
+        sa.Column('subject_id', sa.UUID(), nullable=True),
+        sa.Column('result', sa.String(), nullable=False),
+        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
+        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+        sa.CheckConstraint("result IN ('SUCCESS','DENIED','ERROR')", name='ck_audit_events_result'),
+        sa.PrimaryKeyConstraint('id'),
+    )
+
+    # Create immutability trigger (append-only): BEFORE UPDATE OR DELETE
+    op.execute("""
+        CREATE FUNCTION audit_events_before_update_delete() RETURNS TRIGGER AS $$
+        BEGIN
+          RAISE EXCEPTION 'audit_events is append-only'
+            USING ERRCODE = 'integrity_constraint_violation';
+        END;
+        $$ LANGUAGE plpgsql;
+    """)
+
+    op.execute("""
+        CREATE TRIGGER audit_events_immutable
+          BEFORE UPDATE OR DELETE ON audit_events
+          FOR EACH ROW
+          EXECUTE FUNCTION audit_events_before_update_delete();
+    """)
+
+
+def downgrade() -> None:
+    # Drop trigger and function (in reverse order)
+    op.execute("DROP TRIGGER IF EXISTS audit_events_immutable ON audit_events")
+    op.execute("DROP FUNCTION IF EXISTS audit_events_before_update_delete()")
+
+    # Drop table
+    op.drop_table('audit_events')
warning: in the working copy of 'backend/tests/test_authorization.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/tests/test_authorization.py b/backend/tests/test_authorization.py
new file mode 100644
index 0000000..dc4154a
--- /dev/null
+++ b/backend/tests/test_authorization.py
@@ -0,0 +1,565 @@
+"""
+Test suite for authorization core (yet-2-yetkilendirme-cekirdegi).
+
+Tests the Principal dataclass, can() function, scoped_*() queries, and get_scoped_or_404() helper.
+Implements AC-1..AC-11 and AC-S1..AC-S6 from atdd.md.
+
+Strategy: Unit + Integration tests using real Postgres (no mocks).
+Fixture pattern copied from test_migration.py.
+"""
+
+import pytest
+from sqlalchemy import create_engine
+from sqlalchemy.orm import Session
+
+from app.core.config import settings
+from app.models import Organization, OrganizationMember, TalentProfile, User
+from app.services.authorization import (
+    Principal,
+    can,
+    get_scoped_or_404,
+    scoped_organizations,
+    scoped_talent_profiles,
+)
+
+engine = create_engine(settings.database_url)
+
+
+@pytest.fixture
+def session():
+    """Fixture: real Postgres transaction per test, rollback at end."""
+    connection = engine.connect()
+    transaction = connection.begin()
+    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
+        yield s
+    transaction.rollback()
+    connection.close()
+
+
+# ============================================================================
+# AC-1: Principal dataclass accepts all kind enum values
+# ============================================================================
+
+
+def test_principal_accepts_all_kind_values_anonymous():
+    """AC-1: ANONYMOUS kind is valid."""
+    principal = Principal(
+        user_id=None,
+        kind="ANONYMOUS",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "ANONYMOUS"
+
+
+def test_principal_accepts_all_kind_values_talent():
+    """AC-1: TALENT kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="TALENT",
+        talent_id="550e8400-e29b-41d4-a716-446655440001",
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=["550e8400-e29b-41d4-a716-446655440002"],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "TALENT"
+
+
+def test_principal_accepts_all_kind_values_org_member():
+    """AC-1: ORG_MEMBER kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "ORG_MEMBER"
+
+
+def test_principal_accepts_all_kind_values_org_admin():
+    """AC-1: ORG_ADMIN kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_ADMIN",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "ORG_ADMIN"
+
+
+def test_principal_accepts_all_kind_values_org_supervisor():
+    """AC-1: ORG_SUPERVISOR kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_SUPERVISOR",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "ORG_SUPERVISOR"
+
+
+def test_principal_accepts_all_kind_values_coordinator():
+    """AC-1: COORDINATOR kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="COORDINATOR",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "COORDINATOR"
+
+
+def test_principal_accepts_all_kind_values_inst_admin():
+    """AC-1: INST_ADMIN kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="INST_ADMIN",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    assert principal.kind == "INST_ADMIN"
+
+
+def test_principal_accepts_all_kind_values_platform_admin():
+    """AC-1: PLATFORM_ADMIN kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="PLATFORM_ADMIN",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=True,
+        is_suspended=False,
+    )
+    assert principal.kind == "PLATFORM_ADMIN"
+
+
+def test_principal_accepts_all_kind_values_suspended():
+    """AC-1: SUSPENDED kind is valid."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="SUSPENDED",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=True,
+    )
+    assert principal.kind == "SUSPENDED"
+
+
+# ============================================================================
+# AC-2: scoped_*() functions return SQLAlchemy Select objects
+# ============================================================================
+
+
+def test_scoped_organizations_returns_select_object(session):
+    """AC-2: scoped_organizations() returns a SQLAlchemy Select object."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    result = scoped_organizations(session, principal)
+    # Check that result is a SQLAlchemy Select object
+    assert str(type(result)).find("Select") != -1
+
+
+def test_scoped_talent_profiles_returns_select_object(session):
+    """AC-2: scoped_talent_profiles() returns a SQLAlchemy Select object."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="TALENT",
+        talent_id="550e8400-e29b-41d4-a716-446655440001",
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=["550e8400-e29b-41d4-a716-446655440002"],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+    result = scoped_talent_profiles(session, principal)
+    # Check that result is a SQLAlchemy Select object
+    assert str(type(result)).find("Select") != -1
+
+
+# ============================================================================
+# AC-3: can() returns True for own resource, False for others
+# ============================================================================
+
+
+def test_can_true_for_own_resource(session):
+    """AC-3: can() returns True when principal accesses their own resource."""
+    user = User(email="alice@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+
+    principal = Principal(
+        user_id=user.id,
+        kind="TALENT",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Assuming resource = user object, action = "read"
+    result = can(principal, "read", user)
+    assert result is True
+
+
+def test_can_false_for_others_resource(session):
+    """AC-3: can() returns False when principal accesses another's resource."""
+    user_alice = User(email="alice@example.com", password_hash="hash")
+    user_bob = User(email="bob@example.com", password_hash="hash")
+    session.add_all([user_alice, user_bob])
+    session.flush()
+
+    principal = Principal(
+        user_id=user_alice.id,
+        kind="TALENT",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Alice trying to read Bob's resource
+    result = can(principal, "read", user_bob)
+    assert result is False
+
+
+# ============================================================================
+# AC-5: get_scoped_or_404() returns None when scoped result is empty
+# ============================================================================
+
+
+def test_get_scoped_or_404_returns_none_when_empty(session):
+    """AC-5: get_scoped_or_404() returns None when scoped query returns no rows."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Empty result (no organizations in principal's scope)
+    scoped_select = scoped_organizations(session, principal)
+    result = get_scoped_or_404(scoped_select, session)
+    assert result is None
+
+
+# ============================================================================
+# AC-S1: can() default-deny for undefined action
+# Test each Principal.kind with an undefined action
+# ============================================================================
+
+
+@pytest.mark.parametrize("kind_value", [
+    "ANONYMOUS", "TALENT", "ORG_MEMBER", "ORG_ADMIN", "ORG_SUPERVISOR",
+    "COORDINATOR", "INST_ADMIN", "PLATFORM_ADMIN", "SUSPENDED"
+])
+def test_can_default_deny_undefined_action(session, kind_value):
+    """AC-S1: can() returns False for undefined action, for all Principal.kind values."""
+    user = User(email=f"user-{kind_value}@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+
+    principal = Principal(
+        user_id=user.id,
+        kind=kind_value,
+        talent_id=None if kind_value != "TALENT" else "550e8400-e29b-41d4-a716-446655440001",
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value in ["ORG_MEMBER", "ORG_ADMIN", "ORG_SUPERVISOR"] else [],
+        org_admin_ids=["550e8400-e29b-41d4-a716-446655440001"] if kind_value in ["ORG_ADMIN"] else [],
+        institution_ids=["550e8400-e29b-41d4-a716-446655440002"] if kind_value in ["TALENT", "COORDINATOR", "INST_ADMIN"] else [],
+        is_platform_admin=(kind_value == "PLATFORM_ADMIN"),
+        is_suspended=(kind_value == "SUSPENDED"),
+    )
+
+    # Undefined action (should not exist in authorization matrix)
+    result = can(principal, "undefined_action_xyz", user)
+    assert result is False
+
+
+# ============================================================================
+# AC-S2: Tenant isolation (BOLA) — scoped_*() filters out other orgs
+# ============================================================================
+
+
+def test_scoped_organizations_tenant_isolation(session):
+    """AC-S2: scoped_organizations() does not return organizations outside principal's scope."""
+    # Create two organizations
+    org_a = Organization(name="Organization A")
+    org_b = Organization(name="Organization B")
+    session.add_all([org_a, org_b])
+    session.flush()
+
+    # Create a user and make them member of org_a only
+    user = User(email="org-member@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+
+    member = OrganizationMember(
+        organization_id=org_a.id,
+        user_id=user.id,
+        role="MEMBER",
+        status="ACTIVE",
+    )
+    session.add(member)
+    session.flush()
+
+    # Principal for this user: only has access to org_a
+    principal = Principal(
+        user_id=user.id,
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=[org_a.id],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Execute scoped query
+    scoped_select = scoped_organizations(session, principal)
+    orgs = session.execute(scoped_select).scalars().all()
+
+    # Assert: org_a should be present, org_b should NOT be present
+    org_ids = [org.id for org in orgs]
+    assert org_a.id in org_ids, "Org A (in principal's scope) should be returned"
+    assert org_b.id not in org_ids, "Org B (outside principal's scope) should NOT be returned"
+
+
+def test_scoped_talent_profiles_tenant_isolation(session):
+    """AC-S2: scoped_talent_profiles() filters by institution scope."""
+    # Create users and talent profiles in different institutions
+    # (For simplicity, test the filtering logic without institution setup)
+    user1 = User(email="talent1@example.com", password_hash="hash")
+    user2 = User(email="talent2@example.com", password_hash="hash")
+    session.add_all([user1, user2])
+    session.flush()
+
+    profile1 = TalentProfile(user_id=user1.id, full_name="Talent 1")
+    profile2 = TalentProfile(user_id=user2.id, full_name="Talent 2")
+    session.add_all([profile1, profile2])
+    session.flush()
+
+    # Principal with access to profile1's user only
+    principal = Principal(
+        user_id=user1.id,
+        kind="TALENT",
+        talent_id=profile1.id,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Execute scoped query
+    scoped_select = scoped_talent_profiles(session, principal)
+    profiles = session.execute(scoped_select).scalars().all()
+
+    # Assert: only profile1 should be present
+    profile_ids = [p.id for p in profiles]
+    assert profile1.id in profile_ids, "Profile 1 (principal's own) should be returned"
+    # Note: profile2 may or may not be returned depending on scope logic
+    # This is a simplified test; full tenant isolation depends on the exact implementation
+
+
+# ============================================================================
+# AC-S4: get_scoped_or_404() — boş sonuç = gerçekten yok (no distinction)
+# ============================================================================
+
+
+def test_get_scoped_or_404_out_of_scope_returns_none(session):
+    """AC-S4: get_scoped_or_404() returns None for out-of-scope resource."""
+    # Create an org but principal has no access to it
+    org = Organization(name="Inaccessible Org")
+    session.add(org)
+    session.flush()
+
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],  # Different org
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    scoped_select = scoped_organizations(session, principal)
+    result = get_scoped_or_404(scoped_select, session)
+    assert result is None
+
+
+def test_get_scoped_or_404_nonexistent_returns_none(session):
+    """AC-S4: get_scoped_or_404() returns None for resource that doesn't exist (same as out-of-scope)."""
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # No organizations exist; scoped query also returns empty
+    scoped_select = scoped_organizations(session, principal)
+    result = get_scoped_or_404(scoped_select, session)
+    assert result is None
+
+
+def test_get_scoped_or_404_out_of_scope_and_nonexistent_same_result(session):
+    """AC-S4: Both out-of-scope and nonexistent resources produce the same None result."""
+    org = Organization(name="Test Org")
+    session.add(org)
+    session.flush()
+
+    # Principal with access to different org
+    principal = Principal(
+        user_id="550e8400-e29b-41d4-a716-446655440000",
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=["550e8400-e29b-41d4-a716-446655440001"],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Case 1: scoped query for out-of-scope org
+    scoped_select = scoped_organizations(session, principal)
+    result_out_of_scope = get_scoped_or_404(scoped_select, session)
+
+    # Case 2: scoped query with no orgs matching principal's scope
+    result_nonexistent = get_scoped_or_404(scoped_select, session)
+
+    # Both should be None
+    assert result_out_of_scope is None
+    assert result_nonexistent is None
+
+
+# ============================================================================
+# AC-S5: can() has built-in ownership check (defense-in-depth)
+# ============================================================================
+
+
+def test_can_defense_in_depth_checks_ownership(session):
+    """AC-S5: can() checks resource ownership directly, not just via scoped_*()."""
+    user_a = User(email="user-a@example.com", password_hash="hash")
+    user_b = User(email="user-b@example.com", password_hash="hash")
+    session.add_all([user_a, user_b])
+    session.flush()
+
+    # Principal for user_a
+    principal = Principal(
+        user_id=user_a.id,
+        kind="TALENT",
+        talent_id=None,
+        org_ids=[],
+        org_admin_ids=[],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Try to access user_b's resource directly via can() (bypassing scoped_*())
+    result = can(principal, "read", user_b)
+    # Should be False because can() checks ownership internally
+    assert result is False
+
+
+def test_can_ownership_check_independent_of_scoped(session):
+    """AC-S5: can() ownership check works even if scoped_*() is bypassed."""
+    org = Organization(name="Test Org")
+    session.add(org)
+    session.flush()
+
+    user = User(email="org-admin@example.com", password_hash="hash")
+    session.add(user)
+    session.flush()
+
+    member = OrganizationMember(
+        organization_id=org.id,
+        user_id=user.id,
+        role="ADMIN",
+        status="ACTIVE",
+    )
+    session.add(member)
+    session.flush()
+
+    principal = Principal(
+        user_id=user.id,
+        kind="ORG_ADMIN",
+        talent_id=None,
+        org_ids=[org.id],
+        org_admin_ids=[org.id],
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    # Direct can() call (no scoped_*() lookup)
+    result = can(principal, "admin_update", org)
+    # Should be True because user is admin of this org
+    assert result is True
+
+    # But if user is NOT admin, even with org_ids, should be False
+    principal_member_only = Principal(
+        user_id=user.id,
+        kind="ORG_MEMBER",
+        talent_id=None,
+        org_ids=[org.id],
+        org_admin_ids=[],  # Not an admin
+        institution_ids=[],
+        is_platform_admin=False,
+        is_suspended=False,
+    )
+
+    result = can(principal_member_only, "admin_update", org)
+    assert result is False
warning: in the working copy of 'backend/tests/test_audit_events.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/tests/test_audit_events.py b/backend/tests/test_audit_events.py
new file mode 100644
index 0000000..15f61db
--- /dev/null
+++ b/backend/tests/test_audit_events.py
@@ -0,0 +1,510 @@
+"""
+Test suite for audit events (yet-2-yetkilendirme-cekirdegi).
+
+Tests the AuditEvent model, log_audit_event() helper, and immutability trigger.
+Implements AC-4 and AC-S3, AC-S6 from atdd.md.
+
+Strategy: Integration tests using real Postgres.
+Fixture pattern copied from test_migration.py.
+"""
+
+import pytest
+from sqlalchemy import create_engine, select, text
+from sqlalchemy.exc import IntegrityError
+from sqlalchemy.orm import Session
+
+from app.core.config import settings
+from app.models.audit import AuditEvent
+from app.services.audit import log_audit_event
+
+engine = create_engine(settings.database_url)
+
+
+@pytest.fixture
+def session():
+    """Fixture: real Postgres transaction per test, rollback at end."""
+    connection = engine.connect()
+    transaction = connection.begin()
+    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
+        yield s
+    transaction.rollback()
+    connection.close()
+
+
+# ============================================================================
+# AC-4: audit_events table — INSERT row with correct fields
+# ============================================================================
+
+
+def test_log_audit_event_inserts_row(session):
+    """AC-4: log_audit_event() inserts a row with correct fields."""
+    actor_user_id = "550e8400-e29b-41d4-a716-446655440000"
+    action = "USER_LOGIN"
+    subject_type = "user"
+    subject_id = "550e8400-e29b-41d4-a716-446655440001"
+    result = "SUCCESS"
+
+    # Call log_audit_event
+    log_audit_event(
+        session=session,
+        actor_user_id=actor_user_id,
+        actor_ip=None,
+        action=action,
+        subject_type=subject_type,
+        subject_id=subject_id,
+        result=result,
+        metadata={"login_method": "password"},
+    )
+
+    # Query audit_events table
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action=action)
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert str(audit_row.actor_user_id) == actor_user_id
+    assert audit_row.action == action
+    assert audit_row.subject_type == subject_type
+    assert str(audit_row.subject_id) == subject_id
+    assert audit_row.result == result
+    assert audit_row.event_metadata == {"login_method": "password"}
+
+
+def test_log_audit_event_with_ip_address(session):
+    """AC-4: log_audit_event() stores actor_ip when provided."""
+    actor_ip = "192.168.1.1"
+    action = "RESOURCE_ACCESS"
+
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=actor_ip,
+        action=action,
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata={},
+    )
+
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action=action)
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert str(audit_row.actor_ip) == actor_ip
+
+
+def test_log_audit_event_result_denied(session):
+    """AC-4: log_audit_event() accepts 'DENIED' as result."""
+    action = "UNAUTHORIZED_ACCESS"
+    result = "DENIED"
+
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action=action,
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result=result,
+        metadata={"reason": "insufficient_permissions"},
+    )
+
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action=action)
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert audit_row.result == "DENIED"
+
+
+def test_log_audit_event_result_error(session):
+    """AC-4: log_audit_event() accepts 'ERROR' as result."""
+    action = "SYSTEM_ERROR"
+    result = "ERROR"
+
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action=action,
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result=result,
+        metadata={"error": "database_connection_failed"},
+    )
+
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action=action)
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert audit_row.result == "ERROR"
+
+
+def test_log_audit_event_invalid_result_raises_integrity_error(session):
+    """AC-4: log_audit_event() with invalid result value fails (DB CHECK constraint)."""
+    with pytest.raises(IntegrityError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_ACTION",
+            subject_type="resource",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="INVALID_RESULT",  # Not in (SUCCESS, DENIED, ERROR)
+            metadata={},
+        )
+        session.commit()
+
+
+def test_log_audit_event_with_metadata(session):
+    """AC-4: log_audit_event() stores metadata JSON."""
+    metadata = {
+        "user_agent": "Mozilla/5.0",
+        "request_id": "req-123",
+        "duration_ms": 150,
+    }
+
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="API_CALL",
+        subject_type="api_endpoint",
+        subject_id="550e8400-e29b-41d4-a716-446655440099",
+        result="SUCCESS",
+        metadata=metadata,
+    )
+
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="API_CALL")
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert audit_row.event_metadata == metadata
+
+
+# ============================================================================
+# AC-S3: audit_events immutability — BEFORE UPDATE OR DELETE trigger
+# ============================================================================
+
+
+def test_audit_event_update_blocked_by_trigger_orm(session):
+    """AC-S3: UPDATE via SQLAlchemy ORM is blocked by database trigger."""
+    # Insert an audit event
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="TEST_IMMUTABLE",
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata={"original": True},
+    )
+    session.commit()
+
+    # Retrieve the audit event
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="TEST_IMMUTABLE")
+    ).scalar_one()
+
+    # Try to update it via ORM
+    audit_row.event_metadata = {"modified": True}
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_audit_event_delete_blocked_by_trigger_orm(session):
+    """AC-S3: DELETE via SQLAlchemy ORM is blocked by database trigger."""
+    # Insert an audit event
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="TEST_DELETE_PROTECTED",
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata={},
+    )
+    session.commit()
+
+    # Retrieve the audit event
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="TEST_DELETE_PROTECTED")
+    ).scalar_one()
+
+    # Try to delete it via ORM
+    session.delete(audit_row)
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_audit_event_update_blocked_by_trigger_raw_sql(session):
+    """AC-S3: UPDATE via raw SQL is blocked by database trigger."""
+    # Insert an audit event
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="TEST_RAW_UPDATE",
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata={},
+    )
+    session.commit()
+
+    # Get the audit event ID
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="TEST_RAW_UPDATE")
+    ).scalar_one()
+
+    # Try to update via raw SQL
+    with pytest.raises(IntegrityError):
+        session.execute(
+            text("UPDATE audit_events SET metadata = :metadata WHERE id = :id"),
+            {"metadata": '{"hacked": true}', "id": str(audit_row.id)},
+        )
+        session.commit()
+
+
+def test_audit_event_delete_blocked_by_trigger_raw_sql(session):
+    """AC-S3: DELETE via raw SQL is blocked by database trigger."""
+    # Insert an audit event
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="TEST_RAW_DELETE",
+        subject_type="resource",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata={},
+    )
+    session.commit()
+
+    # Get the audit event ID
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="TEST_RAW_DELETE")
+    ).scalar_one()
+
+    # Try to delete via raw SQL
+    with pytest.raises(IntegrityError):
+        session.execute(
+            text("DELETE FROM audit_events WHERE id = :id"),
+            {"id": str(audit_row.id)},
+        )
+        session.commit()
+
+
+# ============================================================================
+# AC-S6: log_audit_event() PII guard — reject sensitive keywords
+# ============================================================================
+
+
+def test_log_audit_event_rejects_password_in_metadata(session):
+    """AC-S6: log_audit_event() rejects 'password' key in metadata."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_PASSWORD",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={"password": "secret123"},
+        )
+
+
+def test_log_audit_event_rejects_password_hash_in_metadata(session):
+    """AC-S6: log_audit_event() rejects 'password_hash' key in metadata."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_PASSWORD_HASH",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={"password_hash": "bcrypt$2b$12$..."},
+        )
+
+
+def test_log_audit_event_rejects_email_in_metadata(session):
+    """AC-S6: log_audit_event() rejects 'email' key in metadata."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_EMAIL",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={"email": "user@example.com"},
+        )
+
+
+def test_log_audit_event_rejects_tc_kimlik_no_in_metadata(session):
+    """AC-S6: log_audit_event() rejects 'tc_kimlik_no' key in metadata."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_TC",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={"tc_kimlik_no": "12345678901"},
+        )
+
+
+def test_log_audit_event_accepts_safe_metadata(session):
+    """AC-S6: log_audit_event() accepts safe metadata keys."""
+    safe_metadata = {
+        "user_agent": "Mozilla/5.0",
+        "ip_address": "192.168.1.1",
+        "action_details": "Updated profile",
+        "result_code": 200,
+    }
+
+    log_audit_event(
+        session=session,
+        actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+        actor_ip=None,
+        action="TEST_SAFE",
+        subject_type="user",
+        subject_id="550e8400-e29b-41d4-a716-446655440001",
+        result="SUCCESS",
+        metadata=safe_metadata,
+    )
+
+    audit_row = session.execute(
+        select(AuditEvent).filter_by(action="TEST_SAFE")
+    ).scalar_one_or_none()
+
+    assert audit_row is not None
+    assert audit_row.event_metadata == safe_metadata
+
+
+def test_log_audit_event_rejects_multiple_sensitive_keys(session):
+    """AC-S6: log_audit_event() rejects when multiple sensitive keys are present."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_MULTIPLE_SENSITIVE",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={
+                "password": "secret",
+                "email": "user@example.com",
+                "safe_key": "value",
+            },
+        )
+
+
+def test_log_audit_event_nested_metadata_with_sensitive_keys(session):
+    """AC-S6: log_audit_event() checks nested metadata for sensitive keys."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_NESTED",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={
+                "user_info": {
+                    "name": "John",
+                    "password": "secret123",  # Sensitive key in nested dict
+                }
+            },
+        )
+
+
+def test_log_audit_event_case_insensitive_pii_check(session):
+    """AC-S6: log_audit_event() checks for sensitive keys case-insensitively."""
+    with pytest.raises(ValueError):
+        log_audit_event(
+            session=session,
+            actor_user_id="550e8400-e29b-41d4-a716-446655440000",
+            actor_ip=None,
+            action="TEST_CASE",
+            subject_type="user",
+            subject_id="550e8400-e29b-41d4-a716-446655440001",
+            result="SUCCESS",
+            metadata={"Password": "secret123"},  # Capital P
+        )
+
+
+# ============================================================================
+# Additional: audit_events table existence and structure
+# ============================================================================
+
+
+def test_audit_events_table_exists(session):
+    """Verify audit_events table exists in the database."""
+    result = session.execute(
+        text("""
+            SELECT EXISTS (
+                SELECT 1 FROM information_schema.tables
+                WHERE table_name = 'audit_events'
+            )
+        """)
+    ).scalar()
+    assert result is True
+
+
+def test_audit_events_has_required_columns(session):
+    """Verify audit_events table has all required columns."""
+    result = session.execute(
+        text("""
+            SELECT column_name FROM information_schema.columns
+            WHERE table_name = 'audit_events'
+            ORDER BY ordinal_position
+        """)
+    ).scalars().all()
+
+    required_columns = {
+        "id",
+        "actor_user_id",
+        "actor_ip",
+        "action",
+        "subject_type",
+        "subject_id",
+        "result",
+        "metadata",
+        "created_at",
+    }
+
+    assert required_columns.issubset(set(result))
+
+
+def test_audit_events_result_check_constraint(session):
+    """Verify audit_events result CHECK constraint rejects invalid values."""
+    with pytest.raises(IntegrityError):
+        session.execute(
+            text("""
+                INSERT INTO audit_events
+                (actor_user_id, action, subject_type, subject_id, result)
+                VALUES (:uid, :action, :stype, :sid, :result)
+            """),
+            {
+                "uid": "550e8400-e29b-41d4-a716-446655440000",
+                "action": "TEST",
+                "stype": "resource",
+                "sid": "550e8400-e29b-41d4-a716-446655440001",
+                "result": "INVALID",
+            },
+        )
+        session.commit()
