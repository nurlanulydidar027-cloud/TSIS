"""
TSIS 1 — PhoneBook (Extended)
=================================================================
Консольное приложение, работает с PostgreSQL через psycopg2.

Реализует все требования TSIS-1:
    3.2  Фильтр по группе, поиск по email, сортировка, пагинация
    3.3  Импорт / экспорт JSON, расширенный импорт CSV
    3.4  Вызовы процедур: add_phone / move_to_group / search_contacts

Запуск:
    python phonebook.py
"""
from __future__ import annotations

# === ИМПОРТЫ =============================================================
# csv      — модуль для чтения CSV-файлов
# json     — модуль для работы с JSON
# sys      — для выхода из программы (sys.exit)
# date     — тип "дата" (без времени)
# datetime — для парсинга строк в дату
import csv
import json
import sys
from datetime import date, datetime
from typing import Any

# Импортируем контекст-менеджер для соединения с БД из connect.py
from connect import get_cursor

# Сколько строк показывать на одной странице при пагинации
PAGE_SIZE = 5


# =========================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КОНСОЛИ
# Просто рисуют красивый вывод — не основная логика
# =========================================================================
def banner(text: str) -> None:
    """Печатает рамку с текстом — для красоты."""
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def ask(prompt: str, *, allow_empty: bool = False) -> str:
    """
    Запрашивает ввод у пользователя.
    Если allow_empty=False — переспрашивает пока не введут что-то.
    """
    while True:
        v = input(prompt).strip()       # strip убирает пробелы по краям
        if v or allow_empty:
            return v
        print("  ! value required")


def ask_date(prompt: str) -> date | None:
    """
    Запрашивает дату в формате YYYY-MM-DD.
    Если пусто — возвращает None (день рождения не указан).
    Если формат неверный — предупреждает и тоже возвращает None.
    """
    v = input(prompt).strip()
    if not v:
        return None
    try:
        # strptime парсит строку в дату по заданному формату
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        print("  ! invalid date, expected YYYY-MM-DD — set to NULL")
        return None


def print_rows(rows: list[dict]) -> None:
    """Печатает список контактов красиво в виде таблицы."""
    if not rows:
        print("  (no rows)")
        return
    for r in rows:
        # Если день рождения есть — преобразуем в строку, иначе ставим прочерк
        bday = r["birthday"].isoformat() if r.get("birthday") else "—"
        # f-string с выравниванием по ширине: :<22 = 22 символа, влево
        print(
            f"  #{r['id']:<3} {r['name']:<22} "
            f"{(r.get('email') or '—'):<25} "
            f"{bday:<12} "
            f"[{r.get('group_name') or '—'}] "
            f"{r.get('phones') or ''}"
        )


# =========================================================================
# 3.4 — ВЫЗОВЫ ХРАНИМЫХ ПРОЦЕДУР ИЗ procedures.sql
# Это новые процедуры из TSIS-1 (не из практик)
# =========================================================================
def call_add_phone() -> None:
    """
    Добавляет телефон к существующему контакту.
    Вызывает процедуру add_phone(name, phone, type) из БД.
    """
    name  = ask("  contact name : ")
    phone = ask("  phone        : ")
    ptype = ask("  type (home/work/mobile): ").lower()
    try:
        # CALL — это вызов процедуры в PostgreSQL
        # %s — плейсхолдер, реальные значения подставит psycopg2 безопасно
        with get_cursor() as (conn, cur):
            cur.execute("CALL add_phone(%s, %s, %s);", (name, phone, ptype))
        print("  ✓ phone added")
    except Exception as e:
        # Если процедура выбросила ошибку (например, контакта нет) — показываем
        print(f"  ! {e}")


def call_move_to_group() -> None:
    """
    Перемещает контакт в другую группу.
    Если группы ещё нет — процедура её создаст автоматически.
    """
    name  = ask("  contact name : ")
    grp   = ask("  target group : ")
    try:
        with get_cursor() as (conn, cur):
            cur.execute("CALL move_to_group(%s, %s);", (name, grp))
        print(f"  ✓ moved “{name}” to group “{grp}”")
    except Exception as e:
        print(f"  ! {e}")


def call_search_contacts() -> None:
    """
    Универсальный поиск: ищет по имени, email и всем телефонам.
    Использует функцию search_contacts() с JOIN трёх таблиц.
    """
    q = ask("  query (name / email / phone fragment): ")
    # dict_rows=True — чтобы каждая строка возвращалась как словарь
    with get_cursor(dict_rows=True) as (conn, cur):
        cur.execute("SELECT * FROM search_contacts(%s);", (q,))
        # fetchall — забрать все найденные строки
        print_rows(cur.fetchall())


