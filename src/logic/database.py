"""
database.py
SQLite storage layer for Projects, Quotes, and Units.
"""

import sqlite3
import json
import os
import csv
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "corequote.db")
SLIDES_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "slides.csv")


def _json_safe(value):
    """Recursively convert values to JSON-serializable Python primitives."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    # Handle NumPy / pandas scalar types without importing NumPy directly.
    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return _json_safe(item_method())
        except Exception:
            pass

    # Let standard JSON-native primitives pass through.
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    # Last-resort fallback keeps insert robust rather than crashing.
    return str(value)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS board_types (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                brand       TEXT    NOT NULL,
                material    TEXT    NOT NULL,
                thickness   INTEGER NOT NULL,
                length_mm   INTEGER NOT NULL,
                width_mm    INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                client      TEXT    NOT NULL DEFAULT '',
                address     TEXT    NOT NULL DEFAULT '',
                description TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                name        TEXT    NOT NULL,
                notes       TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS units (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id     INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                unit_number  INTEGER NOT NULL,
                unit_type    TEXT    NOT NULL,
                height       INTEGER NOT NULL,
                width        INTEGER NOT NULL,
                depth        INTEGER NOT NULL,
                thickness    INTEGER NOT NULL DEFAULT 16,
                extra_params TEXT    NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS slides (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                brand                 TEXT    NOT NULL,
                model                 TEXT    NOT NULL,
                code                  TEXT    NOT NULL DEFAULT '',
                length                INTEGER NOT NULL,
                side_length           INTEGER NOT NULL,
                side_clearance_total  INTEGER NOT NULL,
                created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (brand, model, code)
            );
        """)

        # Lightweight migrations for existing DBs.
        quote_cols = {r["name"] for r in conn.execute("PRAGMA table_info(quotes)").fetchall()}
        if "default_carcass_board_type_id" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_carcass_board_type_id INTEGER")
        if "default_door_board_type_id" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_door_board_type_id INTEGER")
        if "unit_defaults_json" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN unit_defaults_json TEXT NOT NULL DEFAULT '{}' ")
        if "default_slide_brand" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_brand TEXT")
        if "default_slide_model" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_model TEXT")
        if "default_slide_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_code TEXT")
        if "default_slide_length" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_length INTEGER")
        if "default_slide_side_length" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_side_length INTEGER")
        if "default_slide_side_clearance_total" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_slide_side_clearance_total INTEGER")

        unit_cols = {r["name"] for r in conn.execute("PRAGMA table_info(units)").fetchall()}
        if "carcass_board_type_id" not in unit_cols:
            conn.execute("ALTER TABLE units ADD COLUMN carcass_board_type_id INTEGER")
        if "door_board_type_id" not in unit_cols:
            conn.execute("ALTER TABLE units ADD COLUMN door_board_type_id INTEGER")

        _migrate_slides_csv_to_db(conn)


def _migrate_slides_csv_to_db(conn: sqlite3.Connection):
    """Import legacy slides.csv into SQLite once, without duplicating existing rows."""
    existing_count = conn.execute("SELECT COUNT(*) AS c FROM slides").fetchone()["c"]
    if existing_count > 0:
        return

    if not os.path.exists(SLIDES_CSV_PATH) or os.path.getsize(SLIDES_CSV_PATH) == 0:
        return

    with open(SLIDES_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO slides
                       (brand, model, code, length, side_length, side_clearance_total)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(row.get("brand", "")).strip(),
                        str(row.get("model", "")).strip(),
                        str(row.get("code", "")).strip(),
                        int(row.get("length", 0) or 0),
                        int(row.get("side_length", 0) or 0),
                        int(row.get("side_clearance_total", 0) or 0),
                    ),
                )
            except Exception:
                # Keep migration resilient even if a row is malformed.
                continue


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(name: str, client: str = "", address: str = "", description: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, client, address, description) VALUES (?, ?, ?, ?)",
            (name, client, address, description)
        )
        return cur.lastrowid


