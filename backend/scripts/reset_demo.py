"""
Demo data reset: empties every application table in one statement.

Development/demo tool only — refuses to run when ENVIRONMENT=production.
Kept tables: `skills` (reference taxonomy, not demo data) and `alembic_version`.

Why TRUNCATE (raw SQL outside migrations, approved exception): the append-only
tables (attestations, skill_signals, evaluations, evaluation_items,
verified_experiences, audit_events) have row-level BEFORE DELETE triggers, so a
selective DELETE of "demo rows" is impossible by design. TRUNCATE does not fire
row-level triggers and only ever wipes whole tables — it cannot be used to
quietly remove a single verified record. CLI only; no HTTP endpoint exists.

Uploaded evidence files in object storage are NOT removed (no network calls here).

Usage:
    python -m scripts.reset_demo --yes            # empty all demo data
    python -m scripts.reset_demo --yes --reseed   # empty, then run scripts.seed
"""

import argparse
import runpy
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import _SessionLocal
from app.models import Base

KEEP_TABLES = frozenset({"skills", "alembic_version"})


def resettable_tables() -> list[str]:
    """All ORM tables except the kept ones, in a stable order."""
    return sorted(t.name for t in Base.metadata.sorted_tables if t.name not in KEEP_TABLES)


def reset_demo_data(session: Session) -> list[str]:
    """TRUNCATE every resettable table. Caller commits. Returns truncated table names."""
    if settings.environment == "production":
        raise RuntimeError("Demo reset cannot run in production environment")

    tables = resettable_tables()
    quote = session.get_bind().dialect.identifier_preparer.quote
    # RESTART IDENTITY resets bigserial counters (audit_events.id).
    session.execute(text(f"TRUNCATE {', '.join(quote(t) for t in tables)} RESTART IDENTITY"))
    return tables


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Empty all demo data (development only).")
    parser.add_argument("--yes", action="store_true", help="confirm: permanently delete all data")
    parser.add_argument("--reseed", action="store_true", help="run scripts.seed afterwards")
    args = parser.parse_args(argv)

    if not args.yes:
        print("Refusing to run without --yes (this permanently deletes all data).", file=sys.stderr)
        return 2

    session = _SessionLocal()
    try:
        tables = reset_demo_data(session)
        session.commit()
        print(f"Demo reset: {len(tables)} tables emptied (kept: {', '.join(sorted(KEEP_TABLES))})")
    except Exception as e:
        session.rollback()
        print(f"Demo reset failed, nothing deleted: {e}", file=sys.stderr)
        return 1
    finally:
        session.close()

    if args.reseed:
        runpy.run_module("scripts.seed", run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