# =========================================================================
# 3.2 — ПОИСК / ФИЛЬТР / СОРТИРОВКА / ПАГИНАЦИЯ
# Все запросы делают JOIN трёх таблиц чтобы показать полную инфо о контакте
# =========================================================================
def filter_by_group() -> None:
    """Показывает все контакты из определённой группы."""
    grp = ask("  group name (Family/Work/Friend/Other/...): ")

    # Разбор SQL:
    # - LEFT JOIN groups — добавляем имя группы (LEFT — даже если группы нет)
    # - LEFT JOIN phones — добавляем все телефоны контакта
    # - string_agg — собирает несколько телефонов в одну строку через запятую
    # - WHERE g.name ILIKE — поиск без учёта регистра
    # - GROUP BY — группируем по контакту, чтобы string_agg сработал
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
    """Поиск по части email (например 'gmail' найдёт всех с гмейлом)."""
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
        # %{needle}% — это LIKE-маска: % означает "любые символы"
        cur.execute(sql, (f"%{needle}%",))
        print_rows(cur.fetchall())


def sort_contacts() -> None:
    """Показывает контакты, отсортированные по выбранному полю."""
    print("  sort by:  1) name   2) birthday   3) date added")
    choice = ask("  choice: ")
    # Словарь "выбор пользователя → колонка для сортировки"
    # NULLS LAST — пустые даты в конец списка
    column = {"1": "c.name", "2": "c.birthday NULLS LAST", "3": "c.created_at"}.get(choice)
    if not column:
        print("  ! invalid choice")
        return
    # f-string — здесь безопасно, т.к. column берётся из словаря, не от юзера
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
    """
    Постраничный просмотр.
    LIMIT/OFFSET — стандартный SQL способ пагинации.
    Использует функцию list_contacts(limit, offset) из БД.
    """
    page = 0
    while True:
        with get_cursor(dict_rows=True) as (conn, cur):
            # OFFSET — пропустить первые N строк
            # LIMIT — взять следующие M строк
            cur.execute("SELECT * FROM list_contacts(%s, %s);",
                        (PAGE_SIZE, page * PAGE_SIZE))
            rows = cur.fetchall()

        banner(f"page {page + 1}")
        print_rows(rows)
        cmd = input("  [n]ext  [p]rev  [q]uit > ").strip().lower()
        if cmd == "n":
            # Если строк меньше чем размер страницы — мы на последней
            if len(rows) < PAGE_SIZE:
                print("  (already on last page)")
            else:
                page += 1
        elif cmd == "p":
            # max(0, ...) защищает от ухода в минус
            page = max(0, page - 1)
        else:
            return


# =========================================================================
# 3.3 — ИМПОРТ / ЭКСПОРТ
# JSON — для бэкапа всех данных целиком
# CSV  — для импорта данных из Excel или другой системы
# =========================================================================
def _all_contacts_with_phones() -> list[dict]:
    """
    Получает все контакты с их телефонами в виде вложенного JSON.
    Используется для экспорта.
    """
    # json_agg + json_build_object — собирают телефоны в JSON-массив прямо в SQL
    # FILTER (WHERE p.id IS NOT NULL) — игнорировать контакты без телефонов
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
    """Сохраняет все контакты в JSON-файл."""
    # Если юзер не ввёл имя — берём contacts.json по умолчанию
    path = ask("  output file (default contacts.json): ", allow_empty=True) or "contacts.json"
    rows = _all_contacts_with_phones()

    # JSON не умеет сериализовать объекты date — конвертируем в строку
    for r in rows:
        if r["birthday"]:
            r["birthday"] = r["birthday"].isoformat()

    # ensure_ascii=False — чтобы кириллица не превратилась в \uXXXX
    # indent=2 — красивое форматирование с отступами
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    print(f"  ✓ wrote {len(rows)} contacts to {path}")


