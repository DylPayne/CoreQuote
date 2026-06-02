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
        "item_key, price_component, uom, unit_price_cents, source_supplier_item_cost_id::text, "
        "cost_source, effective_from, effective_to, "
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

BRAND_TABLES = {"board_types", "slides", "hinges"}

SUPPLIER_CONFIG = ResourceConfig(
    table="suppliers",
    fields=("name", "code", "contact_name", "email", "phone", "notes"),
    select_clause="id::text, name, code, contact_name, email, phone, notes, created_at, updated_at",
    order_by="name ASC, code ASC",
)

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

    def list_suppliers(self, company_id: str) -> list[dict]:
        return self._list(SUPPLIER_CONFIG, company_id)

    def create_supplier(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(SUPPLIER_CONFIG, company_id, payload)

    def get_supplier(self, company_id: str, supplier_id: str) -> dict:
        return self._get(SUPPLIER_CONFIG, company_id, supplier_id)

    def update_supplier(self, company_id: str, supplier_id: str, payload: dict[str, Any]) -> dict:
        return self._update(SUPPLIER_CONFIG, company_id, supplier_id, payload)

    def delete_supplier(self, company_id: str, supplier_id: str) -> None:
        self._delete(SUPPLIER_CONFIG, company_id, supplier_id)

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

    def list_item_suppliers(
        self,
        company_id: str,
        item_type: str | None = None,
        item_ref_id: str | None = None,
    ) -> list[dict]:
        filters = ["item.company_id = %s"]
        values: list[Any] = [company_id]
        if item_type:
            filters.append("item.item_type = %s")
            values.append(item_type)
        if item_ref_id:
            filters.append("item.item_ref_id = %s")
            values.append(item_ref_id)
        where_clause = " AND ".join(filters)
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    item.id::text,
                    item.item_type,
                    item.item_ref_id::text,
                    item.supplier_id::text,
                    supplier.name AS supplier_name,
                    item.supplier_sku,
                    item.supplier_description,
                    item.price_component,
                    item.order_uom,
                    item.is_preferred,
                    item.notes,
                    cost.id::text AS active_supplier_item_cost_id,
                    cost.list_price_cents AS active_list_price_cents,
                    cost.discount_bps AS active_discount_bps,
                    cost.unit_cost_cents AS active_unit_cost_cents,
                    cost.currency_code AS active_currency_code,
                    item.created_at,
                    item.updated_at
                FROM item_suppliers item
                JOIN suppliers supplier
                  ON supplier.company_id = item.company_id
                 AND supplier.id = item.supplier_id
                LEFT JOIN supplier_item_costs cost
                  ON cost.company_id = item.company_id
                 AND cost.item_supplier_id = item.id
                 AND cost.effective_to IS NULL
                WHERE {where_clause}
                ORDER BY item.item_type ASC, supplier.name ASC, item.supplier_sku ASC, item.id ASC
                """,
                values,
            ).fetchall()

    def create_item_supplier(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = self._normalize_item_supplier_payload(company_id, payload)
        try:
            with self._connect() as conn:
                if data["is_preferred"]:
                    self._clear_preferred_item_supplier(conn, company_id, data)
                row = conn.execute(
                    """
                    INSERT INTO item_suppliers
                        (company_id, item_type, item_ref_id, supplier_id, supplier_sku, supplier_description,
                         price_component, order_uom, is_preferred, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        data["item_type"],
                        data["item_ref_id"],
                        data["supplier_id"],
                        data["supplier_sku"],
                        data["supplier_description"],
                        data["price_component"],
                        data["order_uom"],
                        data["is_preferred"],
                        data["notes"],
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Item supplier already exists") from exc
        return self.get_item_supplier(company_id, row["id"])

    def get_item_supplier(self, company_id: str, item_supplier_id: str) -> dict:
        rows = self.list_item_suppliers(company_id)
        for row in rows:
            if row["id"] == item_supplier_id:
                return row
        raise LibraryNotFound("Item supplier not found")

    def update_item_supplier(self, company_id: str, item_supplier_id: str, payload: dict[str, Any]) -> dict:
        data = self._normalize_item_supplier_payload(company_id, payload)
        try:
            with self._connect() as conn:
                if data["is_preferred"]:
                    self._clear_preferred_item_supplier(conn, company_id, data, exclude_id=item_supplier_id)
                row = conn.execute(
                    """
                    UPDATE item_suppliers
                    SET item_type = %s,
                        item_ref_id = %s,
                        supplier_id = %s,
                        supplier_sku = %s,
                        supplier_description = %s,
                        price_component = %s,
                        order_uom = %s,
                        is_preferred = %s,
                        notes = %s
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (
                        data["item_type"],
                        data["item_ref_id"],
                        data["supplier_id"],
                        data["supplier_sku"],
                        data["supplier_description"],
                        data["price_component"],
                        data["order_uom"],
                        data["is_preferred"],
                        data["notes"],
                        company_id,
                        item_supplier_id,
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Item supplier already exists") from exc
        if not row:
            raise LibraryNotFound("Item supplier not found")
        return self.get_item_supplier(company_id, row["id"])

    def delete_item_supplier(self, company_id: str, item_supplier_id: str) -> None:
        self._delete(ResourceConfig("item_suppliers", (), "", ""), company_id, item_supplier_id)

    def list_supplier_item_costs(
        self,
        company_id: str,
        item_supplier_id: str,
        include_history: bool = False,
    ) -> list[dict]:
        self._ensure_item_supplier(company_id, item_supplier_id)
        history_filter = "" if include_history else "AND effective_to IS NULL"
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    id::text,
                    item_supplier_id::text,
                    list_price_cents,
                    discount_bps,
                    unit_cost_cents,
                    currency_code,
                    source,
                    source_ref,
                    effective_from,
                    effective_to,
                    replaces_id::text,
                    (effective_to IS NULL) AS is_active,
                    created_at,
                    updated_at
                FROM supplier_item_costs
                WHERE company_id = %s
                  AND item_supplier_id = %s
                  {history_filter}
                ORDER BY effective_from DESC, id DESC
                """,
                (company_id, item_supplier_id),
            ).fetchall()

    def create_supplier_item_cost(self, company_id: str, item_supplier_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_item_supplier(company_id, item_supplier_id)
        data = _clean_payload(payload)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO supplier_item_costs
                        (company_id, item_supplier_id, list_price_cents, discount_bps, unit_cost_cents,
                         currency_code, source, source_ref, effective_from)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        item_supplier_id,
                        data.get("list_price_cents", 0),
                        data.get("discount_bps", 0),
                        data["unit_cost_cents"],
                        data.get("currency_code", "ZAR"),
                        data.get("source", "manual"),
                        data.get("source_ref", ""),
                        data.get("effective_from"),
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Active supplier cost already exists") from exc
        return self.get_supplier_item_cost(company_id, item_supplier_id, row["id"])

    def upsert_supplier_item_cost(self, company_id: str, item_supplier_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_item_supplier(company_id, item_supplier_id)
        data = _clean_payload(payload)
        replacement_time = data.get("effective_from")
        with self._connect() as conn:
            old_row = conn.execute(
                """
                SELECT
                    id::text,
                    list_price_cents,
                    discount_bps,
                    unit_cost_cents,
                    currency_code,
                    source,
                    source_ref
                FROM supplier_item_costs
                WHERE company_id = %s
                  AND item_supplier_id = %s
                  AND effective_to IS NULL
                FOR UPDATE
                """,
                (company_id, item_supplier_id),
            ).fetchone()
            if old_row and _supplier_cost_matches(old_row, data):
                return self.get_supplier_item_cost(company_id, item_supplier_id, old_row["id"])

            replaces_id = None
            if old_row:
                old = conn.execute(
                    """
                    UPDATE supplier_item_costs
                    SET effective_to = COALESCE(%s, now())
                    WHERE company_id = %s
                      AND item_supplier_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (replacement_time, company_id, item_supplier_id, old_row["id"]),
                ).fetchone()
                replaces_id = old["id"]

            row = conn.execute(
                """
                INSERT INTO supplier_item_costs
                    (company_id, item_supplier_id, list_price_cents, discount_bps, unit_cost_cents,
                     currency_code, source, source_ref, effective_from, replaces_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s)
                RETURNING id::text
                """,
                (
                    company_id,
                    item_supplier_id,
                    data.get("list_price_cents", 0),
                    data.get("discount_bps", 0),
                    data["unit_cost_cents"],
                    data.get("currency_code", "ZAR"),
                    data.get("source", "manual"),
                    data.get("source_ref", ""),
                    replacement_time,
                    replaces_id,
                ),
            ).fetchone()
        return self.get_supplier_item_cost(company_id, item_supplier_id, row["id"])

    def get_supplier_item_cost(self, company_id: str, item_supplier_id: str, cost_id: str) -> dict:
        self._ensure_item_supplier(company_id, item_supplier_id)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id::text,
                    item_supplier_id::text,
                    list_price_cents,
                    discount_bps,
                    unit_cost_cents,
                    currency_code,
                    source,
                    source_ref,
                    effective_from,
                    effective_to,
                    replaces_id::text,
                    (effective_to IS NULL) AS is_active,
                    created_at,
                    updated_at
                FROM supplier_item_costs
                WHERE company_id = %s
                  AND item_supplier_id = %s
                  AND id = %s
                """,
                (company_id, item_supplier_id, cost_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Supplier cost not found")
        return row

    def generate_price_list_from_supplier_costs(
        self,
        company_id: str,
        price_list_id: str,
        payload: dict[str, Any],
    ) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        selection_mode = str(payload.get("selection_mode") or "preferred_then_cheapest").strip().lower()
        item_types = [str(item).strip().lower() for item in payload.get("item_types") or [] if str(item).strip()]
        preserve_manual_overrides = bool(payload.get("preserve_manual_overrides", True))
        if selection_mode not in {"preferred_then_cheapest", "preferred_only", "cheapest"}:
            raise LibraryValidationError("Unsupported supplier cost selection mode")
        unsupported_types = [item_type for item_type in item_types if item_type not in PRICE_ITEM_TYPE_TABLES]
        if unsupported_types:
            raise LibraryValidationError(f"Unsupported item_types: {', '.join(unsupported_types)}")

        with self._connect() as conn:
            item_rows = self._fetch_supplier_generation_rows(conn, company_id, item_types)
            selected_rows, missing_price_count = _select_supplier_generation_rows(item_rows, selection_mode)

            created_count = 0
            updated_count = 0
            unchanged_count = 0
            skipped_override_count = 0

            for selected in selected_rows:
                item_key = f"{selected['item_type']}::{selected['item_ref_id']}"
                current = conn.execute(
                    """
                    SELECT id::text, unit_price_cents, uom, source_supplier_item_cost_id::text, cost_source
                    FROM price_list_items
                    WHERE company_id = %s
                      AND price_list_id = %s
                      AND item_type = %s
                      AND item_key = %s
                      AND price_component = %s
                      AND effective_to IS NULL
                    ORDER BY effective_from DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (
                        company_id,
                        price_list_id,
                        selected["item_type"],
                        item_key,
                        selected["price_component"],
                    ),
                ).fetchone()

                if current and preserve_manual_overrides and current["cost_source"] != "supplier":
                    skipped_override_count += 1
                    continue

                source_cost_id = selected["supplier_item_cost_id"]
                unit_cost_cents = int(selected["unit_cost_cents"])
                uom = selected["order_uom"]
                if current and _generated_price_item_matches(current, source_cost_id, unit_cost_cents, uom):
                    unchanged_count += 1
                    continue

                if current:
                    conn.execute(
                        """
                        UPDATE price_list_items
                        SET effective_to = now()
                        WHERE company_id = %s
                          AND price_list_id = %s
                          AND id = %s
                        """,
                        (company_id, price_list_id, current["id"]),
                    )
                    updated_count += 1
                else:
                    created_count += 1

                conn.execute(
                    """
                    INSERT INTO price_list_items
                        (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                         uom, unit_price_cents, source_supplier_item_cost_id, cost_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'supplier')
                    """,
                    (
                        company_id,
                        price_list_id,
                        selected["item_type"],
                        selected["item_ref_id"],
                        item_key,
                        selected["price_component"],
                        uom,
                        unit_cost_cents,
                        source_cost_id,
                    ),
                )

        return {
            "price_list_id": price_list_id,
            "selection_mode": selection_mode,
            "generated_count": len(selected_rows),
            "created_count": created_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "skipped_override_count": skipped_override_count,
            "missing_price_count": missing_price_count,
        }

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
                         uom, unit_price_cents, source_supplier_item_cost_id, cost_source, effective_from)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()))
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
                        data.get("source_supplier_item_cost_id"),
                        data["cost_source"],
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
                         uom, unit_price_cents, source_supplier_item_cost_id, cost_source, effective_from, replaces_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s)
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
                        data.get("source_supplier_item_cost_id"),
                        data["cost_source"],
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
        values = [company_id, *[data[field] for field in config.fields]]
        if config.table in BRAND_TABLES:
            columns = (*columns, "brand_id")
            values.append(self._get_or_create_brand(company_id, data["brand"]))
        placeholders = ", ".join(["%s"] * len(columns))
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
        if config.table in BRAND_TABLES:
            assignments = f"{assignments}, brand_id = %s"
            values = [*[data[field] for field in config.fields], self._get_or_create_brand(company_id, data["brand"]), company_id, item_id]
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

    def _ensure_supplier(self, company_id: str, supplier_id: str) -> None:
        self._get(SUPPLIER_CONFIG, company_id, supplier_id)

    def _ensure_item_supplier(self, company_id: str, item_supplier_id: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id::text
                FROM item_suppliers
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, item_supplier_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Item supplier not found")

    def _ensure_supplier_item_cost(self, company_id: str, cost_id: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id::text
                FROM supplier_item_costs
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, cost_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Supplier cost not found")

    def _normalize_item_supplier_payload(self, company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = _clean_payload(payload)
        item_type = str(data.get("item_type") or "").strip().lower()
        if item_type not in PRICE_ITEM_TYPE_TABLES:
            raise LibraryValidationError(f"Unsupported item_type: {item_type}")
        data["item_type"] = item_type
        data["price_component"] = str(data.get("price_component") or "unit").strip().lower()
        data["order_uom"] = str(data.get("order_uom") or "pcs").strip().lower()
        data["supplier_sku"] = str(data.get("supplier_sku") or "").strip()
        data["supplier_description"] = str(data.get("supplier_description") or "").strip()
        data["notes"] = str(data.get("notes") or "").strip()
        data["is_preferred"] = bool(data.get("is_preferred", False))
        self._ensure_price_item_reference(company_id, item_type, data["item_ref_id"])
        self._ensure_supplier(company_id, data["supplier_id"])
        return data

    def _clear_preferred_item_supplier(
        self,
        conn,
        company_id: str,
        data: dict[str, Any],
        exclude_id: str | None = None,
    ) -> None:
        exclude_filter = ""
        values: list[Any] = [
            company_id,
            data["item_type"],
            data["item_ref_id"],
            data["price_component"],
        ]
        if exclude_id:
            exclude_filter = "AND id <> %s"
            values.append(exclude_id)
        conn.execute(
            f"""
            UPDATE item_suppliers
            SET is_preferred = false
            WHERE company_id = %s
              AND item_type = %s
              AND item_ref_id = %s
              AND price_component = %s
              {exclude_filter}
            """,
            values,
        )

    def _fetch_supplier_generation_rows(self, conn, company_id: str, item_types: list[str]) -> list[dict]:
        filters = ["item.company_id = %s"]
        values: list[Any] = [company_id]
        if item_types:
            filters.append("item.item_type = ANY(%s)")
            values.append(item_types)
        where_clause = " AND ".join(filters)
        return conn.execute(
            f"""
            SELECT
                item.item_type,
                item.item_ref_id::text,
                item.price_component,
                item.order_uom,
                item.is_preferred,
                cost.id::text AS supplier_item_cost_id,
                cost.unit_cost_cents
            FROM item_suppliers item
            LEFT JOIN supplier_item_costs cost
              ON cost.company_id = item.company_id
             AND cost.item_supplier_id = item.id
             AND cost.effective_to IS NULL
            WHERE {where_clause}
            ORDER BY item.item_type ASC, item.item_ref_id ASC, item.price_component ASC, item.is_preferred DESC
            """,
            values,
        ).fetchall()

    def _normalize_price_item_payload(self, company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = _clean_payload(payload)
        item_type = str(data.get("item_type") or "").strip().lower()
        item_ref_id = str(data.get("item_ref_id") or "").strip()
        item_key = str(data.get("item_key") or "").strip()
        source_supplier_item_cost_id = str(data.get("source_supplier_item_cost_id") or "").strip()
        data["cost_source"] = str(data.get("cost_source") or "manual").strip().lower()
        data["source_supplier_item_cost_id"] = source_supplier_item_cost_id or None
        if data["source_supplier_item_cost_id"]:
            self._ensure_supplier_item_cost(company_id, data["source_supplier_item_cost_id"])

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

    def _get_or_create_brand(self, company_id: str, name: str) -> str:
        clean_name = _clean(name)
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO brands (company_id, name)
                VALUES (%s, %s)
                ON CONFLICT (company_id, name) DO UPDATE
                SET name = EXCLUDED.name
                RETURNING id::text
                """,
                (company_id, clean_name),
            ).fetchone()
        return row["id"]


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
    if "cost_source" in data:
        data["cost_source"] = str(data["cost_source"] or "manual").strip().lower()
    if "currency_code" in data:
        data["currency_code"] = str(data["currency_code"] or "ZAR").strip().upper()
    if data.get("item_ref_id") == "":
        data["item_ref_id"] = None
    if data.get("source_supplier_item_cost_id") == "":
        data["source_supplier_item_cost_id"] = None
    return data


def _try_extract_ref_id(item_type: str, item_key: str) -> str | None:
    prefix = f"{item_type}::"
    if not item_key.startswith(prefix):
        return None
    raw_ref = item_key[len(prefix) :].strip()
    if not raw_ref or "::" in raw_ref:
        return None
    return raw_ref


def _supplier_cost_matches(row: dict[str, Any], data: dict[str, Any]) -> bool:
    return (
        int(row["list_price_cents"]) == int(data.get("list_price_cents", 0))
        and int(row["discount_bps"]) == int(data.get("discount_bps", 0))
        and int(row["unit_cost_cents"]) == int(data["unit_cost_cents"])
        and str(row["currency_code"]) == str(data.get("currency_code", "ZAR"))
        and str(row["source"]) == str(data.get("source", "manual"))
        and str(row["source_ref"]) == str(data.get("source_ref", ""))
    )


def _select_supplier_generation_rows(rows: list[dict], selection_mode: str) -> tuple[list[dict], int]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        key = (row["item_type"], row["item_ref_id"], row["price_component"])
        grouped.setdefault(key, []).append(row)

    selected_rows: list[dict] = []
    missing_price_count = 0
    for group_rows in grouped.values():
        active_rows = [row for row in group_rows if row.get("supplier_item_cost_id")]
        if not active_rows:
            missing_price_count += 1
            continue
        preferred_rows = [row for row in active_rows if row["is_preferred"]]
        if selection_mode == "preferred_only":
            if not preferred_rows:
                missing_price_count += 1
                continue
            candidates = preferred_rows
        elif selection_mode == "cheapest":
            candidates = active_rows
        else:
            candidates = preferred_rows or active_rows
        selected_rows.append(min(candidates, key=lambda row: int(row["unit_cost_cents"])))

    return selected_rows, missing_price_count


def _generated_price_item_matches(
    row: dict[str, Any],
    source_supplier_item_cost_id: str,
    unit_cost_cents: int,
    uom: str,
) -> bool:
    return (
        row["cost_source"] == "supplier"
        and row.get("source_supplier_item_cost_id") == source_supplier_item_cost_id
        and int(row["unit_price_cents"]) == int(unit_cost_cents)
        and row["uom"] == uom
    )
