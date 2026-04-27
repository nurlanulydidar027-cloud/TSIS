"""
TSIS 1 — PhoneBook | Database configuration.

Edit these values to match your local PostgreSQL setup, OR override them
through environment variables (preferred for production / CI).
"""
import os

DB_CONFIG = {
    "host":     os.getenv("PGHOST",     "localhost"),
    "port":     os.getenv("PGPORT",     "5432"),
    "dbname":   os.getenv("PGDATABASE", "phonebook"),
    "user":     os.getenv("PGUSER",     "postgres"),
    "password": os.getenv("PGPASSWORD", "postgres"),
}