def import_json() -> None:
    """
    Импортирует контакты из JSON.
    Если контакт уже есть — спрашивает что делать (skip / overwrite).
    Можно ответить "All" чтобы применить решение ко всем оставшимся.
    """
    path = ask("  input file: ")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ! cannot read file: {e}")
        return

    # Запоминаем выбор "ко всем" между итерациями
    answer_all: str | None = None

    with get_cursor() as (conn, cur):
        for entry in data:
            # Проверяем существует ли уже контакт с таким именем
            cur.execute("SELECT 1 FROM contacts WHERE name=%s;", (entry["name"],))
            exists = cur.fetchone() is not None

            if exists:
                if answer_all in ("s", "o"):
                    # Уже выбрали "ко всем" — используем тот же ответ
                    decision = answer_all
                else:
                    print(f"  ! contact '{entry['name']}' already exists.")
                    decision = ask("    [s]kip  [o]verwrite  [A]ll-skip  [O]ll-overwrite : ").lower()
                    # 'a' = пропускать всех оставшихся
                    if decision == "a":
                        decision = answer_all = "s"
                    # 'o' с подтверждением = перезаписать всех оставшихся
                    elif decision == "o" and ask("    apply to all? y/N: ").lower() == "y":
                        answer_all = "o"
                if decision == "s":
                    continue   # пропускаем этот контакт

            # Парсим дату из строки
            bday = entry.get("birthday")
            bday = datetime.strptime(bday, "%Y-%m-%d").date() if bday else None

            # Вызываем UPSERT — добавит если нет, обновит если есть
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s);",
                (entry["name"], entry.get("email"), bday, entry.get("group_name")),
            )
            # Получаем id только что вставленного/обновлённого контакта
            cur.execute("SELECT id FROM contacts WHERE name=%s;", (entry["name"],))
            cid = cur.fetchone()[0]
            # Удаляем старые телефоны и вставляем новые из JSON
            cur.execute("DELETE FROM phones WHERE contact_id=%s;", (cid,))
            for ph in entry.get("phones", []):
                cur.execute(
                    "INSERT INTO phones(contact_id, phone, type) VALUES (%s,%s,%s);",
                    (cid, ph["phone"], ph["type"]),
                )
    print("  ✓ JSON import finished")


def import_csv() -> None:
    """
    Импорт из CSV.
    Структура: name,email,birthday,group,phone,type — один телефон на строку.
    Если у контакта несколько телефонов — несколько строк с одним именем.
    """
    path = ask("  CSV file (default contacts.csv): ", allow_empty=True) or "contacts.csv"
    try:
        # DictReader — читает CSV и каждую строку отдаёт как словарь
        # с ключами из первой строки (заголовков)
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    except FileNotFoundError:
        print("  ! file not found")
        return

    with get_cursor() as (conn, cur):
        for r in rows:
            # Парсим дату или ставим None
            bday = r.get("birthday") or None
            bday = datetime.strptime(bday, "%Y-%m-%d").date() if bday else None

            # UPSERT контакта
            cur.execute(
                "CALL upsert_contact(%s, %s, %s, %s);",
                (r["name"], r.get("email") or None, bday, r.get("group") or None),
            )

            # Если в строке есть телефон — добавляем
            if r.get("phone"):
                cur.execute("SELECT id FROM contacts WHERE name=%s;", (r["name"],))
                cid = cur.fetchone()[0]
                # Хитрый INSERT с проверкой — не вставлять если такой телефон уже есть
                # (защита от дубликатов при повторном импорте)
                cur.execute(
                    "INSERT INTO phones(contact_id, phone, type) "
                    "SELECT %s,%s,%s "
                    "WHERE NOT EXISTS (SELECT 1 FROM phones "
                    "                  WHERE contact_id=%s AND phone=%s);",
                    (cid, r["phone"], r.get("type") or "mobile", cid, r["phone"]),
                )
    print(f"  ✓ imported {len(rows)} CSV rows")


# =========================================================================
# БАЗОВЫЕ CRUD-ОПЕРАЦИИ
# Это операции из Practice 8 — оставлены для удобства
# CRUD = Create, Read, Update, Delete
# =========================================================================
def insert_contact() -> None:
    """
    Добавляет новый контакт или обновляет существующий.
    Использует процедуру upsert_contact (UPSERT = update + insert).
    """
    name  = ask("  name     : ")
    email = ask("  email    : ", allow_empty=True) or None
    bday  = ask_date("  birthday (YYYY-MM-DD, blank to skip): ")
    grp   = ask("  group    : ", allow_empty=True) or None
    with get_cursor() as (conn, cur):
        cur.execute("CALL upsert_contact(%s,%s,%s,%s);", (name, email, bday, grp))
    print("  ✓ saved")


def delete_contact() -> None:
    """
    Удаляет контакт по имени или телефону.
    Благодаря ON DELETE CASCADE в схеме — все его телефоны удалятся автоматически.
    """
    val = ask("  name or phone to delete: ")
    with get_cursor() as (conn, cur):
        cur.execute("CALL delete_contact(%s);", (val,))
    print("  ✓ deleted (if existed)")


# =========================================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================================
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
    """
    Главная функция.
    actions — словарь "номер пункта → функция".
    Вместо длинной цепочки if/elif для каждой опции.
    """
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
        # .get() — если нет такого ключа, вернёт None вместо ошибки
        action = actions.get(choice)
        if action:
            try:
                action()        # вызываем выбранную функцию
            except Exception as e:
                # Ловим ошибки БД, чтобы программа не падала, а оставалась в меню
                print(f"  ! error: {e}")
        else:
            print("  ! unknown option")


# Этот блок выполняется только если запустить файл напрямую (python phonebook.py)
# А не если его импортируют из другого файла
if __name__ == "__main__":
    main()