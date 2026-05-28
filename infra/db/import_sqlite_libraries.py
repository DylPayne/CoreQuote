from __future__ import annotations

import argparse
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = REPO_ROOT / "data" / "corequote.db"


@dataclass(frozen=True)
class ImportCounts:
    boards: int = 0
    slides: int = 0
    hinges: int = 0
    handles: int = 0
    extra_categories: int = 0
    extras: int = 0
    price_lists: int = 0
    price_list_items: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "boards": self.boards,
            "slides": self.slides,
            "hinges": self.hinges,
            "handles": self.handles,
            "extra_categories": self.extra_categories,
            "extras": self.extras,
            "price_lists": self.price_lists,
            "price_list_items": self.price_list_items,
        }


def import_sqlite_libraries(
    *,
    company_id: str,
    sqlite_path: str | Path = DEFAULT_SQLITE_PATH,
    database_url: str | None = None,
) -> ImportCounts:
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required to import SQLite libraries")

    sqlite_rows = load_sqlite_libraries(sqlite_path)
    with psycopg.connect(url, row_factory=dict_row) as pg_conn:
        with pg_conn.transaction():
            _ensure_company(pg_conn, company_id)
            id_map = _import_catalog(pg_conn, company_id, sqlite_rows)
            return _import_pricing(pg_conn, company_id, sqlite_rows, id_map)


def load_sqlite_libraries(sqlite_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    path = Path(sqlite_path)
    if not path.exists():
        raise RuntimeError(f"SQLite database not found: {path}")

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return {
            "board_types": _rows(conn, "board_types"),
            "slides": _rows(conn, "slides"),
            "hinges": _rows(conn, "hinges"),
            "handles": _rows(conn, "handles"),
            "extra_categories": _rows(conn, "extra_categories"),
            "extras": _rows(conn, "extras"),
            "price_lists": _rows(conn, "price_lists"),
            "price_list_items": _rows(conn, "price_list_items"),
        }


def remap_price_item(row: dict[str, Any], id_map: dict[str, dict[int, str]]) -> dict[str, Any]:
    item_type = str(row["item_type"]).strip()
    item_key = str(row["item_key"]).strip()
    item_ref_id = row.get("item_ref_id")

    if item_type == "board":
        match = re.fullmatch(r"board::(\d+)::(.+)", item_key)
        if match:
            old_id = int(match.group(1))
            mapped_id = id_map.get("board_types", {}).get(old_id)
            if mapped_id:
                item_ref_id = mapped_id
                item_key = f"board::{mapped_id}"
                price_component = match.group(2)
            else:
                price_component = "unit"
        else:
            price_component = "unit"
    elif item_type == "extra":
        match = re.fullmatch(r"extra::(\d+)", item_key)
        if match:
            old_id = int(match.group(1))
            mapped_id = id_map.get("extras", {}).get(old_id)
            if mapped_id:
                item_ref_id = mapped_id
                item_key = f"extra::{mapped_id}"
        price_component = "unit"
    elif item_type == "slide":
        item_ref_id = _mapped_natural_item_ref(row, id_map, "slides")
        price_component = "unit"
    elif item_type == "hinge":
        item_ref_id = _mapped_natural_item_ref(row, id_map, "hinges")
        price_component = "unit"
    elif item_type == "handle":
        item_ref_id = _mapped_natural_item_ref(row, id_map, "handles")
        price_component = "unit"
    else:
        price_component = "unit"

    return {
        "item_type": item_type,
        "item_ref_id": _normalize_ref(item_ref_id),
        "item_key": item_key,
        "price_component": str(row.get("price_component") or price_component).strip().lower(),
        "uom": str(row["uom"]).strip(),
        "unit_price_cents": int(row["unit_price_cents"]),
    }


def _rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]


def _ensure_company(conn, company_id: str) -> None:
    row = conn.execute("SELECT id FROM companies WHERE id = %s", (company_id,)).fetchone()
    if not row:
        raise RuntimeError(f"Company does not exist: {company_id}")


