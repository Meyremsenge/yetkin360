"""
YET-184: registering the same stored object twice at the same time.

The service pre-checks for an existing record, but two requests can both pass that
check before either commits. uq_evidence_storage_key is the real guard; the service
turns the loser's IntegrityError into the same 409 EVIDENCE_ALREADY_REGISTERED the
pre-check gives.

Genuinely committed, two independent sessions (the rolled-back `session` fixture
cannot show a lock wait). The loser is made to block on the winner's uncommitted
unique-index entry, then the winner commits — the interleaving the race produces.
"""

import threading
import time
import uuid

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.errors import ApiError
from app.models import Evidence, Outbox, TalentProfile, User
from app.services.authorization import Principal
from app.services.evidence import create_evidence
from tests._evidence_api import add_evidence


def _principal(user_id, talent_id) -> Principal:
    return Principal(
        user_id=user_id,
        kind="TALENT",
        talent_id=talent_id,
        org_ids=[],
        org_admin_ids=[],
        institution_ids=[],
        is_platform_admin=False,
        is_suspended=False,
    )


def _wait_until_a_session_waits_on_a_lock(engine, thread: threading.Thread, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    with engine.connect() as probe:
        while time.monotonic() < deadline and thread.is_alive():
            waiting = probe.execute(
                text(
                    "select count(*) from pg_stat_activity "
                    "where datname = current_database() and wait_event_type = 'Lock'"
                )
            ).scalar_one()
            if waiting:
                return True
            time.sleep(0.05)
    return False


def test_concurrent_registration_of_the_same_object_yields_one_record_and_one_409():
    engine = create_engine(settings.database_url)
    Maker = sessionmaker(bind=engine)

    setup = Maker()
    user = User(email=f"evidence-race-{uuid.uuid4()}@example.com", password_hash="x")
    setup.add(user)
    setup.flush()
    talent = TalentProfile(user_id=user.id, full_name="Race Talent", visibility="PRIVATE")
    setup.add(talent)
    setup.commit()
    user_id, talent_id = user.id, talent.id
    setup.close()

    key = f"evidence/{talent_id}/{uuid.uuid4()}.pdf"
    principal = _principal(user_id, talent_id)
    winner, loser = Maker(), Maker()
    outcome: dict = {}

    def register(session):
        return create_evidence(session, principal, key, "DOCUMENT", "application/pdf", 1024)

    def run_loser():
        try:
            register(loser)
            loser.commit()
            outcome["result"] = "registered"
        except ApiError as exc:
            outcome["result"] = (exc.status_code, exc.detail["code"])
            loser.rollback()
        except Exception as exc:  # anything else (e.g. a raw IntegrityError) is a failure
            outcome["result"] = f"unexpected {type(exc).__name__}"
            loser.rollback()

    try:
        register(winner)  # flushed, not committed: holds the unique-index entry
        thread = threading.Thread(target=run_loser)
        thread.start()
        _wait_until_a_session_waits_on_a_lock(engine, thread)
        winner.commit()
        thread.join(timeout=10)
        assert not thread.is_alive()

        assert outcome["result"] == (409, "EVIDENCE_ALREADY_REGISTERED")

        check = Maker()
        try:
            assert check.scalar(select(func.count()).select_from(Evidence).where(Evidence.storage_key == key)) == 1
            assert (
                check.scalar(
                    select(func.count())
                    .select_from(Outbox)
                    .where(Outbox.topic == "evidence.scan_requested", Outbox.payload["storage_key"].as_string() == key)
                )
                == 1
            )  # the loser's outbox row rolled back with it
        finally:
            check.close()
    finally:
        winner.close()
        loser.close()
        cleanup = Maker()
        cleanup.execute(
            Outbox.__table__.delete().where(
                Outbox.topic == "evidence.scan_requested", Outbox.payload["storage_key"].as_string() == key
            )
        )
        cleanup.execute(Evidence.__table__.delete().where(Evidence.owner_talent_id == talent_id))
        cleanup.execute(TalentProfile.__table__.delete().where(TalentProfile.id == talent_id))
        cleanup.execute(User.__table__.delete().where(User.id == user_id))
        cleanup.commit()
        cleanup.close()
        engine.dispose()


def test_database_itself_rejects_a_second_record_for_the_same_object(session, talent_a):
    """The constraint holds without the service pre-check (any other writer, a future code path)."""
    first = add_evidence(session, talent_a)

    with pytest.raises(IntegrityError, match="uq_evidence_storage_key"):
        with session.begin_nested():
            add_evidence(session, talent_a, storage_key=first.storage_key)
