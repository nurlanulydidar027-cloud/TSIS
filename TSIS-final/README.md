# TSIS — Final Defense Projects (Programming Principles 2)

Repo: `Beisenbek/programming-principles-2` · folder `TSIS/`

This bundle contains four final tasks completed for the end-of-course defense.

| # | Project | Stack | Highlights |
|---|---|---|---|
| TSIS 1 | PhoneBook (PostgreSQL) | Python · psycopg2 · PostgreSQL | Multi-phone contacts, groups, full-text search, JSON / CSV import-export with conflict resolution |
| TSIS 2 | Paint | Python · pygame | 11 tools (pencil, line, rect, square, circle, right & equilateral triangle, rhombus, eraser, fill, text), 12-color palette, 3 brush sizes, live preview, save as PNG |
| TSIS 3 | Racer | Python · pygame | Lane-based traffic, obstacles, coins, power-ups (nitro/shield/repair), 3 difficulties, settings & top-10 leaderboard |
| TSIS 4 | Snake | Python · pygame · PostgreSQL | Levels, obstacles, big/poison/power-up food, online leaderboard with offline fallback |

## Setup

```bash
# Pygame projects (TSIS 2, 3)
pip install pygame

# DB projects (TSIS 1, 4)
pip install pygame psycopg2-binary

# DB credentials via environment (defaults shown)
export PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD=postgres
```

## Running

```bash
# TSIS 1
createdb phonebook
psql -d phonebook -f TSIS1/schema.sql
psql -d phonebook -f TSIS1/procedures.sql
PGDATABASE=phonebook python TSIS1/phonebook.py

# TSIS 2
python TSIS2/paint.py

# TSIS 3
python TSIS3/main.py

# TSIS 4
createdb snakegame    # optional — game runs offline if DB is unreachable
PGDATABASE=snakegame python TSIS4/main.py
```

Each subfolder has its own `README.md` with controls and details.

## Suggested commit messages for GitHub

```
feat(TSIS1): PhoneBook with groups, multi-phone, JSON/CSV I/O
feat(TSIS2): Paint app with 11 tools, palette, brush sizes
feat(TSIS3): Racer game with traffic, power-ups, leaderboard
feat(TSIS4): Snake game with levels, obstacles, online leaderboard
```
