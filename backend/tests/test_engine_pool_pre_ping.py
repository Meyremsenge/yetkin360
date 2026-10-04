"""
YET-234 (L-12): the request-scoped engine must validate pooled connections on
checkout, so a DB restart does not turn the first requests into 500s.
"""

from sqlalchemy import text

from app.core import deps


def test_request_engine_has_pool_pre_ping_enabled():
    assert deps._engine.pool._pre_ping is True


def test_request_engine_still_serves_queries():
    with deps._engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
