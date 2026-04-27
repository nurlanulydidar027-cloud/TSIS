# TSIS 4 — Snake (Database Edition)

Pygame + PostgreSQL. Persistent leaderboard, poison food, three power-ups, runtime obstacles, JSON settings, and four polished game screens.

## Features by spec section

| Spec | What's done |
|---|---|
| 3.1 Leaderboard | `players` + `game_sessions` tables created on startup; auto-save after game over; Top-10 screen; **personal best** displayed during gameplay |
| 3.2 Poison food | Dark-red ✕ marker. Eats → snake shrinks by 2; if length ≤ 1 → game over |
| 3.3 Power-ups | **Speed** (+5 fps for 5 s), **Slow** (-4 fps for 5 s), **Shield** (consumes the next wall / self / obstacle hit). Only one on the field; despawns after 8 s |
| 3.4 Obstacles | From level 3 onward; never trap the snake; food / power-ups never overlap obstacles |
| 3.5 Settings | `settings.json` — snake colour, grid overlay, sound — auto-loaded at startup |
| 3.6 Screens | Main Menu, Game Over, Leaderboard, Settings |

## Files

```
TSIS4/
├── main.py        entry, screens, render
├── game.py        gameplay state machine
├── db.py          psycopg2 access (offline-tolerant)
├── config.py      constants & DB credentials
├── schema.sql     reference schema
└── settings.json  auto-created on first run
```

## Run

```bash
# 1. install deps
pip install pygame psycopg2-binary

# 2. create DB
createdb snakegame
# (db.py auto-creates the tables on startup)

# 3. credentials (or edit config.py)
export PGUSER=postgres PGPASSWORD=postgres PGDATABASE=snakegame

# 4. run
python main.py
```

If the DB is not reachable, the game **still runs** in offline mode — just without leaderboard persistence.

## Controls

- **Arrow keys** or **W/A/S/D** — move
- **Esc** — back to main menu
