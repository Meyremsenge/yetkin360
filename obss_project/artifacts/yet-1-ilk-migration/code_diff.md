diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 3e0f4d6..c08e3cb 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -12,6 +12,20 @@ jobs:
     defaults:
       run:
         working-directory: backend
+    services:
+      postgres:
+        image: postgres:16
+        env:
+          POSTGRES_USER: test
+          POSTGRES_PASSWORD: test
+          POSTGRES_DB: test
+        ports:
+          - 5432:5432
+        options: >-
+          --health-cmd "pg_isready -U test"
+          --health-interval 5s
+          --health-timeout 5s
+          --health-retries 10
     env:
       DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/test
     steps:
@@ -22,6 +36,7 @@ jobs:
       - run: pip install -r requirements.txt
       - run: ruff check .
       - run: mypy app
+      - run: alembic upgrade head
       - run: pytest -q
 
   frontend:
diff --git a/backend/alembic/env.py b/backend/alembic/env.py
index e1ed493..d974001 100644
--- a/backend/alembic/env.py
+++ b/backend/alembic/env.py
@@ -4,6 +4,7 @@ from alembic import context
 from sqlalchemy import engine_from_config, pool
 
 from app.core.config import settings
+from app.models import Base
 
 config = context.config
 config.set_main_option("sqlalchemy.url", settings.database_url)
@@ -11,7 +12,7 @@ config.set_main_option("sqlalchemy.url", settings.database_url)
 if config.config_file_name is not None:
     fileConfig(config.config_file_name)
 
-target_metadata = None
+target_metadata = Base.metadata
 
 
 def run_migrations_offline() -> None:
diff --git a/backend/requirements.txt b/backend/requirements.txt
index f90df49..ef78f51 100644
--- a/backend/requirements.txt
+++ b/backend/requirements.txt
@@ -5,6 +5,7 @@ alembic==1.14.0
 psycopg[binary]==3.2.3
 pydantic==2.10.4
 pydantic-settings==2.7.0
+uuid6==2024.7.10
 
 ruff==0.8.4
 mypy==1.14.0
