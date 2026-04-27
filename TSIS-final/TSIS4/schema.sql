-- TSIS 4 — Snake | reference schema (db.py creates the same tables on startup)
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
