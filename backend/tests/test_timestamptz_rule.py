"""
YET-216 (VER-03): CLAUDE.md requires timestamptz/UTC for every datetime column.
The rule must hold in the ORM declarations and in the real schema.
"""

from sqlalchemy import DateTime, text

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.models.base import Base


def test_orm_declares_no_naive_datetime():
    naive = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    ]
    assert naive == []


def test_database_has_no_timestamp_without_time_zone(session):
    rows = session.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND data_type = 'timestamp without time zone' "
            "ORDER BY 1, 2"
        )
    ).all()
    assert rows == []
