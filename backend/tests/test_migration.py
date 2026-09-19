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
