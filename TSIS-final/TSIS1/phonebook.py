"""
TSIS 1 — PhoneBook (Extended)
=================================================================
Console application that talks to PostgreSQL via psycopg2.

Implements every requirement from TSIS-1:
    3.2  Filter by group, search by email, sortable lists, paginator
    3.3  Import / export JSON, extended CSV import
    3.4  Calls to add_phone / move_to_group / search_contacts

Run:
    python phonebook.py
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime
from typing import Any

from connect import get_cursor

PAGE_SIZE = 5  # rows per page in the paginator


# ---------------------------------------------------------------------------
# small console helpers
# ---------------------------------------------------------------------------
def banner(text: str) -> None:
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def ask(prompt: str, *, allow_empty: bool = False) -> str:
    while True:
        v = input(prompt).strip()
        if v or allow_empty:
            return v
        print("  ! value required")


def ask_date(prompt: str) -> date | None:
    v = input(prompt).strip()
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        print("  ! invalid date, expected YYYY-MM-DD — set to NULL")
        return None


def print_rows(rows: list[dict]) -> None:
    if not rows:
        print("  (no rows)")
        return
    for r in rows:
        bday = r["birthday"].isoformat() if r.get("birthday") else "—"
        print(
            f"  #{r['id']:<3} {r['name']:<22} "
            f"{(r.get('email') or '—'):<25} "
            f"{bday:<12} "
            f"[{r.get('group_name') or '—'}] "
            f"{r.get('phones') or ''}"
        )


# ---------------------------------------------------------------------------
# 3.4  wrappers around the new stored procedures / functions
# ---------------------------------------------------------------------------
def call_add_phone() -> None:
    name  = ask("  contact name : ")
    phone = ask("  phone        : ")
    ptype = ask("  type (home/work/mobile): ").lower()
    try:
        with get_cursor() as (conn, cur):
            cur.execute("CALL add_phone(%s, %s, %s);", (name, phone, ptype))
        print("  ✓ phone added")
    except Exception as e:
        print(f"  ! {e}")


def call_move_to_group() -> None:
    name  = ask("  contact name : ")
    grp   = ask("  target group : ")
    try:
        with get_cursor() as (conn, cur):
            cur.execute("CALL move_to_group(%s, %s);", (name, grp))
        print(f"  ✓ moved “{name}” to group “{grp}”")
    except Exception as e:
        print(f"  ! {e}")


def call_search_contacts() -> None:
    q = ask("  query (name / email / phone fragment): ")
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute("SELECT * FROM search_contacts(%s);", (q,))
        print_rows(cur.fetchall())


# ---------------------------------------------------------------------------
# 3.2  console search / filter / sort / paginate
# ---------------------------------------------------------------------------
def filter_by_group() -> None:
    grp = ask("  group name (Family/Work/Friend/Other/...): ")
    sql = """
        SELECT  c.id, c.name, c.email, c.birthday,
                g.name AS group_name,
                COALESCE(string_agg(DISTINCT p.phone||' ('||p.type||')',', '),'') AS phones
        FROM    contacts c
        LEFT    JOIN groups g ON g.id = c.group_id
        LEFT    JOIN phones p ON p.contact_id = c.id
        WHERE   g.name ILIKE %s
        GROUP   BY c.id, g.name
        ORDER   BY c.name;
    """
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute(sql, (grp,))
        print_rows(cur.fetchall())


def search_by_email() -> None:
    needle = ask("  email fragment: ")
    sql = """
        SELECT  c.id, c.name, c.email, c.birthday,
                g.name AS group_name,
                COALESCE(string_agg(DISTINCT p.phone||' ('||p.type||')',', '),'') AS phones
        FROM    contacts c
        LEFT    JOIN groups g ON g.id = c.group_id
        LEFT    JOIN phones p ON p.contact_id = c.id
        WHERE   c.email ILIKE %s
        GROUP   BY c.id, g.name
        ORDER   BY c.email;
    """
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute(sql, (f"%{needle}%",))
        print_rows(cur.fetchall())


def sort_contacts() -> None:
    print("  sort by:  1) name   2) birthday   3) date added")
    choice = ask("  choice: ")
    column = {"1": "c.name", "2": "c.birthday NULLS LAST", "3": "c.created_at"}.get(choice)
    if not column:
        print("  ! invalid choice")
        return
    sql = f"""
        SELECT  c.id, c.name, c.email, c.birthday,
                g.name AS group_name,
                COALESCE(string_agg(DISTINCT p.phone||' ('||p.type||')',', '),'') AS phones
        FROM    contacts c
        LEFT    JOIN groups g ON g.id = c.group_id
        LEFT    JOIN phones p ON p.contact_id = c.id
        GROUP   BY c.id, g.name
        ORDER   BY {column};
    """
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute(sql)
        print_rows(cur.fetchall())


def paginate_contacts() -> None:
    """Loop next/prev/quit using the existing list_contacts() DB function."""
    page = 0
    while True:
        with get_cursor(dict_rows=True) as (conn, cur):
            cur.execute("SELECT * FROM list_contacts(%s, %s);",
                        (PAGE_SIZE, page * PAGE_SIZE))
            rows = cur.fetchall()

        banner(f"page {page + 1}")
        print_rows(rows)
        cmd = input("  [n]ext  [p]rev  [q]uit > ").strip().lower()
        if cmd == "n":
            if len(rows) < PAGE_SIZE:
                print("  (already on last page)")
            else:
                page += 1
        elif cmd == "p":
            page = max(0, page - 1)
        else:
            return


# ---------------------------------------------------------------------------
# 3.3  import / export
# ---------------------------------------------------------------------------
def _all_contacts_with_phones() -> list[dict]:
    sql = """
        SELECT  c.id, c.name, c.email,
                c.birthday,
                g.name AS group_name,
                COALESCE(json_agg(json_build_object('phone', p.phone, 'type', p.type))
                         FILTER (WHERE p.id IS NOT NULL), '[]') AS phones
        FROM    contacts c
        LEFT    JOIN groups g ON g.id = c.group_id
        LEFT    JOIN phones p ON p.contact_id = c.id
        GROUP   BY c.id, g.name
        ORDER   BY c.id;
    """
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute(sql)
        return cur.fetchall()


def export_json() -> None:
    path = ask("  output file (default contacts.json): ", allow_empty=True) or "contacts.json"
    rows = _all_contacts_with_phones()
    # JSON cannot serialise date objects directly
    for r in rows:
        if r["birthday"]:
            r["birthday"] = r["birthday"].isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"  ✓ wrote {len(rows)} contacts to {path}")


def import_json() -> None:
    path = ask("  input file: ")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ! cannot read file: {e}")
        return

    answer_all: str | None = None  # remember "[a]ll" choice across rows

    with get_cursor() as (conn, cur):
        for entry in data:
            cur.execute("SELECT 1 FROM contacts WHERE name=%s;", (entry["name"],))
            exists = cur.fetchone() is not None

            if exists:
                if answer_all in ("s", "o"):
                    decision = answer_all
                else:
                    print(f"  ! contact '{entry['name']}' already exists.")
                    decision = ask("    [s]kip  [o]verwrite  [A]ll-skip  [O]ll-overwrite : ").lower()
                    if decision == "a":
                        decision = answer_all = "s"
                    elif decision == "o" and ask("    apply to all? y/N: ").lower() == "y":
                        answer_all = "o"
                if decision == "s":
                    continue

            bday = entry.get("birthday")
            bday = datetime.strptime(bday, "%Y-%m-%d").date() if bday else None
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s);",
                (entry["name"], entry.get("email"), bday, entry.get("group_name")),
            )
            cur.execute("SELECT id FROM contacts WHERE name=%s;", (entry["name"],))
            cid = cur.fetchone()[0]
            cur.execute("DELETE FROM phones WHERE contact_id=%s;", (cid,))
            for ph in entry.get("phones", []):
                cur.execute(
                    "INSERT INTO phones(contact_id, phone, type) VALUES (%s,%s,%s);",
                    (cid, ph["phone"], ph["type"]),
                )
    print("  ✓ JSON import finished")


def import_csv() -> None:
    """Extended CSV: name,email,birthday,group,phone,type   (one phone per row)."""
    path = ask("  CSV file (default contacts.csv): ", allow_empty=True) or "contacts.csv"
    try:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    except FileNotFoundError:
        print("  ! file not found")
        return

    with get_cursor() as (conn, cur):
        for r in rows:
            bday = r.get("birthday") or None
            bday = datetime.strptime(bday, "%Y-%m-%d").date() if bday else None
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s);",
                (r["name"], r.get("email") or None, bday, r.get("group") or None),
            )
            if r.get("phone"):
                cur.execute("SELECT id FROM contacts WHERE name=%s;", (r["name"],))
                cid = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO phones(contact_id, phone, type) "
                    "SELECT %s,%s,%s "
                    "WHERE NOT EXISTS (SELECT 1 FROM phones "
                    "                  WHERE contact_id=%s AND phone=%s);",
                    (cid, r["phone"], r.get("type") or "mobile", cid, r["phone"]),
                )
    print(f"  ✓ imported {len(rows)} CSV rows")


# ---------------------------------------------------------------------------
# basic CRUD (kept here for convenience; not the focus of TSIS-1)
# ---------------------------------------------------------------------------
def insert_contact() -> None:
    name  = ask("  name     : ")
    email = ask("  email    : ", allow_empty=True) or None
    bday  = ask_date("  birthday (YYYY-MM-DD, blank to skip): ")
    grp   = ask("  group    : ", allow_empty=True) or None
    with get_cursor() as (conn, cur):
        cur.execute("CALL upsert_contact(%s,%s,%s,%s);", (name, email, bday, grp))
    print("  ✓ saved")


def delete_contact() -> None:
    val = ask("  name or phone to delete: ")
    with get_cursor() as (conn, cur):
        cur.execute("CALL delete_contact(%s);", (val,))
    print("  ✓ deleted (if existed)")


# ---------------------------------------------------------------------------
# main menu
# ---------------------------------------------------------------------------
MENU = """
PhoneBook — Extended (TSIS-1)
  1)  Insert / upsert contact
  2)  Add phone to existing contact          (proc add_phone)
  3)  Move contact to group                  (proc move_to_group)
  4)  Search across name/email/phones        (fn  search_contacts)
  5)  Filter by group
  6)  Search by email fragment
  7)  Sort contacts (name / birthday / added)
  8)  Browse contacts (paginated)
  9)  Delete contact (by name or phone)
 10)  Export to JSON
 11)  Import from JSON  (skip / overwrite)
 12)  Import from CSV   (extended schema)
  0)  Quit
"""


def main() -> None:
    actions = {
        "1": insert_contact,
        "2": call_add_phone,
        "3": call_move_to_group,
        "4": call_search_contacts,
        "5": filter_by_group,
        "6": search_by_email,
        "7": sort_contacts,
        "8": paginate_contacts,
        "9": delete_contact,
        "10": export_json,
        "11": import_json,
        "12": import_csv,
    }
    while True:
        print(MENU)
        choice = input("> ").strip()
        if choice == "0":
            print("bye")
            sys.exit(0)
        action = actions.get(choice)
        if action:
            try:
                action()
            except Exception as e:  # show DB errors but stay in menu
                print(f"  ! error: {e}")
        else:
            print("  ! unknown option")


if __name__ == "__main__":
    main()
