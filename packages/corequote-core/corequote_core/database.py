"""
database.py
SQLite storage layer for Projects, Quotes, and Units.
"""

import sqlite3
import json
import os
import csv
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = os.environ.get("COREQUOTE_DB_PATH", str(REPO_ROOT / "data" / "corequote.db"))
SLIDES_CSV_PATH = os.environ.get("COREQUOTE_SLIDES_CSV_PATH", str(REPO_ROOT / "data" / "slides.csv"))


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
                costing_mode TEXT   NOT NULL DEFAULT 'sheet',
                edging_cost_cents_per_m INTEGER NOT NULL DEFAULT 0,
                cut_edge_labour_cents_per_board INTEGER NOT NULL DEFAULT 0,
                sqm_price_cents INTEGER NOT NULL DEFAULT 0,
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
                side_height_uplift    INTEGER NOT NULL DEFAULT 0,
                created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (brand, model, code)
            );

            CREATE TABLE IF NOT EXISTS hinges (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                brand              TEXT    NOT NULL,
                model              TEXT    NOT NULL,
                code               TEXT    NOT NULL DEFAULT '',
                opening_angle_deg  INTEGER NOT NULL,
                created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (brand, model, code)
            );

            CREATE TABLE IF NOT EXISTS handles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                supplier    TEXT    NOT NULL DEFAULT '',
                code        TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (name, supplier, code)
            );

            CREATE TABLE IF NOT EXISTS extra_categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS extras (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                category_id  INTEGER NOT NULL REFERENCES extra_categories(id) ON DELETE RESTRICT,
                supplier     TEXT    NOT NULL DEFAULT '',
                code         TEXT    NOT NULL DEFAULT '',
                notes        TEXT    NOT NULL DEFAULT '',
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (name, category_id, supplier, code)
            );

            CREATE TABLE IF NOT EXISTS quote_extras (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id    INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                extra_id    INTEGER NOT NULL REFERENCES extras(id) ON DELETE RESTRICT,
                qty         INTEGER NOT NULL DEFAULT 1,
                notes       TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pricing_settings (
                id            INTEGER PRIMARY KEY CHECK (id = 1),
                vat_rate_bps  INTEGER NOT NULL DEFAULT 1500,
                default_markup_bps INTEGER NOT NULL DEFAULT 2500,
                updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS price_lists (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT    NOT NULL,
                status         TEXT    NOT NULL DEFAULT 'draft',
                effective_from TEXT,
                effective_to   TEXT,
                created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS price_list_items (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                price_list_id     INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
                item_type         TEXT    NOT NULL,
                item_ref_id       INTEGER,
                item_key          TEXT    NOT NULL,
                uom               TEXT    NOT NULL,
                unit_price_cents  INTEGER NOT NULL,
                created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (price_list_id, item_type, item_key)
            );

            CREATE TABLE IF NOT EXISTS quote_pricing_runs (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id               INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                price_list_id          INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE RESTRICT,
                pricing_mode           TEXT    NOT NULL,
                pricing_value_bps      INTEGER NOT NULL DEFAULT 0,
                vat_rate_bps_snapshot  INTEGER NOT NULL,
                subtotal_cents         INTEGER NOT NULL,
                sell_before_vat_cents  INTEGER NOT NULL,
                vat_cents              INTEGER NOT NULL,
                grand_total_cents      INTEGER NOT NULL,
                is_current             INTEGER NOT NULL DEFAULT 1,
                created_at             TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS quote_pricing_lines (
                id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                pricing_run_id            INTEGER NOT NULL REFERENCES quote_pricing_runs(id) ON DELETE CASCADE,
                source_type               TEXT    NOT NULL,
                source_ref                TEXT    NOT NULL DEFAULT '',
                description               TEXT    NOT NULL,
                qty                       REAL    NOT NULL,
                uom                       TEXT    NOT NULL,
                unit_price_cents_snapshot INTEGER NOT NULL,
                line_total_cents_snapshot INTEGER NOT NULL,
                meta_json                 TEXT    NOT NULL DEFAULT '{}'
            );
        """)

        # Lightweight migrations for existing DBs.
        quote_cols = {r["name"] for r in conn.execute("PRAGMA table_info(quotes)").fetchall()}
        if "default_carcass_board_type_id" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_carcass_board_type_id INTEGER")
        if "default_door_board_type_id" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_door_board_type_id INTEGER")
        if "default_panel_board_type_id" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_panel_board_type_id INTEGER")
        if "unit_defaults_json" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN unit_defaults_json TEXT NOT NULL DEFAULT '{}' ")
        if "custom_panels_json" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN custom_panels_json TEXT NOT NULL DEFAULT '{}' ")
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
        if "default_hinge_brand" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_hinge_brand TEXT")
        if "default_hinge_model" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_hinge_model TEXT")
        if "default_hinge_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_hinge_code TEXT")
        if "default_hinge_opening_angle_deg" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_hinge_opening_angle_deg INTEGER")
        if "default_base_handle_name" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_base_handle_name TEXT")
        if "default_base_handle_supplier" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_base_handle_supplier TEXT")
        if "default_base_handle_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_base_handle_code TEXT")
        if "default_wall_handle_name" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_wall_handle_name TEXT")
        if "default_wall_handle_supplier" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_wall_handle_supplier TEXT")
        if "default_wall_handle_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_wall_handle_code TEXT")
        if "default_tall_handle_name" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_tall_handle_name TEXT")
        if "default_tall_handle_supplier" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_tall_handle_supplier TEXT")
        if "default_tall_handle_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_tall_handle_code TEXT")
        if "default_drawer_handle_name" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_drawer_handle_name TEXT")
        if "default_drawer_handle_supplier" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_drawer_handle_supplier TEXT")
        if "default_drawer_handle_code" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_drawer_handle_code TEXT")
        if "default_markup_bps" not in quote_cols:
            conn.execute("ALTER TABLE quotes ADD COLUMN default_markup_bps INTEGER")

        pricing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(pricing_settings)").fetchall()}
        if "default_markup_bps" not in pricing_cols:
            conn.execute("ALTER TABLE pricing_settings ADD COLUMN default_markup_bps INTEGER NOT NULL DEFAULT 2500")

        unit_cols = {r["name"] for r in conn.execute("PRAGMA table_info(units)").fetchall()}
        if "carcass_board_type_id" not in unit_cols:
            conn.execute("ALTER TABLE units ADD COLUMN carcass_board_type_id INTEGER")
        if "door_board_type_id" not in unit_cols:
            conn.execute("ALTER TABLE units ADD COLUMN door_board_type_id INTEGER")

        board_cols = {r["name"] for r in conn.execute("PRAGMA table_info(board_types)").fetchall()}
        if "costing_mode" not in board_cols:
            conn.execute("ALTER TABLE board_types ADD COLUMN costing_mode TEXT NOT NULL DEFAULT 'sheet'")
        if "edging_cost_cents_per_m" not in board_cols:
            conn.execute("ALTER TABLE board_types ADD COLUMN edging_cost_cents_per_m INTEGER NOT NULL DEFAULT 0")
        if "cut_edge_labour_cents_per_board" not in board_cols:
            conn.execute("ALTER TABLE board_types ADD COLUMN cut_edge_labour_cents_per_board INTEGER NOT NULL DEFAULT 0")
        if "sqm_price_cents" not in board_cols:
            conn.execute("ALTER TABLE board_types ADD COLUMN sqm_price_cents INTEGER NOT NULL DEFAULT 0")

        slide_cols = {r["name"] for r in conn.execute("PRAGMA table_info(slides)").fetchall()}
        if "side_height_uplift" not in slide_cols:
            conn.execute("ALTER TABLE slides ADD COLUMN side_height_uplift INTEGER NOT NULL DEFAULT 0")

        hinge_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hinges)").fetchall()}
        if "opening_angle_deg" not in hinge_cols:
            conn.execute("ALTER TABLE hinges ADD COLUMN opening_angle_deg INTEGER NOT NULL DEFAULT 110")

        _migrate_slides_csv_to_db(conn)
        _seed_default_pricing(conn)


def _seed_default_pricing(conn: sqlite3.Connection):
    """Seed baseline pricing records for first-run DBs."""
    conn.execute(
        """INSERT OR IGNORE INTO pricing_settings (id, vat_rate_bps, default_markup_bps)
           VALUES (1, 1500, 2500)"""
    )

    active_list = conn.execute(
        "SELECT id FROM price_lists WHERE status = 'active' ORDER BY datetime(created_at) DESC LIMIT 1"
    ).fetchone()
    if active_list:
        return

    conn.execute(
        """INSERT INTO price_lists (name, status)
           VALUES (?, 'active')""",
        ("Default Price List",),
    )


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
                       (brand, model, code, length, side_length, side_clearance_total, side_height_uplift)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(row.get("brand", "")).strip(),
                        str(row.get("model", "")).strip(),
                        str(row.get("code", "")).strip(),
                        int(row.get("length", 0) or 0),
                        int(row.get("side_length", 0) or 0),
                        int(row.get("side_clearance_total", 0) or 0),
                        int(row.get("side_height_uplift", 0) or 0),
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
    default_panel_board_type_id: int | None = None,
    unit_defaults: dict | None = None,
    default_slide: dict | None = None,
    default_hinge: dict | None = None,
    default_base_handle: dict | None = None,
    default_wall_handle: dict | None = None,
    default_tall_handle: dict | None = None,
    default_drawer_handle: dict | None = None,
) -> int:
    unit_defaults = _json_safe(unit_defaults or {})
    default_slide = _json_safe(default_slide or {})
    default_hinge = _json_safe(default_hinge or {})
    default_base_handle = _json_safe(default_base_handle or {})
    default_wall_handle = _json_safe(default_wall_handle or {})
    default_tall_handle = _json_safe(default_tall_handle or {})
    default_drawer_handle = _json_safe(default_drawer_handle or {})
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO quotes
               (project_id, name, notes, default_carcass_board_type_id, default_door_board_type_id,
                default_panel_board_type_id, unit_defaults_json, custom_panels_json,
                default_slide_brand, default_slide_model, default_slide_code,
                default_slide_length, default_slide_side_length, default_slide_side_clearance_total,
                 default_hinge_brand, default_hinge_model, default_hinge_code, default_hinge_opening_angle_deg,
                 default_base_handle_name, default_base_handle_supplier, default_base_handle_code,
                 default_wall_handle_name, default_wall_handle_supplier, default_wall_handle_code,
                 default_tall_handle_name, default_tall_handle_supplier, default_tall_handle_code,
                 default_drawer_handle_name, default_drawer_handle_supplier, default_drawer_handle_code)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                name,
                notes,
                default_carcass_board_type_id,
                default_door_board_type_id,
                default_panel_board_type_id,
                json.dumps(unit_defaults),
                json.dumps({}),
                default_slide.get("brand"),
                default_slide.get("model"),
                default_slide.get("code"),
                default_slide.get("length"),
                default_slide.get("side_length"),
                default_slide.get("side_clearance_total"),
                default_hinge.get("brand"),
                default_hinge.get("model"),
                default_hinge.get("code"),
                default_hinge.get("opening_angle_deg"),
                default_base_handle.get("name"),
                default_base_handle.get("supplier"),
                default_base_handle.get("code"),
                default_wall_handle.get("name"),
                default_wall_handle.get("supplier"),
                default_wall_handle.get("code"),
                default_tall_handle.get("name"),
                default_tall_handle.get("supplier"),
                default_tall_handle.get("code"),
                default_drawer_handle.get("name"),
                default_drawer_handle.get("supplier"),
                default_drawer_handle.get("code"),
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
            d["custom_panels"] = json.loads(d.get("custom_panels_json") or "{}")
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
        d["custom_panels"] = json.loads(d.get("custom_panels_json") or "{}")
        return d


def update_quote(
    quote_id: int,
    name: str,
    notes: str,
    default_carcass_board_type_id: int | None = None,
    default_door_board_type_id: int | None = None,
    default_panel_board_type_id: int | None = None,
    unit_defaults: dict | None = None,
    default_slide: dict | None = None,
    default_hinge: dict | None = None,
    default_base_handle: dict | None = None,
    default_wall_handle: dict | None = None,
    default_tall_handle: dict | None = None,
    default_drawer_handle: dict | None = None,
):
    unit_defaults = _json_safe(unit_defaults or {})
    default_slide = _json_safe(default_slide or {})
    default_hinge = _json_safe(default_hinge or {})
    default_base_handle = _json_safe(default_base_handle or {})
    default_wall_handle = _json_safe(default_wall_handle or {})
    default_tall_handle = _json_safe(default_tall_handle or {})
    default_drawer_handle = _json_safe(default_drawer_handle or {})
    with get_connection() as conn:
        conn.execute(
            """UPDATE quotes
               SET name=?, notes=?, default_carcass_board_type_id=?, default_door_board_type_id=?,
                   default_panel_board_type_id=?, unit_defaults_json=?,
                   default_slide_brand=?, default_slide_model=?, default_slide_code=?,
                   default_slide_length=?, default_slide_side_length=?, default_slide_side_clearance_total=?,
                   default_hinge_brand=?, default_hinge_model=?, default_hinge_code=?, default_hinge_opening_angle_deg=?,
                   default_base_handle_name=?, default_base_handle_supplier=?, default_base_handle_code=?,
                   default_wall_handle_name=?, default_wall_handle_supplier=?, default_wall_handle_code=?,
                   default_tall_handle_name=?, default_tall_handle_supplier=?, default_tall_handle_code=?,
                   default_drawer_handle_name=?, default_drawer_handle_supplier=?, default_drawer_handle_code=?
               WHERE id=?""",
            (
                name,
                notes,
                default_carcass_board_type_id,
                default_door_board_type_id,
                default_panel_board_type_id,
                json.dumps(unit_defaults),
                default_slide.get("brand"),
                default_slide.get("model"),
                default_slide.get("code"),
                default_slide.get("length"),
                default_slide.get("side_length"),
                default_slide.get("side_clearance_total"),
                default_hinge.get("brand"),
                default_hinge.get("model"),
                default_hinge.get("code"),
                default_hinge.get("opening_angle_deg"),
                default_base_handle.get("name"),
                default_base_handle.get("supplier"),
                default_base_handle.get("code"),
                default_wall_handle.get("name"),
                default_wall_handle.get("supplier"),
                default_wall_handle.get("code"),
                default_tall_handle.get("name"),
                default_tall_handle.get("supplier"),
                default_tall_handle.get("code"),
                default_drawer_handle.get("name"),
                default_drawer_handle.get("supplier"),
                default_drawer_handle.get("code"),
                quote_id,
            )
        )


def get_quote_panels(quote_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT custom_panels_json FROM quotes WHERE id = ?", (quote_id,)
        ).fetchone()
        if not row:
            return {}
        return json.loads(row["custom_panels_json"] or "{}")


def update_quote_panels(quote_id: int, payload: dict):
    payload = _json_safe(payload or {})
    with get_connection() as conn:
        conn.execute(
            "UPDATE quotes SET custom_panels_json = ? WHERE id = ?",
            (json.dumps(payload), quote_id),
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

def create_board_type(
    brand: str,
    material: str,
    thickness: int,
    length_mm: int,
    width_mm: int,
    costing_mode: str = "sheet",
    edging_cost_cents_per_m: int = 0,
    cut_edge_labour_cents_per_board: int = 0,
    sqm_price_cents: int = 0,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO board_types
               (brand, material, thickness, length_mm, width_mm, costing_mode,
                edging_cost_cents_per_m, cut_edge_labour_cents_per_board, sqm_price_cents)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                brand,
                material,
                thickness,
                length_mm,
                width_mm,
                str(costing_mode or "sheet").strip().lower(),
                int(edging_cost_cents_per_m or 0),
                int(cut_edge_labour_cents_per_board or 0),
                int(sqm_price_cents or 0),
            ),
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


def update_board_type(
    board_type_id: int,
    brand: str,
    material: str,
    thickness: int,
    length_mm: int,
    width_mm: int,
    costing_mode: str = "sheet",
    edging_cost_cents_per_m: int = 0,
    cut_edge_labour_cents_per_board: int = 0,
    sqm_price_cents: int = 0,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE board_types
               SET brand=?, material=?, thickness=?, length_mm=?, width_mm=?, costing_mode=?,
                   edging_cost_cents_per_m=?, cut_edge_labour_cents_per_board=?, sqm_price_cents=?
               WHERE id=?""",
            (
                brand,
                material,
                thickness,
                length_mm,
                width_mm,
                str(costing_mode or "sheet").strip().lower(),
                int(edging_cost_cents_per_m or 0),
                int(cut_edge_labour_cents_per_board or 0),
                int(sqm_price_cents or 0),
                board_type_id,
            ),
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
    side_height_uplift: int = 0,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO slides
               (brand, model, code, length, side_length, side_clearance_total, side_height_uplift)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                brand.strip(),
                model.strip(),
                code.strip(),
                int(length),
                int(side_length),
                int(side_clearance_total),
                int(side_height_uplift),
            ),
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
    side_height_uplift: int = 0,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE slides
               SET brand=?, model=?, code=?, length=?, side_length=?, side_clearance_total=?, side_height_uplift=?
               WHERE id=?""",
            (
                brand.strip(),
                model.strip(),
                code.strip(),
                int(length),
                int(side_length),
                int(side_clearance_total),
                int(side_height_uplift),
                slide_id,
            ),
        )


def delete_slide(slide_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM slides WHERE id = ?", (slide_id,))


# ── Hinges ─────────────────────────────────────────────────────────────────────

def create_hinge(
    brand: str,
    model: str,
    code: str,
    opening_angle_deg: int,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO hinges
               (brand, model, code, opening_angle_deg)
               VALUES (?, ?, ?, ?)""",
            (
                brand.strip(),
                model.strip(),
                code.strip(),
                int(opening_angle_deg),
            ),
        )
        return cur.lastrowid


def get_all_hinges() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM hinges
               ORDER BY brand ASC, model ASC, opening_angle_deg ASC, code ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def update_hinge(
    hinge_id: int,
    brand: str,
    model: str,
    code: str,
    opening_angle_deg: int,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE hinges
               SET brand=?, model=?, code=?, opening_angle_deg=?
               WHERE id=?""",
            (
                brand.strip(),
                model.strip(),
                code.strip(),
                int(opening_angle_deg),
                hinge_id,
            ),
        )


def delete_hinge(hinge_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM hinges WHERE id = ?", (hinge_id,))


# ── Handles ─────────────────────────────────────────────────────────────────────

def create_handle(name: str, supplier: str, code: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO handles (name, supplier, code)
               VALUES (?, ?, ?)""",
            (name.strip(), supplier.strip(), code.strip()),
        )
        return cur.lastrowid


def get_all_handles() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM handles ORDER BY name ASC, supplier ASC, code ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_handle(handle_id: int, name: str, supplier: str, code: str):
    with get_connection() as conn:
        conn.execute(
            """UPDATE handles
               SET name=?, supplier=?, code=?
               WHERE id=?""",
            (name.strip(), supplier.strip(), code.strip(), int(handle_id)),
        )


def delete_handle(handle_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM handles WHERE id = ?", (int(handle_id),))


# ── Extra Categories ───────────────────────────────────────────────────────────

def create_extra_category(name: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO extra_categories (name) VALUES (?)",
            (name.strip(),),
        )
        return cur.lastrowid


def get_all_extra_categories() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM extra_categories ORDER BY name ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_extra_category(category_id: int, name: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE extra_categories SET name = ? WHERE id = ?",
            (name.strip(), int(category_id)),
        )


def delete_extra_category(category_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM extra_categories WHERE id = ?", (int(category_id),))


# ── Extras ─────────────────────────────────────────────────────────────────────

def create_extra(name: str, category_id: int, supplier: str, code: str, notes: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO extras (name, category_id, supplier, code, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (name.strip(), int(category_id), supplier.strip(), code.strip(), notes.strip()),
        )
        return cur.lastrowid


def get_all_extras() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT e.*, c.name AS category_name
               FROM extras e
               JOIN extra_categories c ON c.id = e.category_id
               ORDER BY c.name ASC, e.name ASC, e.supplier ASC, e.code ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def update_extra(extra_id: int, name: str, category_id: int, supplier: str, code: str, notes: str = ""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE extras
               SET name=?, category_id=?, supplier=?, code=?, notes=?
               WHERE id=?""",
            (name.strip(), int(category_id), supplier.strip(), code.strip(), notes.strip(), int(extra_id)),
        )


def delete_extra(extra_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM extras WHERE id = ?", (int(extra_id),))


# ── Quote Extras ───────────────────────────────────────────────────────────────

def add_quote_extra(quote_id: int, extra_id: int, qty: int, notes: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO quote_extras (quote_id, extra_id, qty, notes)
               VALUES (?, ?, ?, ?)""",
            (int(quote_id), int(extra_id), max(1, int(qty)), notes.strip()),
        )
        return cur.lastrowid


def get_quote_extras(quote_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT qe.id, qe.quote_id, qe.extra_id, qe.qty, qe.notes, qe.created_at,
                      e.name AS extra_name, e.supplier AS extra_supplier, e.code AS extra_code,
                      c.id AS category_id, c.name AS category_name
               FROM quote_extras qe
               JOIN extras e ON e.id = qe.extra_id
               JOIN extra_categories c ON c.id = e.category_id
               WHERE qe.quote_id = ?
               ORDER BY c.name ASC, e.name ASC, qe.created_at ASC""",
            (int(quote_id),),
        ).fetchall()
        return [dict(r) for r in rows]


def update_quote_extra(quote_extra_id: int, extra_id: int, qty: int, notes: str = ""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE quote_extras
               SET extra_id=?, qty=?, notes=?
               WHERE id=?""",
            (int(extra_id), max(1, int(qty)), notes.strip(), int(quote_extra_id)),
        )


def delete_quote_extra(quote_extra_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM quote_extras WHERE id = ?", (int(quote_extra_id),))


# ── Pricing ────────────────────────────────────────────────────────────────────

def get_pricing_settings() -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM pricing_settings WHERE id = 1").fetchone()
        if not row:
            conn.execute("INSERT OR IGNORE INTO pricing_settings (id, vat_rate_bps) VALUES (1, 1500)")
            row = conn.execute("SELECT * FROM pricing_settings WHERE id = 1").fetchone()
        return dict(row)


def update_vat_rate_bps(vat_rate_bps: int):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO pricing_settings (id, vat_rate_bps, updated_at)
               VALUES (1, ?, datetime('now'))
               ON CONFLICT(id) DO UPDATE
               SET vat_rate_bps=excluded.vat_rate_bps, updated_at=datetime('now')""",
            (int(vat_rate_bps),),
        )


def update_default_markup_bps(default_markup_bps: int):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO pricing_settings (id, default_markup_bps, updated_at)
               VALUES (1, ?, datetime('now'))
               ON CONFLICT(id) DO UPDATE
               SET default_markup_bps=excluded.default_markup_bps, updated_at=datetime('now')""",
            (int(default_markup_bps),),
        )


def update_quote_default_markup_bps(quote_id: int, default_markup_bps: int | None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE quotes SET default_markup_bps = ? WHERE id = ?",
            (int(default_markup_bps) if default_markup_bps is not None else None, int(quote_id)),
        )


def create_price_list(name: str, status: str = "draft", effective_from: str | None = None, effective_to: str | None = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO price_lists (name, status, effective_from, effective_to)
               VALUES (?, ?, ?, ?)""",
            (str(name).strip(), str(status).strip(), effective_from, effective_to),
        )
        return int(cur.lastrowid)


def get_all_price_lists() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM price_lists
               ORDER BY datetime(created_at) DESC, id DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_price_list() -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT * FROM price_lists
               WHERE status = 'active'
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1"""
        ).fetchone()
        return dict(row) if row else None


def set_price_list_status(price_list_id: int, status: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE price_lists SET status=? WHERE id=?",
            (str(status).strip(), int(price_list_id)),
        )


def upsert_price_list_item(
    price_list_id: int,
    item_type: str,
    item_key: str,
    uom: str,
    unit_price_cents: int,
    item_ref_id: int | None = None,
):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO price_list_items
               (price_list_id, item_type, item_ref_id, item_key, uom, unit_price_cents)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(price_list_id, item_type, item_key) DO UPDATE SET
                   item_ref_id=excluded.item_ref_id,
                   uom=excluded.uom,
                   unit_price_cents=excluded.unit_price_cents""",
            (
                int(price_list_id),
                str(item_type).strip(),
                int(item_ref_id) if item_ref_id is not None else None,
                str(item_key).strip(),
                str(uom).strip(),
                int(unit_price_cents),
            ),
        )


def get_price_list_items(price_list_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM price_list_items
               WHERE price_list_id = ?
               ORDER BY item_type ASC, item_key ASC""",
            (int(price_list_id),),
        ).fetchall()
        return [dict(r) for r in rows]


def create_quote_pricing_run(
    quote_id: int,
    price_list_id: int,
    pricing_mode: str,
    pricing_value_bps: int,
    vat_rate_bps_snapshot: int,
    subtotal_cents: int,
    sell_before_vat_cents: int,
    vat_cents: int,
    grand_total_cents: int,
    lines: list[dict],
) -> int:
    with get_connection() as conn:
        conn.execute("UPDATE quote_pricing_runs SET is_current = 0 WHERE quote_id = ?", (int(quote_id),))
        cur = conn.execute(
            """INSERT INTO quote_pricing_runs
               (quote_id, price_list_id, pricing_mode, pricing_value_bps, vat_rate_bps_snapshot,
                subtotal_cents, sell_before_vat_cents, vat_cents, grand_total_cents, is_current)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                int(quote_id),
                int(price_list_id),
                str(pricing_mode),
                int(pricing_value_bps),
                int(vat_rate_bps_snapshot),
                int(subtotal_cents),
                int(sell_before_vat_cents),
                int(vat_cents),
                int(grand_total_cents),
            ),
        )
        run_id = int(cur.lastrowid)

        for line in lines:
            conn.execute(
                """INSERT INTO quote_pricing_lines
                   (pricing_run_id, source_type, source_ref, description, qty, uom,
                    unit_price_cents_snapshot, line_total_cents_snapshot, meta_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    str(line.get("source_type", "")).strip(),
                    str(line.get("source_ref", "")).strip(),
                    str(line.get("description", "")).strip(),
                    float(line.get("qty", 0.0) or 0.0),
                    str(line.get("uom", "")).strip(),
                    int(line.get("unit_price_cents", 0) or 0),
                    int(line.get("line_total_cents", 0) or 0),
                    json.dumps(_json_safe(line.get("meta", {}) or {})),
                ),
            )
        return run_id


def get_current_quote_pricing_run(quote_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT * FROM quote_pricing_runs
               WHERE quote_id = ? AND is_current = 1
               ORDER BY datetime(created_at) DESC, id DESC
               LIMIT 1""",
            (int(quote_id),),
        ).fetchone()
        return dict(row) if row else None


def get_quote_pricing_runs(quote_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM quote_pricing_runs
               WHERE quote_id = ?
               ORDER BY datetime(created_at) DESC, id DESC""",
            (int(quote_id),),
        ).fetchall()
        return [dict(r) for r in rows]


def get_quote_pricing_lines(pricing_run_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM quote_pricing_lines
               WHERE pricing_run_id = ?
               ORDER BY id ASC""",
            (int(pricing_run_id),),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d.get("meta_json") or "{}")
            result.append(d)
        return result


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
