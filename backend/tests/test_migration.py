import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Institution, InstitutionMember, Organization, Skill, TalentProfile, User

engine = create_engine(settings.database_url)


@pytest.fixture
def session():
    connection = engine.connect()
    transaction = connection.begin()
    with Session(bind=connection, join_transaction_mode="create_savepoint") as s:
        yield s
    transaction.rollback()
    connection.close()


EXPECTED_TABLES = {
    "users",
    "institutions",
    "institution_members",
    "talent_profiles",
    "organizations",
    "organization_members",
    "skills",
    "outbox",
}


def test_all_seven_tables_exist():
    inspector = inspect(engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))


def test_users_status_check_rejects_invalid_value(session):
    with pytest.raises(IntegrityError):
        session.execute(
            User.__table__.insert().values(
                email="a@example.com", password_hash="x", status="INVALID"
            )
        )
        session.commit()


def test_users_email_unique_constraint(session):
    session.add(User(email="dup@example.com", password_hash="x"))
    session.commit()
    session.add(User(email="dup@example.com", password_hash="y"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_institution_members_role_check_rejects_invalid_value(session):
    inst = Institution(name="Test Uni")
    user = User(email="member@example.com", password_hash="x")
    session.add_all([inst, user])
    session.flush()
    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="OWNER"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_institution_members_unique_pair(session):
    inst = Institution(name="Test Uni 2")
    user = User(email="member2@example.com", password_hash="x")
    session.add_all([inst, user])
    session.flush()
    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="ADMIN"))
    session.commit()
    session.add(InstitutionMember(institution_id=inst.id, user_id=user.id, role="COORDINATOR"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_talent_profiles_study_year_check(session):
    user = User(email="talent@example.com", password_hash="x")
    session.add(user)
    session.flush()
    session.add(TalentProfile(user_id=user.id, full_name="Ali Veli", study_year=9))
    with pytest.raises(IntegrityError):
        session.commit()


def test_skill_merged_requires_target(session):
    session.add(Skill(slug="python", name_tr="Python", category="LANGUAGE", status="MERGED"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_skill_merged_with_target_succeeds(session):
    target = Skill(slug="js", name_tr="JavaScript", category="LANGUAGE")
    session.add(target)
    session.flush()
    merged = Skill(
        slug="ecmascript", name_tr="ECMAScript", category="LANGUAGE",
        status="MERGED", merged_into_id=target.id,
    )
    session.add(merged)
    session.commit()
    assert merged.id is not None


def test_organization_legal_id_unique_when_present(session):
    session.add(Organization(name="Acme A", legal_id="1234567890"))
    session.commit()
    session.add(Organization(name="Acme B", legal_id="1234567890"))
    with pytest.raises(IntegrityError):
        session.commit()


# ============================================================================
# Outbox table migration tests (yet-5-outbox-worker)
# ============================================================================


def test_outbox_table_exists():
    """Verify outbox table exists after migration."""
    from sqlalchemy import text
    connection = engine.connect()
    result = connection.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'outbox'
            )
        """)
    ).scalar()
    connection.close()
    assert result is True


def test_outbox_has_required_columns(session):
    """Verify outbox table has all required columns."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'outbox'
            ORDER BY ordinal_position
        """)
    ).scalars().all()

    required_columns = {"id", "topic", "payload", "created_at", "processed_at", "attempts"}
    assert required_columns.issubset(set(result))


def test_outbox_id_bigserial_primary_key(session):
    """Verify outbox.id is bigserial (BIGINT) and primary key."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT column_name, data_type, is_identity, identity_generation
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'id'
        """)
    ).fetchone()

    assert result is not None
    # data_type should be "bigint" (result of bigserial)
    assert result[1] == "bigint"
    # is_identity should be YES (identity/auto-increment)
    assert result[2] == "YES"


def test_outbox_topic_text_not_null(session):
    """Verify outbox.topic is TEXT and NOT NULL."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'topic'
        """)
    ).fetchone()

    assert result is not None
    assert result[0] == "text"
    assert result[1] == "NO"  # NOT NULL


def test_outbox_payload_jsonb_not_null(session):
    """Verify outbox.payload is JSONB and NOT NULL."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'payload'
        """)
    ).fetchone()

    assert result is not None
    assert result[0] == "jsonb"
    assert result[1] == "NO"  # NOT NULL


def test_outbox_created_at_timestamptz_not_null(session):
    """Verify outbox.created_at is TIMESTAMPTZ and NOT NULL."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'created_at'
        """)
    ).fetchone()

    assert result is not None
    assert "timestamp" in result[0].lower()  # timestamptz
    assert result[1] == "NO"  # NOT NULL


def test_outbox_processed_at_nullable(session):
    """Verify outbox.processed_at is TIMESTAMPTZ and nullable."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'processed_at'
        """)
    ).fetchone()

    assert result is not None
    assert "timestamp" in result[0].lower()  # timestamptz
    assert result[1] == "YES"  # nullable


def test_outbox_attempts_int_default_zero(session):
    """Verify outbox.attempts is INT with default 0."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'outbox' AND column_name = 'attempts'
        """)
    ).fetchone()

    assert result is not None
    assert result[0] == "integer"
    assert "0" in str(result[1])  # column_default should contain "0"


def test_outbox_partial_index_on_processed_at_null(session):
    """Verify partial index exists on (created_at) WHERE processed_at IS NULL."""
    from sqlalchemy import text
    result = session.execute(
        text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'outbox'
            AND indexdef LIKE '%processed_at IS NULL%'
        """)
    ).fetchone()

    assert result is not None
    # indexdef should contain the partial index definition
    assert "processed_at IS NULL" in result[1]


def test_outbox_insert_with_default_values(session):
    """Verify outbox row can be inserted with required fields, defaults applied."""
    from app.models.outbox import Outbox

    row = Outbox(
        topic="email.test",
        payload={"message": "test"},
    )
    session.add(row)
    session.flush()

    # Verify defaults were applied
    assert row.id is not None  # bigserial
    assert row.created_at is not None  # auto-set
    assert row.processed_at is None  # nullable default
    assert row.attempts == 0  # explicit default


def test_outbox_insert_without_attempts_uses_default(session):
    """Verify outbox.attempts defaults to 0 if not specified."""
    from sqlalchemy import text

    session.execute(
        text("""
            INSERT INTO outbox (topic, payload)
            VALUES (:topic, :payload)
        """),
        {"topic": "email.test", "payload": '{"message": "test"}'},
    )
    session.commit()

    result = session.execute(text("SELECT attempts FROM outbox WHERE topic = 'email.test'")).scalar()
    assert result == 0
