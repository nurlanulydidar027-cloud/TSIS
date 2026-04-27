-- =====================================================================
-- TSIS 1 — PhoneBook Extended Schema
-- =====================================================================
-- Drops are wrapped in IF EXISTS so the script is idempotent.
-- Run order:  psql -d phonebook -f schema.sql
-- =====================================================================

DROP TABLE IF EXISTS phones    CASCADE;
DROP TABLE IF EXISTS contacts  CASCADE;
DROP TABLE IF EXISTS groups    CASCADE;

-- ---------------------------------------------------------------------
-- groups: contact category lookup table
-- ---------------------------------------------------------------------
CREATE TABLE groups (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(50) UNIQUE NOT NULL
);

-- Pre-populate the four categories required by spec.
INSERT INTO groups (name) VALUES
    ('Family'), ('Work'), ('Friend'), ('Other')
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------------
-- contacts: master record (extended from Practice 7-8 with email,
-- birthday, group_id and a created_at audit column for sorting).
-- The legacy `phone` column is intentionally removed -- all phones now
-- live in the phones table to support 1-to-many.
-- ---------------------------------------------------------------------
CREATE TABLE contacts (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(100),
    birthday    DATE,
    group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- phones: 1-to-many.  Type constrained to the three values from spec.
-- ON DELETE CASCADE so removing a contact also removes their phones.
-- ---------------------------------------------------------------------
CREATE TABLE phones (
    id          SERIAL PRIMARY KEY,
    contact_id  INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    phone       VARCHAR(20) NOT NULL,
    type        VARCHAR(10) CHECK (type IN ('home', 'work', 'mobile'))
);

-- Useful indexes for the search / sort use-cases.
CREATE INDEX idx_contacts_name      ON contacts (lower(name));
CREATE INDEX idx_contacts_email     ON contacts (lower(email));
CREATE INDEX idx_contacts_birthday  ON contacts (birthday);
CREATE INDEX idx_phones_contact     ON phones   (contact_id);
CREATE INDEX idx_phones_phone       ON phones   (phone);
