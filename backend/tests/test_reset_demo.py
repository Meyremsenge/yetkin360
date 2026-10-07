"""Demo reset script: empties data tables (incl. append-only ones), keeps taxonomy, refuses prod."""

import uuid

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models import AuditEvent, Base, Skill, User
from scripts import reset_demo
from scripts.reset_demo import KEEP_TABLES, reset_demo_data, resettable_tables


def test_reset_empties_data_tables_including_append_only(session):
    session.add(User(email=f"demo-{uuid.uuid4()}@seed.local", password_hash="h"))
    session.add(AuditEvent(action="demo.test", subject_type="user", result="SUCCESS"))
    session.flush()

    reset_demo_data(session)

    assert session.execute(select(func.count()).select_from(User)).scalar_one() == 0
    assert session.execute(select(func.count()).select_from(AuditEvent)).scalar_one() == 0


def test_reset_keeps_skill_taxonomy(session):
    slug = f"reset-demo-{uuid.uuid4().hex[:8]}"
    session.add(Skill(slug=slug, name_tr="Demo", category="TOOL"))
    session.flush()

    reset_demo_data(session)

    assert session.execute(select(Skill.id).where(Skill.slug == slug)).scalar_one_or_none() is not None


def test_resettable_tables_cover_all_but_kept():
    names = set(resettable_tables())
    assert names.isdisjoint(KEEP_TABLES)
    assert names | {"skills"} == {t.name for t in Base.metadata.sorted_tables}
    assert {"attestations", "verified_experiences", "audit_events", "skill_signals"} <= names


def test_reset_refuses_in_production(session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError):
        reset_demo_data(session)


def test_main_requires_yes(monkeypatch):
    called = []
    monkeypatch.setattr(reset_demo, "_SessionLocal", lambda: called.append(1))
    assert reset_demo.main([]) == 2
    assert called == []