--- NEW FILES ---
warning: in the working copy of 'backend/app/models/__init__.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/models/__init__.py b/backend/app/models/__init__.py
new file mode 100644
index 0000000..7b1dcf8
--- /dev/null
+++ b/backend/app/models/__init__.py
@@ -0,0 +1,21 @@
+from app.models.base import Base
+from app.models.identity import (
+    Institution,
+    InstitutionMember,
+    Organization,
+    OrganizationMember,
+    TalentProfile,
+    User,
+)
+from app.models.skill import Skill
+
+__all__ = [
+    "Base",
+    "User",
+    "Institution",
+    "InstitutionMember",
+    "TalentProfile",
+    "Organization",
+    "OrganizationMember",
+    "Skill",
+]
warning: in the working copy of 'backend/app/models/base.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/models/base.py b/backend/app/models/base.py
new file mode 100644
index 0000000..35cb52c
--- /dev/null
+++ b/backend/app/models/base.py
@@ -0,0 +1,23 @@
+import uuid
+from datetime import datetime
+
+from sqlalchemy import DateTime, func
+from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
+from uuid6 import uuid7
+
+
+class Base(DeclarativeBase):
+    pass
+
+
+def uuid7_default() -> uuid.UUID:
+    return uuid7()
+
+
+class TimestampMixin:
+    created_at: Mapped[datetime] = mapped_column(
+        DateTime(timezone=True), server_default=func.now(), nullable=False
+    )
+    updated_at: Mapped[datetime] = mapped_column(
+        DateTime(timezone=True), server_default=func.now(), nullable=False
+    )
warning: in the working copy of 'backend/app/models/identity.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/models/identity.py b/backend/app/models/identity.py
new file mode 100644
index 0000000..2713e35
--- /dev/null
+++ b/backend/app/models/identity.py
@@ -0,0 +1,130 @@
+import uuid
+from datetime import datetime
+
+from sqlalchemy import (
+    CheckConstraint,
+    DateTime,
+    ForeignKey,
+    Integer,
+    SmallInteger,
+    String,
+    UniqueConstraint,
+)
+from sqlalchemy.dialects.postgresql import CITEXT, UUID
+from sqlalchemy.orm import Mapped, mapped_column
+
+from app.models.base import Base, TimestampMixin, uuid7_default
+
+
+class User(Base, TimestampMixin):
+    __tablename__ = "users"
+    __table_args__ = (
+        CheckConstraint(
+            "status IN ('PENDING','ACTIVE','SUSPENDED','DELETED')",
+            name="ck_users_status",
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
+    password_hash: Mapped[str] = mapped_column(String, nullable=False)
+    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
+    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
+    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+
+
+class Institution(Base, TimestampMixin):
+    __tablename__ = "institutions"
+    __table_args__ = (
+        CheckConstraint(
+            "verification_level IN ('T1','T2','T3','T4')",
+            name="ck_institutions_verification_level",
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    name: Mapped[str] = mapped_column(String, nullable=False)
+    domain: Mapped[str | None] = mapped_column(CITEXT, unique=True)
+    verification_level: Mapped[str] = mapped_column(String, nullable=False, server_default="T1")
+    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
+
+
+class InstitutionMember(Base, TimestampMixin):
+    __tablename__ = "institution_members"
+    __table_args__ = (
+        UniqueConstraint("institution_id", "user_id", name="uq_institution_members_institution_user"),
+        CheckConstraint("role IN ('ADMIN','COORDINATOR')", name="ck_institution_members_role"),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    institution_id: Mapped[uuid.UUID] = mapped_column(
+        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
+    )
+    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
+    role: Mapped[str] = mapped_column(String, nullable=False)
+
+
+class TalentProfile(Base, TimestampMixin):
+    __tablename__ = "talent_profiles"
+    __table_args__ = (
+        CheckConstraint("study_year BETWEEN 1 AND 8", name="ck_talent_profiles_study_year"),
+        CheckConstraint(
+            "visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')",
+            name="ck_talent_profiles_visibility",
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    user_id: Mapped[uuid.UUID] = mapped_column(
+        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
+    )
+    institution_id: Mapped[uuid.UUID | None] = mapped_column(
+        UUID(as_uuid=True), ForeignKey("institutions.id")
+    )
+    full_name: Mapped[str] = mapped_column(String, nullable=False)
+    headline: Mapped[str | None] = mapped_column(String)
+    department: Mapped[str | None] = mapped_column(String)
+    study_year: Mapped[int | None] = mapped_column(SmallInteger)
+    city: Mapped[str | None] = mapped_column(String)
+    visibility: Mapped[str] = mapped_column(String, nullable=False, server_default="INSTITUTION")
+    public_slug: Mapped[str | None] = mapped_column(CITEXT, unique=True)
+    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+
+
+class Organization(Base, TimestampMixin):
+    __tablename__ = "organizations"
+    __table_args__ = (
+        UniqueConstraint("legal_id", name="uq_organizations_legal_id"),
+        CheckConstraint(
+            "verification_level IN ('T1','T2','T3','T4')",
+            name="ck_organizations_verification_level",
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    name: Mapped[str] = mapped_column(String, nullable=False)
+    legal_id: Mapped[str | None] = mapped_column(String)
+    domain: Mapped[str | None] = mapped_column(CITEXT)
+    verification_level: Mapped[str] = mapped_column(String, nullable=False, server_default="T1")
+    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
+    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
+    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
+
+
+class OrganizationMember(Base, TimestampMixin):
+    __tablename__ = "organization_members"
+    __table_args__ = (
+        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_organization_user"),
+        CheckConstraint("role IN ('ADMIN','MEMBER')", name="ck_organization_members_role"),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    organization_id: Mapped[uuid.UUID] = mapped_column(
+        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
+    )
+    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
+    role: Mapped[str] = mapped_column(String, nullable=False)
+    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
warning: in the working copy of 'backend/app/models/skill.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/app/models/skill.py b/backend/app/models/skill.py
new file mode 100644
index 0000000..b23afd6
--- /dev/null
+++ b/backend/app/models/skill.py
@@ -0,0 +1,34 @@
+import uuid
+
+from sqlalchemy import CheckConstraint, ForeignKey, String
+from sqlalchemy.dialects.postgresql import CITEXT, UUID
+from sqlalchemy.orm import Mapped, mapped_column
+
+from app.models.base import Base, TimestampMixin, uuid7_default
+
+
+class Skill(Base, TimestampMixin):
+    __tablename__ = "skills"
+    __table_args__ = (
+        CheckConstraint(
+            "category IN ('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT')",
+            name="ck_skills_category",
+        ),
+        CheckConstraint(
+            "status IN ('ACTIVE','MERGED','DEPRECATED')",
+            name="ck_skills_status",
+        ),
+        CheckConstraint(
+            "status <> 'MERGED' OR merged_into_id IS NOT NULL",
+            name="ck_skills_merged_requires_target",
+        ),
+    )
+
+    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7_default)
+    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
+    name_tr: Mapped[str] = mapped_column(String, nullable=False)
+    name_en: Mapped[str | None] = mapped_column(String)
+    category: Mapped[str] = mapped_column(String, nullable=False)
+    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id"))
+    status: Mapped[str] = mapped_column(String, nullable=False, server_default="ACTIVE")
+    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id"))
warning: in the working copy of 'backend/tests/test_migration.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/tests/test_migration.py b/backend/tests/test_migration.py
new file mode 100644
index 0000000..cc956be
--- /dev/null
+++ b/backend/tests/test_migration.py
@@ -0,0 +1,111 @@
+import pytest
+from sqlalchemy import create_engine, inspect
+from sqlalchemy.exc import IntegrityError
+from sqlalchemy.orm import Session
+
+from app.core.config import settings
+from app.models import Institution, InstitutionMember, Organization, Skill, TalentProfile, User
+
+engine = create_engine(settings.database_url)
+
+
+@pytest.fixture
+def session():
+    connection = engine.connect()
+    transaction = connection.begin()
+    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
+        yield s
+    transaction.rollback()
+    connection.close()
+
+
+EXPECTED_TABLES = {
+    "users",
+    "institutions",
+    "institution_members",
+    "talent_profiles",
+    "organizations",
+    "organization_members",
+    "skills",
+}
+
+
+def test_all_seven_tables_exist():
+    inspector = inspect(engine)
+    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
+
+
+def test_users_status_check_rejects_invalid_value(session):
+    with pytest.raises(IntegrityError):
+        session.execute(
+            User.__table__.insert().values(
+                email="a@example.com", password_hash="x", status="INVALID"
+            )
+        )
+        session.commit()
+
+
+def test_users_email_unique_constraint(session):
+    session.add(User(email="dup@example.com", password_hash="x"))
+    session.commit()
+    session.add(User(email="dup@example.com", password_hash="y"))
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_institution_members_role_check_rejects_invalid_value(session):
+    inst = Institution(name="Test Uni")
+    user = User(email="member@example.com", password_hash="x")
+    session.add_all([inst, user])
+    session.flush()
+    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="OWNER"))
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_institution_members_unique_pair(session):
+    inst = Institution(name="Test Uni 2")
+    user = User(email="member2@example.com", password_hash="x")
+    session.add_all([inst, user])
+    session.flush()
+    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="ADMIN"))
+    session.commit()
+    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="COORDINATOR"))
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_talent_profiles_study_year_check(session):
+    user = User(email="talent@example.com", password_hash="x")
+    session.add(user)
+    session.flush()
+    session.add(TalentProfile(user_id=user.id, full_name="Ali Veli", study_year=9))
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_skill_merged_requires_target(session):
+    session.add(Skill(slug="python", name_tr="Python", category="LANGUAGE", status="MERGED"))
+    with pytest.raises(IntegrityError):
+        session.commit()
+
+
+def test_skill_merged_with_target_succeeds(session):
+    target = Skill(slug="js", name_tr="JavaScript", category="LANGUAGE")
+    session.add(target)
+    session.flush()
+    merged = Skill(
+        slug="ecmascript", name_tr="ECMAScript", category="LANGUAGE",
+        status="MERGED", merged_into_id=target.id,
+    )
+    session.add(merged)
+    session.commit()
+    assert merged.id is not None
+
+
+def test_organization_legal_id_unique_when_present(session):
+    session.add(Organization(name="Acme A", legal_id="1234567890"))
+    session.commit()
+    session.add(Organization(name="Acme B", legal_id="1234567890"))
+    with pytest.raises(IntegrityError):
+        session.commit()
warning: in the working copy of 'backend/alembic/versions/d3696712a323_initial_schema_users_institutions_.py', LF will be replaced by CRLF the next time Git touches it
diff --git a/backend/alembic/versions/d3696712a323_initial_schema_users_institutions_.py b/backend/alembic/versions/d3696712a323_initial_schema_users_institutions_.py
new file mode 100644
index 0000000..93c8a2e
--- /dev/null
+++ b/backend/alembic/versions/d3696712a323_initial_schema_users_institutions_.py
@@ -0,0 +1,148 @@
+"""initial schema: users, institutions, talent_profiles, organizations, memberships, skills
+
+Revision ID: d3696712a323
+Revises: 
+Create Date: 2026-09-19 21:45:26.956915
+
+"""
+from typing import Sequence, Union
+
+from alembic import op
+import sqlalchemy as sa
+from sqlalchemy.dialects import postgresql
+
+revision: str = 'd3696712a323'
+down_revision: Union[str, None] = None
+branch_labels: Union[str, Sequence[str], None] = None
+depends_on: Union[str, Sequence[str], None] = None
+
+
+def upgrade() -> None:
+    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
+    # ### commands auto generated by Alembic - please adjust! ###
+    op.create_table('institutions',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('name', sa.String(), nullable=False),
+    sa.Column('domain', postgresql.CITEXT(), nullable=True),
+    sa.Column('verification_level', sa.String(), server_default='T1', nullable=False),
+    sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("verification_level IN ('T1','T2','T3','T4')", name='ck_institutions_verification_level'),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('domain')
+    )
+    op.create_table('skills',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('slug', postgresql.CITEXT(), nullable=False),
+    sa.Column('name_tr', sa.String(), nullable=False),
+    sa.Column('name_en', sa.String(), nullable=True),
+    sa.Column('category', sa.String(), nullable=False),
+    sa.Column('parent_id', sa.UUID(), nullable=True),
+    sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
+    sa.Column('merged_into_id', sa.UUID(), nullable=True),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("category IN ('LANGUAGE','FRAMEWORK','TOOL','DOMAIN','SOFT')", name='ck_skills_category'),
+    sa.CheckConstraint("status <> 'MERGED' OR merged_into_id IS NOT NULL", name='ck_skills_merged_requires_target'),
+    sa.CheckConstraint("status IN ('ACTIVE','MERGED','DEPRECATED')", name='ck_skills_status'),
+    sa.ForeignKeyConstraint(['merged_into_id'], ['skills.id'], ),
+    sa.ForeignKeyConstraint(['parent_id'], ['skills.id'], ),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('slug')
+    )
+    op.create_table('users',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('email', postgresql.CITEXT(), nullable=False),
+    sa.Column('password_hash', sa.String(), nullable=False),
+    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
+    sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=False),
+    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("status IN ('PENDING','ACTIVE','SUSPENDED','DELETED')", name='ck_users_status'),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('email')
+    )
+    op.create_table('institution_members',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('institution_id', sa.UUID(), nullable=False),
+    sa.Column('user_id', sa.UUID(), nullable=False),
+    sa.Column('role', sa.String(), nullable=False),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("role IN ('ADMIN','COORDINATOR')", name='ck_institution_members_role'),
+    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ),
+    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('institution_id', 'user_id', name='uq_institution_members_institution_user')
+    )
+    op.create_table('organizations',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('name', sa.String(), nullable=False),
+    sa.Column('legal_id', sa.String(), nullable=True),
+    sa.Column('domain', postgresql.CITEXT(), nullable=True),
+    sa.Column('verification_level', sa.String(), server_default='T1', nullable=False),
+    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('verified_by_user_id', sa.UUID(), nullable=True),
+    sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
+    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("verification_level IN ('T1','T2','T3','T4')", name='ck_organizations_verification_level'),
+    sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('legal_id', name='uq_organizations_legal_id')
+    )
+    op.create_table('talent_profiles',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('user_id', sa.UUID(), nullable=False),
+    sa.Column('institution_id', sa.UUID(), nullable=True),
+    sa.Column('full_name', sa.String(), nullable=False),
+    sa.Column('headline', sa.String(), nullable=True),
+    sa.Column('department', sa.String(), nullable=True),
+    sa.Column('study_year', sa.SmallInteger(), nullable=True),
+    sa.Column('city', sa.String(), nullable=True),
+    sa.Column('visibility', sa.String(), server_default='INSTITUTION', nullable=False),
+    sa.Column('public_slug', postgresql.CITEXT(), nullable=True),
+    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("visibility IN ('PRIVATE','INSTITUTION','ORGANIZATIONS','PUBLIC')", name='ck_talent_profiles_visibility'),
+    sa.CheckConstraint('study_year BETWEEN 1 AND 8', name='ck_talent_profiles_study_year'),
+    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ),
+    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('public_slug'),
+    sa.UniqueConstraint('user_id')
+    )
+    op.create_table('organization_members',
+    sa.Column('id', sa.UUID(), nullable=False),
+    sa.Column('organization_id', sa.UUID(), nullable=False),
+    sa.Column('user_id', sa.UUID(), nullable=False),
+    sa.Column('role', sa.String(), nullable=False),
+    sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False),
+    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
+    sa.CheckConstraint("role IN ('ADMIN','MEMBER')", name='ck_organization_members_role'),
+    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
+    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
+    sa.PrimaryKeyConstraint('id'),
+    sa.UniqueConstraint('organization_id', 'user_id', name='uq_organization_members_organization_user')
+    )
+    # ### end Alembic commands ###
+
+
+def downgrade() -> None:
+    # ### commands auto generated by Alembic - please adjust! ###
+    op.drop_table('organization_members')
+    op.drop_table('talent_profiles')
+    op.drop_table('organizations')
+    op.drop_table('institution_members')
+    op.drop_table('users')
+    op.drop_table('skills')
+    op.drop_table('institutions')
+    # ### end Alembic commands ###
+    op.execute("DROP EXTENSION IF EXISTS citext")