def _import_catalog(conn, company_id: str, rows: dict[str, list[dict[str, Any]]]) -> dict[str, dict[int, str]]:
    id_map: dict[str, dict[int, str]] = {
        "board_types": {},
        "slides": {},
        "hinges": {},
        "handles": {},
        "extra_categories": {},
        "extras": {},
    }

    for row in rows["board_types"]:
        new_id = conn.execute(
            """
            INSERT INTO board_types (company_id, brand, material, thickness, length_mm, width_mm, costing_mode)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, brand, material, thickness, length_mm, width_mm)
            DO UPDATE SET costing_mode = EXCLUDED.costing_mode
            RETURNING id::text
            """,
            (
                company_id,
                _clean(row["brand"]),
                _clean(row["material"]),
                int(row["thickness"]),
                int(row["length_mm"]),
                int(row["width_mm"]),
                _clean(row.get("costing_mode") or "sheet").lower(),
            ),
        ).fetchone()["id"]
        id_map["board_types"][int(row["id"])] = new_id

    for row in rows["slides"]:
        new_id = conn.execute(
            """
            INSERT INTO slides
                (company_id, brand, model, code, length, side_length, side_clearance_total, side_height_uplift)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, brand, model, code)
            DO UPDATE SET
                length = EXCLUDED.length,
                side_length = EXCLUDED.side_length,
                side_clearance_total = EXCLUDED.side_clearance_total,
                side_height_uplift = EXCLUDED.side_height_uplift
            RETURNING id::text
            """,
            (
                company_id,
                _clean(row["brand"]),
                _clean(row["model"]),
                _clean(row.get("code", "")),
                int(row["length"]),
                int(row["side_length"]),
                int(row["side_clearance_total"]),
                int(row.get("side_height_uplift") or 0),
            ),
        ).fetchone()["id"]
        id_map["slides"][int(row["id"])] = new_id

    for row in rows["hinges"]:
        new_id = conn.execute(
            """
            INSERT INTO hinges (company_id, brand, model, code, opening_angle_deg)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_id, brand, model, code)
            DO UPDATE SET opening_angle_deg = EXCLUDED.opening_angle_deg
            RETURNING id::text
            """,
            (
                company_id,
                _clean(row["brand"]),
                _clean(row["model"]),
                _clean(row.get("code", "")),
                int(row["opening_angle_deg"]),
            ),
        ).fetchone()["id"]
        id_map["hinges"][int(row["id"])] = new_id

    for row in rows["handles"]:
        new_id = conn.execute(
            """
            INSERT INTO handles (company_id, name, supplier, code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (company_id, name, supplier, code)
            DO UPDATE SET name = EXCLUDED.name
            RETURNING id::text
            """,
            (company_id, _clean(row["name"]), _clean(row.get("supplier", "")), _clean(row.get("code", ""))),
        ).fetchone()["id"]
        id_map["handles"][int(row["id"])] = new_id

    for row in rows["extra_categories"]:
        new_id = conn.execute(
            """
            INSERT INTO extra_categories (company_id, name)
            VALUES (%s, %s)
            ON CONFLICT (company_id, name)
            DO UPDATE SET name = EXCLUDED.name
            RETURNING id::text
            """,
            (company_id, _clean(row["name"])),
        ).fetchone()["id"]
        id_map["extra_categories"][int(row["id"])] = new_id

    for row in rows["extras"]:
        category_id = id_map["extra_categories"][int(row["category_id"])]
        new_id = conn.execute(
            """
            INSERT INTO extras (company_id, name, category_id, supplier, code, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id, name, category_id, supplier, code)
            DO UPDATE SET notes = EXCLUDED.notes
            RETURNING id::text
            """,
            (
                company_id,
                _clean(row["name"]),
                category_id,
                _clean(row.get("supplier", "")),
                _clean(row.get("code", "")),
                _clean(row.get("notes", "")),
            ),
        ).fetchone()["id"]
        id_map["extras"][int(row["id"])] = new_id

    return id_map


def _import_pricing(
    conn,
    company_id: str,
    rows: dict[str, list[dict[str, Any]]],
    id_map: dict[str, dict[int, str]],
) -> ImportCounts:
    price_list_map: dict[int, str] = {}

    for row in rows["price_lists"]:
        new_id = _upsert_price_list(conn, company_id, row)
        price_list_map[int(row["id"])] = new_id

    for row in rows["price_list_items"]:
        price_list_id = price_list_map[int(row["price_list_id"])]
        item = remap_price_item(row, id_map)
        conn.execute(
            """
            INSERT INTO price_list_items
                (company_id, price_list_id, item_type, item_ref_id, item_key, price_component, uom, unit_price_cents)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (price_list_id, item_type, item_key, price_component)
            WHERE effective_to IS NULL
            DO UPDATE SET
                item_ref_id = EXCLUDED.item_ref_id,
                uom = EXCLUDED.uom,
                unit_price_cents = EXCLUDED.unit_price_cents
            """,
            (
                company_id,
                price_list_id,
                item["item_type"],
                item["item_ref_id"],
                item["item_key"],
                item["price_component"],
                item["uom"],
                item["unit_price_cents"],
            ),
        )

    return ImportCounts(
        boards=len(rows["board_types"]),
        slides=len(rows["slides"]),
        hinges=len(rows["hinges"]),
        handles=len(rows["handles"]),
        extra_categories=len(rows["extra_categories"]),
        extras=len(rows["extras"]),
        price_lists=len(rows["price_lists"]),
        price_list_items=len(rows["price_list_items"]),
    )


def _upsert_price_list(conn, company_id: str, row: dict[str, Any]) -> str:
    existing = conn.execute(
        """
        SELECT id::text
        FROM price_lists
        WHERE company_id = %s
          AND name = %s
          AND status = %s
          AND effective_from IS NOT DISTINCT FROM %s
          AND effective_to IS NOT DISTINCT FROM %s
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (
            company_id,
            _clean(row["name"]),
            _clean(row.get("status") or "draft"),
            row.get("effective_from") or None,
            row.get("effective_to") or None,
        ),
    ).fetchone()
    if existing:
        return existing["id"]

    return conn.execute(
        """
        INSERT INTO price_lists (company_id, name, status, effective_from, effective_to)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id::text
        """,
        (
            company_id,
            _clean(row["name"]),
            _clean(row.get("status") or "draft"),
            row.get("effective_from") or None,
            row.get("effective_to") or None,
        ),
    ).fetchone()["id"]


def _mapped_natural_item_ref(row: dict[str, Any], id_map: dict[str, dict[int, str]], table: str) -> str | None:
    ref = _normalize_ref(row.get("item_ref_id"))
    if ref is None:
        return None
    try:
        return id_map.get(table, {}).get(int(ref))
    except (TypeError, ValueError):
        return ref


def _normalize_ref(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CoreQuote SQLite library data into company-scoped Postgres tables.")
    parser.add_argument("--company-id", required=True, help="Target company UUID that will own the imported library rows.")
    parser.add_argument("--sqlite-path", default=str(DEFAULT_SQLITE_PATH), help="Path to the legacy SQLite database.")
    parser.add_argument("--database-url", default=None, help="Postgres DATABASE_URL. Defaults to the environment variable.")
    args = parser.parse_args()

    counts = import_sqlite_libraries(
        company_id=args.company_id,
        sqlite_path=args.sqlite_path,
        database_url=args.database_url,
    )
    for name, count in counts.as_dict().items():
        print(f"Imported {count} {name}")


if __name__ == "__main__":
    main()
