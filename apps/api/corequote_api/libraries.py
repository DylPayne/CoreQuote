from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


class LibraryError(Exception):
    pass


class LibraryNotFound(LibraryError):
    pass


class LibraryConflict(LibraryError):
    pass


class LibraryValidationError(LibraryError):
    pass


@dataclass(frozen=True)
class ResourceConfig:
    table: str
    fields: tuple[str, ...]
    select_clause: str
    order_by: str


BOARD_CONFIG = ResourceConfig(
    table="board_types",
    fields=("brand", "material", "thickness", "length_mm", "width_mm", "costing_mode"),
    select_clause=(
        "id::text, brand, material, thickness, length_mm, width_mm, costing_mode, "
        "created_at, updated_at"
    ),
    order_by="brand ASC, material ASC, thickness ASC",
)

SLIDE_CONFIG = ResourceConfig(
    table="slides",
    fields=("brand", "model", "code", "length", "side_length", "side_clearance_total", "side_height_uplift"),
    select_clause=(
        "id::text, brand, model, code, length, side_length, "
        "side_clearance_total, side_height_uplift, created_at, updated_at"
    ),
    order_by="brand ASC, model ASC, length ASC, code ASC",
)

HINGE_CONFIG = ResourceConfig(
    table="hinges",
    fields=("brand", "model", "code", "opening_angle_deg"),
    select_clause="id::text, brand, model, code, opening_angle_deg, created_at, updated_at",
    order_by="brand ASC, model ASC, opening_angle_deg ASC, code ASC",
)

HANDLE_CONFIG = ResourceConfig(
    table="handles",
    fields=("name", "supplier", "code"),
    select_clause="id::text, name, supplier, code, created_at, updated_at",
    order_by="name ASC, supplier ASC, code ASC",
)

EXTRA_CATEGORY_CONFIG = ResourceConfig(
    table="extra_categories",
    fields=("name",),
    select_clause="id::text, name, created_at, updated_at",
    order_by="name ASC",
)

PRICE_LIST_CONFIG = ResourceConfig(
    table="price_lists",
    fields=("name", "status", "effective_from", "effective_to"),
    select_clause="id::text, name, status, effective_from, effective_to, created_at, updated_at",
    order_by="created_at DESC, id DESC",
)

PRICE_LIST_ITEM_CONFIG = ResourceConfig(
    table="price_list_items",
    fields=("item_type", "item_ref_id", "item_key", "price_component", "uom", "unit_price_cents", "effective_from"),
    select_clause=(
        "id::text, price_list_id::text, item_type, item_ref_id::text, "
        "item_key, price_component, uom, unit_price_cents, effective_from, effective_to, "
        "replaces_id::text, (effective_to IS NULL) AS is_active, created_at, updated_at"
    ),
    order_by="item_type ASC, item_key ASC, price_component ASC, effective_from DESC",
)

PRICE_ITEM_TYPE_TABLES: dict[str, str] = {
    "board": "board_types",
    "slide": "slides",
    "hinge": "hinges",
    "handle": "handles",
    "extra": "extras",
}

PRICING_SETTINGS_COLUMNS: tuple[str, ...] = (
    "vat_rate_bps",
    "default_markup_bps",
    "carcass_markup_bps",
    "door_panel_markup_bps",
    "component_markup_bps",
    "handle_markup_bps",
    "extras_markup_bps",
    "fabrication_markup_bps",
    "install_markup_bps",
    "delivery_markup_bps",
    "joinery_commission_bps",
    "labour_cents_per_m2",
    "consumables_cents_per_m2",
    "install_day_cost_cents",
    "delivery_base_cents",
    "install_units_per_day",
    "delivery_units_per_trip",
    "minimum_install_days_bps",
    "minimum_delivery_trips_bps",
)
PRICING_SETTINGS_SELECT = ", ".join(PRICING_SETTINGS_COLUMNS)


class LibraryStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def list_boards(self, company_id: str) -> list[dict]:
        return self._list(BOARD_CONFIG, company_id)

    def create_board(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(BOARD_CONFIG, company_id, payload)

    def get_board(self, company_id: str, item_id: str) -> dict:
        return self._get(BOARD_CONFIG, company_id, item_id)

    def update_board(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(BOARD_CONFIG, company_id, item_id, payload)

    def delete_board(self, company_id: str, item_id: str) -> None:
        self._delete(BOARD_CONFIG, company_id, item_id)

    def list_slides(self, company_id: str) -> list[dict]:
        return self._list(SLIDE_CONFIG, company_id)

    def create_slide(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(SLIDE_CONFIG, company_id, payload)

    def get_slide(self, company_id: str, item_id: str) -> dict:
        return self._get(SLIDE_CONFIG, company_id, item_id)

    def update_slide(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(SLIDE_CONFIG, company_id, item_id, payload)

    def delete_slide(self, company_id: str, item_id: str) -> None:
        self._delete(SLIDE_CONFIG, company_id, item_id)

    def list_hinges(self, company_id: str) -> list[dict]:
        return self._list(HINGE_CONFIG, company_id)

    def create_hinge(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(HINGE_CONFIG, company_id, payload)

    def get_hinge(self, company_id: str, item_id: str) -> dict:
        return self._get(HINGE_CONFIG, company_id, item_id)

    def update_hinge(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(HINGE_CONFIG, company_id, item_id, payload)

    def delete_hinge(self, company_id: str, item_id: str) -> None:
        self._delete(HINGE_CONFIG, company_id, item_id)

    def list_handles(self, company_id: str) -> list[dict]:
        return self._list(HANDLE_CONFIG, company_id)

    def create_handle(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(HANDLE_CONFIG, company_id, payload)

    def get_handle(self, company_id: str, item_id: str) -> dict:
        return self._get(HANDLE_CONFIG, company_id, item_id)

    def update_handle(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(HANDLE_CONFIG, company_id, item_id, payload)

    def delete_handle(self, company_id: str, item_id: str) -> None:
        self._delete(HANDLE_CONFIG, company_id, item_id)

    def list_extra_categories(self, company_id: str) -> list[dict]:
        return self._list(EXTRA_CATEGORY_CONFIG, company_id)

    def create_extra_category(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(EXTRA_CATEGORY_CONFIG, company_id, payload)

    def get_extra_category(self, company_id: str, item_id: str) -> dict:
        return self._get(EXTRA_CATEGORY_CONFIG, company_id, item_id)

    def update_extra_category(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(EXTRA_CATEGORY_CONFIG, company_id, item_id, payload)

    def delete_extra_category(self, company_id: str, item_id: str) -> None:
        self._delete(EXTRA_CATEGORY_CONFIG, company_id, item_id)

    def list_extras(self, company_id: str) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    e.id::text,
                    e.name,
                    e.category_id::text,
                    c.name AS category_name,
                    e.supplier,
                    e.code,
                    e.notes,
                    e.created_at,
                    e.updated_at
                FROM extras e
                JOIN extra_categories c ON c.id = e.category_id
                WHERE e.company_id = %s
                ORDER BY c.name ASC, e.name ASC, e.supplier ASC, e.code ASC
                """,
                (company_id,),
            ).fetchall()

    def create_extra(self, company_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_extra_category(company_id, payload["category_id"])
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO extras (company_id, name, category_id, supplier, code, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        _clean(payload["name"]),
                        payload["category_id"],
                        _clean(payload.get("supplier", "")),
                        _clean(payload.get("code", "")),
                        _clean(payload.get("notes", "")),
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        return self.get_extra(company_id, row["id"])

    def get_extra(self, company_id: str, item_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    e.id::text,
                    e.name,
                    e.category_id::text,
                    c.name AS category_name,
                    e.supplier,
                    e.code,
                    e.notes,
                    e.created_at,
                    e.updated_at
                FROM extras e
                JOIN extra_categories c ON c.id = e.category_id
                WHERE e.company_id = %s
                  AND e.id = %s
                """,
                (company_id, item_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def update_extra(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_extra_category(company_id, payload["category_id"])
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    UPDATE extras
                    SET name = %s,
                        category_id = %s,
                        supplier = %s,
                        code = %s,
                        notes = %s
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (
                        _clean(payload["name"]),
                        payload["category_id"],
                        _clean(payload.get("supplier", "")),
                        _clean(payload.get("code", "")),
                        _clean(payload.get("notes", "")),
                        company_id,
                        item_id,
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        if not row:
            raise LibraryNotFound("Library row not found")
        return self.get_extra(company_id, row["id"])

    def delete_extra(self, company_id: str, item_id: str) -> None:
        self._delete(ResourceConfig("extras", (), "", ""), company_id, item_id)

    def get_pricing_settings(self, company_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                INSERT INTO pricing_settings (company_id)
                VALUES (%s)
                ON CONFLICT (company_id) DO NOTHING
                RETURNING company_id::text, {PRICING_SETTINGS_SELECT}, created_at, updated_at
                """,
                (company_id,),
            ).fetchone()
            if row:
                return row
            return conn.execute(
                f"""
                SELECT company_id::text, {PRICING_SETTINGS_SELECT}, created_at, updated_at
                FROM pricing_settings
                WHERE company_id = %s
                """,
                (company_id,),
            ).fetchone()

    def update_pricing_settings(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        values = [data[column] for column in PRICING_SETTINGS_COLUMNS]
        assignments = ",\n                    ".join(f"{column} = EXCLUDED.{column}" for column in PRICING_SETTINGS_COLUMNS)
        placeholders = ", ".join(["%s"] * (len(PRICING_SETTINGS_COLUMNS) + 1))
        with self._connect() as conn:
            return conn.execute(
                f"""
                INSERT INTO pricing_settings (company_id, {PRICING_SETTINGS_SELECT})
                VALUES ({placeholders})
                ON CONFLICT (company_id) DO UPDATE
                SET {assignments}
                RETURNING company_id::text, {PRICING_SETTINGS_SELECT}, created_at, updated_at
                """,
                (company_id, *values),
            ).fetchone()

    def list_price_lists(self, company_id: str) -> list[dict]:
        return self._list(PRICE_LIST_CONFIG, company_id)

    def get_active_price_list(self, company_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {PRICE_LIST_CONFIG.select_clause}
                FROM price_lists
                WHERE company_id = %s
                  AND status = 'active'
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Active price list not found")
        return row

    def create_price_list(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(PRICE_LIST_CONFIG, company_id, payload)

    def get_price_list(self, company_id: str, price_list_id: str) -> dict:
        return self._get(PRICE_LIST_CONFIG, company_id, price_list_id)

    def update_price_list(self, company_id: str, price_list_id: str, payload: dict[str, Any]) -> dict:
        return self._update(PRICE_LIST_CONFIG, company_id, price_list_id, payload)

    def delete_price_list(self, company_id: str, price_list_id: str) -> None:
        self._delete(PRICE_LIST_CONFIG, company_id, price_list_id)

    def list_price_list_items(self, company_id: str, price_list_id: str, include_history: bool = False) -> list[dict]:
        self._ensure_price_list(company_id, price_list_id)
        history_filter = "" if include_history else "AND effective_to IS NULL"
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
                FROM price_list_items
                WHERE company_id = %s
                  AND price_list_id = %s
                  {history_filter}
                ORDER BY {PRICE_LIST_ITEM_CONFIG.order_by}
                """,
                (company_id, price_list_id),
            ).fetchall()

    def create_price_list_item(self, company_id: str, price_list_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        data = self._normalize_price_item_payload(company_id, payload)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO price_list_items
                        (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                         uom, unit_price_cents, effective_from)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        price_list_id,
                        data["item_type"],
                        data.get("item_ref_id"),
                        data["item_key"],
                        data["price_component"],
                        data["uom"],
                        data["unit_price_cents"],
                        data.get("effective_from"),
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Price list item already exists") from exc
        return self.get_price_list_item(company_id, price_list_id, row["id"])

    def get_price_list_item(self, company_id: str, price_list_id: str, item_id: str) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
                FROM price_list_items
                WHERE company_id = %s
                  AND price_list_id = %s
                  AND id = %s
                """,
                (company_id, price_list_id, item_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Price list item not found")
        return row

    def update_price_list_item(
        self,
        company_id: str,
        price_list_id: str,
        item_id: str,
        payload: dict[str, Any],
    ) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        data = self._normalize_price_item_payload(company_id, payload)
        try:
            with self._connect() as conn:
                old_row = conn.execute(
                    f"""
                    SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
                    FROM price_list_items
                    WHERE company_id = %s
                      AND price_list_id = %s
                      AND id = %s
                    FOR UPDATE
                    """,
                    (company_id, price_list_id, item_id),
                ).fetchone()
                if not old_row:
                    raise LibraryNotFound("Price list item not found")
                replacement_time = data.get("effective_from")
                row = conn.execute(
                    """
                    UPDATE price_list_items
                    SET effective_to = COALESCE(%s, now())
                    WHERE company_id = %s
                      AND price_list_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (
                        replacement_time,
                        company_id,
                        price_list_id,
                        item_id,
                    ),
                ).fetchone()
                new_row = conn.execute(
                    """
                    INSERT INTO price_list_items
                        (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                         uom, unit_price_cents, effective_from, replaces_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        price_list_id,
                        data["item_type"],
                        data.get("item_ref_id"),
                        data["item_key"],
                        data["price_component"],
                        data["uom"],
                        data["unit_price_cents"],
                        replacement_time,
                        row["id"],
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Active price list item already exists") from exc
        return self.get_price_list_item(company_id, price_list_id, new_row["id"])

    def upsert_price_list_item(self, company_id: str, price_list_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        data = self._normalize_price_item_payload(company_id, payload)

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id::text
                FROM price_list_items
                WHERE company_id = %s
                  AND price_list_id = %s
                  AND item_type = %s
                  AND item_key = %s
                  AND price_component = %s
                  AND effective_to IS NULL
                ORDER BY effective_from DESC
                LIMIT 1
                """,
                (
                    company_id,
                    price_list_id,
                    data["item_type"],
                    data["item_key"],
                    data["price_component"],
                ),
            ).fetchone()

        if existing:
            return self.update_price_list_item(company_id, price_list_id, existing["id"], data)
        return self.create_price_list_item(company_id, price_list_id, data)

    def delete_price_list_item(self, company_id: str, price_list_id: str, item_id: str) -> None:
        self._ensure_price_list(company_id, price_list_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE price_list_items
                SET effective_to = now()
                WHERE company_id = %s
                  AND price_list_id = %s
                  AND id = %s
                  AND effective_to IS NULL
                RETURNING id::text
                """,
                (company_id, price_list_id, item_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Price list item not found")

    def _list(self, config: ResourceConfig, company_id: str) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {config.select_clause}
                FROM {config.table}
                WHERE company_id = %s
                ORDER BY {config.order_by}
                """,
                (company_id,),
            ).fetchall()

    def _create(self, config: ResourceConfig, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        columns = ("company_id", *config.fields)
        placeholders = ", ".join(["%s"] * len(columns))
        values = [company_id, *[data[field] for field in config.fields]]
        try:
            with self._connect() as conn:
                row = conn.execute(
                    f"""
                    INSERT INTO {config.table} ({", ".join(columns)})
                    VALUES ({placeholders})
                    RETURNING {config.select_clause}
                    """,
                    values,
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        return row

    def _get(self, config: ResourceConfig, company_id: str, item_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {config.select_clause}
                FROM {config.table}
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, item_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def _update(self, config: ResourceConfig, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        assignments = ", ".join([f"{field} = %s" for field in config.fields])
        values = [*[data[field] for field in config.fields], company_id, item_id]
        try:
            with self._connect() as conn:
                row = conn.execute(
                    f"""
                    UPDATE {config.table}
                    SET {assignments}
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING {config.select_clause}
                    """,
                    values,
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def _delete(self, config: ResourceConfig, company_id: str, item_id: str) -> None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    f"""
                    DELETE FROM {config.table}
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (company_id, item_id),
                ).fetchone()
        except psycopg.errors.ForeignKeyViolation as exc:
            raise LibraryConflict("Library row is still in use") from exc
        if not row:
            raise LibraryNotFound("Library row not found")

    def _ensure_extra_category(self, company_id: str, category_id: str) -> None:
        self._get(EXTRA_CATEGORY_CONFIG, company_id, category_id)

    def _ensure_price_list(self, company_id: str, price_list_id: str) -> None:
        self._get(PRICE_LIST_CONFIG, company_id, price_list_id)

    def _normalize_price_item_payload(self, company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = _clean_payload(payload)
        item_type = str(data.get("item_type") or "").strip().lower()
        item_ref_id = str(data.get("item_ref_id") or "").strip()
        item_key = str(data.get("item_key") or "").strip()

        if item_ref_id:
            self._ensure_price_item_reference(company_id, item_type, item_ref_id)
            data["item_ref_id"] = item_ref_id
            data["item_key"] = f"{item_type}::{item_ref_id}"
            return data

        if not item_key:
            raise LibraryValidationError("Either item_ref_id or item_key is required")

        data["item_key"] = item_key
        derived_ref = _try_extract_ref_id(item_type, item_key)
        if derived_ref:
            self._ensure_price_item_reference(company_id, item_type, derived_ref)
            data["item_ref_id"] = derived_ref

        return data

    def _ensure_price_item_reference(self, company_id: str, item_type: str, item_ref_id: str) -> None:
        table = PRICE_ITEM_TYPE_TABLES.get(item_type)
        if not table:
            raise LibraryValidationError(f"Unsupported item_type: {item_type}")

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT id::text
                FROM {table}
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, item_ref_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Library row not found")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for library database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = {key: _clean(value) for key, value in payload.items()}
    if "costing_mode" in data:
        data["costing_mode"] = str(data["costing_mode"] or "sheet").strip().lower()
    if "price_component" in data:
        data["price_component"] = str(data["price_component"] or "unit").strip().lower()
    if data.get("item_ref_id") == "":
        data["item_ref_id"] = None
    return data


def _try_extract_ref_id(item_type: str, item_key: str) -> str | None:
    prefix = f"{item_type}::"
    if not item_key.startswith(prefix):
        return None
    raw_ref = item_key[len(prefix) :].strip()
    if not raw_ref or "::" in raw_ref:
        return None
    return raw_ref
