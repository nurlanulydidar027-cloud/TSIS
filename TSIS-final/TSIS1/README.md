# TSIS 1 — PhoneBook (Extended)

Console phone-book backed by PostgreSQL via psycopg2.

## What's inside (vs. Practice 7-8)

| Layer | New in TSIS-1 |
|---|---|
| Schema | `groups` table, `phones` table (1-to-many), `email`, `birthday`, `created_at`, indexes |
| Procedures | `add_phone`, `move_to_group`, `search_contacts` |
| Console | filter by group, email search, sort by name/birthday/added, page navigator |
| I/O | export to JSON, import from JSON with skip/overwrite, extended CSV import (email, birthday, group, phone type) |

## Run

```bash
# 1. create DB
createdb phonebook

# 2. load schema + procedures
psql -d phonebook -f schema.sql
psql -d phonebook -f procedures.sql

# 3. set credentials (or edit config.py)
export PGUSER=postgres PGPASSWORD=postgres PGDATABASE=phonebook

# 4. install client
pip install psycopg2-binary

# 5. run
python phonebook.py
```

## Quick demo flow

1. `12` — import CSV (`contacts.csv`)
2. `8`  — paginated browse, `n`/`p`/`q`
3. `4`  — `search_contacts` with `gmail` finds all Gmail addresses
4. `2`  — `add_phone Alice Johnson +77000000000 work`
5. `3`  — `move_to_group Alice Johnson VIP` (auto-creates group)
6. `10` — export everything to `contacts.json`
7. `11` — import `contacts.json` back, choose skip/overwrite on duplicates
