"""
TSIS 1 — PhoneBook | psycopg2 connection helper.

Provides a context-managed connection so callers don't have to
remember to commit / close manually.
"""
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_CONFIG


@contextmanager
def get_conn():
    """Yield a psycopg2 connection, commit on success, rollback on error."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor(dict_rows: bool = False):
    """Yield (conn, cursor).  dict_rows=True returns RealDictCursor rows."""
    with get_conn() as conn:
        factory = RealDictCursor if dict_rows else None
        cur = conn.cursor(cursor_factory=factory)
        try:
            yield conn, cur
        finally:
            cur.close()
