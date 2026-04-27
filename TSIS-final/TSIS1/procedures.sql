-- =====================================================================
-- TSIS 1 — PhoneBook PL/pgSQL Procedures & Functions
-- =====================================================================
-- This file contains BOTH the legacy Practice 7-8 procedures and
-- the new TSIS-1 ones, so the application has everything it needs
-- after a single load:
--
--    psql -d phonebook -f procedures.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- Practice 8 carry-overs (kept here so the DB is self-contained)
-- ---------------------------------------------------------------------

-- Pattern search across name and any phone number.
CREATE OR REPLACE FUNCTION search_pattern(p_query TEXT)
RETURNS TABLE(id INT, name VARCHAR, email VARCHAR, phones TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT  c.id,
            c.name,
            c.email,
            string_agg(p.phone || ' (' || p.type || ')', ', ')
    FROM    contacts c
    LEFT    JOIN phones p ON p.contact_id = c.id
    WHERE   c.name  ILIKE '%' || p_query || '%'
       OR   p.phone ILIKE '%' || p_query || '%'
    GROUP BY c.id;
END;
$$ LANGUAGE plpgsql;

-- Upsert by name -- used by both CSV and JSON importers.
CREATE OR REPLACE PROCEDURE upsert_contact(
    p_name      VARCHAR,
    p_email     VARCHAR,
    p_birthday  DATE,
    p_group     VARCHAR
) AS $$
DECLARE
    v_group_id INT;
BEGIN
    -- ensure group exists, create if missing
    IF p_group IS NOT NULL THEN
        INSERT INTO groups(name) VALUES (p_group)
            ON CONFLICT (name) DO NOTHING;
        SELECT id INTO v_group_id FROM groups WHERE name = p_group;
    END IF;

    INSERT INTO contacts (name, email, birthday, group_id)
    VALUES (p_name, p_email, p_birthday, v_group_id)
    ON CONFLICT (name) DO UPDATE
    SET email     = EXCLUDED.email,
        birthday  = EXCLUDED.birthday,
        group_id  = EXCLUDED.group_id;
END;
$$ LANGUAGE plpgsql;

-- Paginated listing.
CREATE OR REPLACE FUNCTION list_contacts(p_limit INT, p_offset INT)
RETURNS TABLE(id INT, name VARCHAR, email VARCHAR,
              birthday DATE, group_name VARCHAR, phones TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT  c.id, c.name, c.email, c.birthday,
            g.name AS group_name,
            COALESCE(string_agg(p.phone || ' (' || p.type || ')', ', '), '')
    FROM    contacts c
    LEFT    JOIN groups g ON g.id = c.group_id
    LEFT    JOIN phones p ON p.contact_id = c.id
    GROUP BY c.id, g.name
    ORDER BY c.id
    LIMIT  p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Delete by name OR phone.
CREATE OR REPLACE PROCEDURE delete_contact(p_value VARCHAR) AS $$
BEGIN
    DELETE FROM contacts
    WHERE  name = p_value
       OR  id IN (SELECT contact_id FROM phones WHERE phone = p_value);
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- TSIS 1 — NEW objects (3.4)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 3.4.1   add_phone(contact_name, phone, type)
-- Adds a new phone for an existing contact.
-- Raises a friendly exception if the contact does not exist.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE add_phone(
    p_contact_name VARCHAR,
    p_phone        VARCHAR,
    p_type         VARCHAR
) AS $$
DECLARE
    v_contact_id INT;
BEGIN
    SELECT id INTO v_contact_id
    FROM   contacts
    WHERE  name = p_contact_name;

    IF v_contact_id IS NULL THEN
        RAISE EXCEPTION 'Contact "%" does not exist', p_contact_name;
    END IF;

    IF p_type NOT IN ('home', 'work', 'mobile') THEN
        RAISE EXCEPTION 'Phone type must be home/work/mobile (got "%")', p_type;
    END IF;

    INSERT INTO phones(contact_id, phone, type)
    VALUES (v_contact_id, p_phone, p_type);
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 3.4.2   move_to_group(contact_name, group_name)
-- Moves a contact to another group; creates the group if missing.
-- ---------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE move_to_group(
    p_contact_name VARCHAR,
    p_group_name   VARCHAR
) AS $$
DECLARE
    v_group_id INT;
BEGIN
    -- create the group on demand
    INSERT INTO groups(name) VALUES (p_group_name)
        ON CONFLICT (name) DO NOTHING;

    SELECT id INTO v_group_id FROM groups WHERE name = p_group_name;

    UPDATE contacts
       SET group_id = v_group_id
     WHERE name = p_contact_name;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contact "%" does not exist', p_contact_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 3.4.3   search_contacts(query)
-- Extends pattern-search to also cover email and ALL phones in the
-- new phones table.  Returns one row per matching contact with
-- aggregated phone list.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_contacts(p_query TEXT)
RETURNS TABLE(
    id        INT,
    name      VARCHAR,
    email     VARCHAR,
    birthday  DATE,
    group_name VARCHAR,
    phones    TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT  c.id,
            c.name,
            c.email,
            c.birthday,
            g.name AS group_name,
            COALESCE(string_agg(DISTINCT p.phone || ' (' || p.type || ')', ', '), '')
    FROM    contacts c
    LEFT    JOIN groups g ON g.id = c.group_id
    LEFT    JOIN phones p ON p.contact_id = c.id
    WHERE   c.name  ILIKE '%' || p_query || '%'
       OR   c.email ILIKE '%' || p_query || '%'
       OR   c.id IN (
             SELECT contact_id FROM phones
              WHERE phone ILIKE '%' || p_query || '%'
           )
    GROUP BY c.id, g.name
    ORDER BY c.name;
END;
$$ LANGUAGE plpgsql;