def get_all_projects() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_project(project_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None


def update_project(project_id: int, name: str, client: str, address: str, description: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE projects SET name=?, client=?, address=?, description=? WHERE id=?",
            (name, client, address, description, project_id)
        )


def delete_project(project_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


# ── Quotes ────────────────────────────────────────────────────────────────────

def create_quote(
    project_id: int,
    name: str,
    notes: str = "",
    default_carcass_board_type_id: int | None = None,
    default_door_board_type_id: int | None = None,
    unit_defaults: dict | None = None,
    default_slide: dict | None = None,
) -> int:
    unit_defaults = _json_safe(unit_defaults or {})
    default_slide = _json_safe(default_slide or {})
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO quotes
               (project_id, name, notes, default_carcass_board_type_id, default_door_board_type_id,
                unit_defaults_json, default_slide_brand, default_slide_model, default_slide_code,
                default_slide_length, default_slide_side_length, default_slide_side_clearance_total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                name,
                notes,
                default_carcass_board_type_id,
                default_door_board_type_id,
                json.dumps(unit_defaults),
                default_slide.get("brand"),
                default_slide.get("model"),
                default_slide.get("code"),
                default_slide.get("length"),
                default_slide.get("side_length"),
                default_slide.get("side_clearance_total"),
            )
        )
        return cur.lastrowid


def get_quotes_for_project(project_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM quotes WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["unit_defaults"] = json.loads(d.get("unit_defaults_json") or "{}")
            result.append(d)
        return result


def get_quote(quote_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM quotes WHERE id = ?", (quote_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["unit_defaults"] = json.loads(d.get("unit_defaults_json") or "{}")
        return d


def update_quote(
    quote_id: int,
    name: str,
    notes: str,
    default_carcass_board_type_id: int | None = None,
    default_door_board_type_id: int | None = None,
    unit_defaults: dict | None = None,
    default_slide: dict | None = None,
):
    unit_defaults = _json_safe(unit_defaults or {})
    default_slide = _json_safe(default_slide or {})
    with get_connection() as conn:
        conn.execute(
            """UPDATE quotes
               SET name=?, notes=?, default_carcass_board_type_id=?, default_door_board_type_id=?,
                   unit_defaults_json=?,
                   default_slide_brand=?, default_slide_model=?, default_slide_code=?,
                   default_slide_length=?, default_slide_side_length=?, default_slide_side_clearance_total=?
               WHERE id=?""",
            (
                name,
                notes,
                default_carcass_board_type_id,
                default_door_board_type_id,
                json.dumps(unit_defaults),
                default_slide.get("brand"),
                default_slide.get("model"),
                default_slide.get("code"),
                default_slide.get("length"),
                default_slide.get("side_length"),
                default_slide.get("side_clearance_total"),
                quote_id,
            )
        )


def delete_quote(quote_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))


# ── Units ─────────────────────────────────────────────────────────────────────

def _next_unit_number(conn: sqlite3.Connection, quote_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(unit_number), 0) + 1 FROM units WHERE quote_id = ?",
        (quote_id,)
    ).fetchone()
    return row[0]


def add_unit(
    quote_id: int,
    unit_type: str,
    height: int,
    width: int,
    depth: int,
    thickness: int = 16,
    carcass_board_type_id: int | None = None,
    door_board_type_id: int | None = None,
    extra_params: dict = None,
) -> int:
    if extra_params is None:
        extra_params = {}
    extra_params = _json_safe(extra_params)
    with get_connection() as conn:
        unit_number = _next_unit_number(conn, quote_id)
        cur = conn.execute(
            """INSERT INTO units
               (quote_id, unit_number, unit_type, height, width, depth, thickness,
                carcass_board_type_id, door_board_type_id, extra_params)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (quote_id, unit_number, unit_type, height, width, depth, thickness,
             carcass_board_type_id, door_board_type_id,
             json.dumps(extra_params))
        )
        return cur.lastrowid


def update_unit(
    unit_id: int,
    unit_type: str,
    height: int,
    width: int,
    depth: int,
    thickness: int = 16,
    carcass_board_type_id: int | None = None,
    door_board_type_id: int | None = None,
    extra_params: dict = None,
):
    if extra_params is None:
        extra_params = {}
    extra_params = _json_safe(extra_params)
    with get_connection() as conn:
        conn.execute(
            """UPDATE units
               SET unit_type=?, height=?, width=?, depth=?, thickness=?,
                   carcass_board_type_id=?, door_board_type_id=?, extra_params=?
               WHERE id=?""",
            (
                unit_type,
                height,
                width,
                depth,
                thickness,
                carcass_board_type_id,
                door_board_type_id,
                json.dumps(extra_params),
                unit_id,
            )
        )


def get_units_for_quote(quote_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM units WHERE quote_id = ? ORDER BY unit_number ASC",
            (quote_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["extra_params"] = json.loads(d["extra_params"])
            result.append(d)
        return result


# ── Board Types ────────────────────────────────────────────────────────────────

def create_board_type(brand: str, material: str, thickness: int, length_mm: int, width_mm: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO board_types (brand, material, thickness, length_mm, width_mm)
               VALUES (?, ?, ?, ?, ?)""",
            (brand, material, thickness, length_mm, width_mm),
        )
        return cur.lastrowid


def get_all_board_types() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM board_types ORDER BY brand ASC, material ASC, thickness ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_board_type(board_type_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM board_types WHERE id = ?", (board_type_id,)).fetchone()
        return dict(row) if row else None


def update_board_type(board_type_id: int, brand: str, material: str, thickness: int, length_mm: int, width_mm: int):
    with get_connection() as conn:
        conn.execute(
            """UPDATE board_types
               SET brand=?, material=?, thickness=?, length_mm=?, width_mm=?
               WHERE id=?""",
            (brand, material, thickness, length_mm, width_mm, board_type_id),
        )


def delete_board_type(board_type_id: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE quotes SET default_carcass_board_type_id = NULL WHERE default_carcass_board_type_id = ?",
            (board_type_id,),
        )
        conn.execute(
            "UPDATE quotes SET default_door_board_type_id = NULL WHERE default_door_board_type_id = ?",
            (board_type_id,),
        )
        conn.execute(
            "UPDATE units SET carcass_board_type_id = NULL WHERE carcass_board_type_id = ?",
            (board_type_id,),
        )
        conn.execute(
            "UPDATE units SET door_board_type_id = NULL WHERE door_board_type_id = ?",
            (board_type_id,),
        )
        conn.execute("DELETE FROM board_types WHERE id = ?", (board_type_id,))


# ── Slides ──────────────────────────────────────────────────────────────────────

def create_slide(
    brand: str,
    model: str,
    code: str,
    length: int,
    side_length: int,
    side_clearance_total: int,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO slides
               (brand, model, code, length, side_length, side_clearance_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (brand.strip(), model.strip(), code.strip(), int(length), int(side_length), int(side_clearance_total)),
        )
        return cur.lastrowid


def get_all_slides() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM slides
               ORDER BY brand ASC, model ASC, length ASC, code ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def update_slide(
    slide_id: int,
    brand: str,
    model: str,
    code: str,
    length: int,
    side_length: int,
    side_clearance_total: int,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE slides
               SET brand=?, model=?, code=?, length=?, side_length=?, side_clearance_total=?
               WHERE id=?""",
            (brand.strip(), model.strip(), code.strip(), int(length), int(side_length), int(side_clearance_total), slide_id),
        )


def delete_slide(slide_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM slides WHERE id = ?", (slide_id,))


def delete_unit(unit_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))
        # Renumber remaining units in the same quote
        row = conn.execute(
            "SELECT quote_id FROM units WHERE id = ?", (unit_id,)
        ).fetchone()
        # unit already deleted, renumber via a subquery approach
        # We'll renumber all units for the affected quote after deletion
    # Re-fetch quote_id from the deleted unit is not possible; caller should renumber if needed.
    # Instead, renumber is handled by get_units_for_quote returning ordered results.


def renumber_units(quote_id: int):
    """Renumber unit_number sequentially after a deletion."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM units WHERE quote_id = ? ORDER BY unit_number ASC",
            (quote_id,)
        ).fetchall()
        for i, row in enumerate(rows, start=1):
            conn.execute(
                "UPDATE units SET unit_number = ? WHERE id = ?",
                (i, row["id"])
            )


def delete_unit_and_renumber(unit_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT quote_id FROM units WHERE id = ?", (unit_id,)
        ).fetchone()
        if not row:
            return
        quote_id = row["quote_id"]
        conn.execute("DELETE FROM units WHERE id = ?", (unit_id,))
        # Renumber
        rows = conn.execute(
            "SELECT id FROM units WHERE quote_id = ? ORDER BY unit_number ASC",
            (quote_id,)
        ).fetchall()
        for i, r in enumerate(rows, start=1):
            conn.execute(
                "UPDATE units SET unit_number = ? WHERE id = ?",
                (i, r["id"])
            )


# Initialise on import
init_db()
