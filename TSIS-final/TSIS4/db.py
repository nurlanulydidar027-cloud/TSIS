"""
TSIS 4 — Snake | PostgreSQL access via psycopg2.

Tables:
    players (id, username UNIQUE)
    game_sessions (id, player_id, score, level_reached, played_at)

The module degrades gracefully: if psycopg2 isn't installed or the DB
isn't reachable, every public function returns sane "empty" values
instead of crashing the game (so the game still runs in offline mode).
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime   import datetime
from typing     import Any

from config import DB_CONFIG

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _HAS_PG = True
except ImportError:
    _HAS_PG = False

_OFFLINE = False


# ---------------------------------------------------------------------------
# connection helpers
# ---------------------------------------------------------------------------
@contextmanager
def _conn():
    global _OFFLINE
    if not _HAS_PG or _OFFLINE:
        raise RuntimeError("offline")
    try:
        c = psycopg2.connect(**DB_CONFIG)
    except Exception:
        _OFFLINE = True
        raise RuntimeError("offline")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


# ---------------------------------------------------------------------------
# schema bootstrap (run once at game start)
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id        SERIAL PRIMARY KEY,
    username  VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id            SERIAL PRIMARY KEY,
    player_id     INTEGER REFERENCES players(id) ON DELETE CASCADE,
    score         INTEGER   NOT NULL,
    level_reached INTEGER   NOT NULL,
    played_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_score ON game_sessions(score DESC);
"""


def init_schema() -> bool:
    """Returns True if DB available, False otherwise (game still runs)."""
    try:
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute(SCHEMA_SQL)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# user / session
# ---------------------------------------------------------------------------
def ensure_player(username: str) -> int | None:
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO players(username) VALUES (%s) "
                "ON CONFLICT (username) DO UPDATE SET username = EXCLUDED.username "
                "RETURNING id;", (username,)
            )
            return cur.fetchone()[0]
    except Exception:
        return None


def save_session(username: str, score: int, level: int) -> bool:
    pid = ensure_player(username)
    if pid is None:
        return False
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO game_sessions (player_id, score, level_reached) "
                "VALUES (%s, %s, %s);",
                (pid, score, level),
            )
        return True
    except Exception:
        return False


def personal_best(username: str) -> int:
    try:
        with _conn() as c, c.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(MAX(score), 0) FROM game_sessions s "
                "JOIN players p ON p.id = s.player_id "
                "WHERE p.username = %s;",
                (username,),
            )
            return cur.fetchone()[0] or 0
    except Exception:
        return 0


def top10() -> list[dict[str, Any]]:
    try:
        with _conn() as c:
            cur = c.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT  p.username, s.score, s.level_reached, s.played_at
                FROM    game_sessions s
                JOIN    players p ON p.id = s.player_id
                ORDER   BY s.score DESC, s.played_at DESC
                LIMIT   10;
            """)
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]
    except Exception:
        return []


def is_online() -> bool:
    return _HAS_PG and not _OFFLINE
