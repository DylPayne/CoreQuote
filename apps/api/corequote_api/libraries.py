from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from corequote_core.channel_handles import PROFILE_HANDLE_ID_KEYS

from corequote_api.library_imports import build_import_preview, build_reference_maps
from corequote_api.pricing_fields import (
    PricingFieldValidationError,
    normalize_order_uom,
    normalize_price_component,
    pricing_issues_as_fastapi_errors,
    validate_pricing_combination,
)


class LibraryError(Exception):
    pass


class LibraryNotFound(LibraryError):
    pass


class LibraryConflict(LibraryError):
    pass


class LibraryValidationError(LibraryError):
    def __init__(self, message: str, *, field_errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.field_errors = field_errors or []


@dataclass(frozen=True)
class ResourceConfig:
    table: str
    fields: tuple[str, ...]
    select_clause: str
    order_by: str
    search_fields: tuple[str, ...] = ()


BOARD_CONFIG = ResourceConfig(
    table="board_types",
    fields=("brand", "material", "thickness", "length_mm", "width_mm", "costing_mode", "grain_policy"),
    select_clause=(
        "id::text, brand, material, thickness, length_mm, width_mm, costing_mode, grain_policy, "
        "created_at, updated_at"
    ),
    order_by="brand ASC, material ASC, thickness ASC",
    search_fields=("brand", "material", "costing_mode", "grain_policy"),
)

SLIDE_CONFIG = ResourceConfig(
    table="slides",
    fields=(
        "brand",
        "model",
        "code",
        "length",
        "side_length",
        "side_clearance_total",
        "side_height_uplift",
        "mount_type",
        "product_family",
        "required_depth_mm",
        "drawer_depth_deduction_mm",
        "box_width_deduction_mm",
        "drawer_system_kind",
        "drawer_system_config",
        "accessory_config",
    ),
    select_clause=(
        "id::text, brand, model, code, length, side_length, "
        "side_clearance_total, side_height_uplift, mount_type, product_family, required_depth_mm, "
        "drawer_depth_deduction_mm, box_width_deduction_mm, drawer_system_kind, drawer_system_config, accessory_config, "
        "created_at, updated_at"
    ),
    order_by="brand ASC, model ASC, length ASC, code ASC",
    search_fields=("brand", "model", "code", "mount_type", "product_family"),
)

HINGE_CONFIG = ResourceConfig(
    table="hinges",
    fields=("brand", "model", "code", "opening_angle_deg", "accessory_config"),
    select_clause="id::text, brand, model, code, opening_angle_deg, accessory_config, created_at, updated_at",
    order_by="brand ASC, model ASC, opening_angle_deg ASC, code ASC",
    search_fields=("brand", "model", "code"),
)

HANDLE_CONFIG = ResourceConfig(
    table="handles",
    fields=("name", "supplier_id", "handle_type", "front_reduction_mm"),
    select_clause=(
        "id::text, name, supplier_id::text, "
        "COALESCE((SELECT s.name FROM suppliers s WHERE s.company_id = handles.company_id AND s.id = handles.supplier_id), '') AS supplier_name, "
        "handle_type, front_reduction_mm, created_at, updated_at"
    ),
    order_by="handle_type ASC, name ASC, supplier_id ASC",
    search_fields=("name", "handle_type"),
)

EXTRA_CATEGORY_CONFIG = ResourceConfig(
    table="extra_categories",
    fields=("name",),
    select_clause="id::text, name, created_at, updated_at",
    order_by="name ASC",
    search_fields=("name",),
)

PRICE_LIST_CONFIG = ResourceConfig(
    table="price_lists",
    fields=("name", "status", "effective_from", "effective_to"),
    select_clause="id::text, name, status, effective_from, effective_to, created_at, updated_at",
    order_by="created_at DESC, id DESC",
    search_fields=("name", "status"),
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
    search_fields=("item_type", "item_key", "price_component", "uom", "cost_source"),
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
    fields=("name", "code", "contact_name", "email", "phone", "notes", "default_discount_bps"),
    select_clause="id::text, name, code, contact_name, email, phone, notes, default_discount_bps, created_at, updated_at",
    order_by="name ASC, code ASC",
    search_fields=("name", "code", "contact_name", "email", "phone", "notes"),
)

CATALOG_BULK_CONFIGS: dict[str, ResourceConfig] = {
    "boards": BOARD_CONFIG,
    "slides": SLIDE_CONFIG,
    "hinges": HINGE_CONFIG,
    "handles": HANDLE_CONFIG,
    "suppliers": SUPPLIER_CONFIG,
}

CATALOG_BULK_ALLOWED_FIELDS: dict[str, set[str]] = {
    "boards": {"costing_mode", "grain_policy"},
    "slides": {"brand", "code"},
    "hinges": {"brand", "code"},
    "handles": {"supplier_id", "handle_type", "front_reduction_mm"},
    "extras": {"category_id", "supplier_id", "code", "notes"},
    "suppliers": {"contact_name", "email", "phone", "notes", "default_discount_bps"},
}

IMPORT_CATALOG_CONFIGS: dict[str, ResourceConfig] = {
    "boards": BOARD_CONFIG,
    "slides": SLIDE_CONFIG,
    "hinges": HINGE_CONFIG,
    "handles": HANDLE_CONFIG,
    "suppliers": SUPPLIER_CONFIG,
    "extra_categories": EXTRA_CATEGORY_CONFIG,
}

IMPORT_TARGET_TABLES: dict[str, str] = {
    "boards": "board_types",
    "slides": "slides",
    "hinges": "hinges",
    "handles": "handles",
    "suppliers": "suppliers",
    "extra_categories": "extra_categories",
    "extras": "extras",
    "supplier_item_costs": "item_suppliers",
    "price_list_items": "price_list_items",
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
DEFAULT_VAT_RATE_BPS = 1500
DEFAULT_MARKUP_BPS = 2500
PRICE_EFFECTIVE_STATUS_VALUES = {"current", "future", "retired"}
GRAIN_POLICY_VALUES = {"none", "optional", "required"}


class LibraryStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def list_boards(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(BOARD_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_board(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(BOARD_CONFIG, company_id, payload)

    def get_board(self, company_id: str, item_id: str) -> dict:
        return self._get(BOARD_CONFIG, company_id, item_id)

    def update_board(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(BOARD_CONFIG, company_id, item_id, payload)

    def delete_board(self, company_id: str, item_id: str) -> None:
        self._delete(BOARD_CONFIG, company_id, item_id)

    def list_slides(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(SLIDE_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_slide(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(SLIDE_CONFIG, company_id, payload)

    def create_slide_range(self, company_id: str, payload: dict[str, Any]) -> dict:
        slide_payloads = build_slide_range_payloads(payload)
        rows: list[dict[str, Any]] = []
        with self._connect() as conn:
            for slide_payload in slide_payloads:
                rows.append(self._create_with_conn(conn, SLIDE_CONFIG, company_id, slide_payload))
        return {"created_count": len(rows), "slides": rows}

    def get_slide(self, company_id: str, item_id: str) -> dict:
        return self._get(SLIDE_CONFIG, company_id, item_id)

    def update_slide(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(SLIDE_CONFIG, company_id, item_id, payload)

    def delete_slide(self, company_id: str, item_id: str) -> None:
        self._delete(SLIDE_CONFIG, company_id, item_id)

    def list_hinges(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(HINGE_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_hinge(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(HINGE_CONFIG, company_id, payload)

    def get_hinge(self, company_id: str, item_id: str) -> dict:
        return self._get(HINGE_CONFIG, company_id, item_id)

    def update_hinge(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(HINGE_CONFIG, company_id, item_id, payload)

    def delete_hinge(self, company_id: str, item_id: str) -> None:
        self._delete(HINGE_CONFIG, company_id, item_id)

    def list_suppliers(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(SUPPLIER_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_supplier(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(SUPPLIER_CONFIG, company_id, payload)

    def get_supplier(self, company_id: str, supplier_id: str) -> dict:
        return self._get(SUPPLIER_CONFIG, company_id, supplier_id)

    def update_supplier(self, company_id: str, supplier_id: str, payload: dict[str, Any]) -> dict:
        return self._update(SUPPLIER_CONFIG, company_id, supplier_id, payload)

    def delete_supplier(self, company_id: str, supplier_id: str) -> None:
        self._delete(SUPPLIER_CONFIG, company_id, supplier_id)

    def apply_supplier_discount(self, company_id: str, supplier_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_supplier(company_id, supplier_id)
        data = _clean_payload(payload)
        discount_bps = int(data.get("discount_bps", 0))
        apply_to_active_costs = bool(data.get("apply_to_active_costs", True))
        replacement_time = data.get("effective_from")
        source = str(data.get("source") or "supplier-discount").strip()
        source_ref = str(data.get("source_ref") or "").strip()

        with self._connect() as conn:
            updated_supplier = conn.execute(
                """
                UPDATE suppliers
                SET default_discount_bps = %s
                WHERE company_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (discount_bps, company_id, supplier_id),
            ).fetchone()
            if not updated_supplier:
                raise LibraryNotFound("Library row not found")
            matched_count = conn.execute(
                """
                SELECT count(*) AS count
                FROM item_suppliers
                WHERE company_id = %s
                  AND supplier_id = %s
                """,
                (company_id, supplier_id),
            ).fetchone()["count"]

            updated_count = 0
            unchanged_count = 0
            active_count = 0
            if apply_to_active_costs:
                active_rows = conn.execute(
                    """
                    SELECT
                        cost.id::text,
                        cost.item_supplier_id::text,
                        cost.list_price_cents,
                        cost.discount_bps,
                        cost.unit_cost_cents,
                        cost.currency_code
                    FROM item_suppliers item
                    JOIN supplier_item_costs cost
                      ON cost.company_id = item.company_id
                     AND cost.item_supplier_id = item.id
                     AND cost.effective_from <= COALESCE(%s, now())
                     AND (cost.effective_to IS NULL OR cost.effective_to > COALESCE(%s, now()))
                    WHERE item.company_id = %s
                      AND item.supplier_id = %s
                    ORDER BY item.item_type ASC, item.item_ref_id ASC, item.price_component ASC, item.id ASC
                    FOR UPDATE OF cost
                    """,
                    (replacement_time, replacement_time, company_id, supplier_id),
                ).fetchall()
                active_count = len(active_rows)

                for row in active_rows:
                    unit_cost_cents = _calculate_discounted_cost_cents(row["list_price_cents"], discount_bps)
                    if int(row["discount_bps"]) == discount_bps and int(row["unit_cost_cents"]) == unit_cost_cents:
                        unchanged_count += 1
                        continue

                    conn.execute(
                        """
                        UPDATE supplier_item_costs
                        SET effective_to = COALESCE(%s, now())
                        WHERE company_id = %s
                          AND id = %s
                        """,
                        (replacement_time, company_id, row["id"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO supplier_item_costs
                            (company_id, item_supplier_id, list_price_cents, discount_bps, unit_cost_cents,
                             currency_code, source, source_ref, effective_from, replaces_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, now()), %s)
                        """,
                        (
                            company_id,
                            row["item_supplier_id"],
                            row["list_price_cents"],
                            discount_bps,
                            unit_cost_cents,
                            row["currency_code"],
                            source,
                            source_ref,
                            replacement_time,
                            row["id"],
                        ),
                    )
                    updated_count += 1

        return {
            "supplier_id": supplier_id,
            "discount_bps": discount_bps,
            "matched_item_supplier_count": matched_count,
            "updated_cost_count": updated_count,
            "unchanged_cost_count": unchanged_count,
            "skipped_without_active_cost_count": matched_count - active_count if apply_to_active_costs else 0,
        }

    def list_handles(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(HANDLE_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_handle(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        if data.get("supplier_id"):
            self._ensure_supplier(company_id, data["supplier_id"])
        return self._create(HANDLE_CONFIG, company_id, data)

    def get_handle(self, company_id: str, item_id: str) -> dict:
        return self._get(HANDLE_CONFIG, company_id, item_id)

    def update_handle(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        if data.get("supplier_id"):
            self._ensure_supplier(company_id, data["supplier_id"])
        return self._update(HANDLE_CONFIG, company_id, item_id, data)

    def delete_handle(self, company_id: str, item_id: str) -> None:
        self._delete(HANDLE_CONFIG, company_id, item_id)

    def list_extra_categories(self, company_id: str, search: str | None = None, recent_days: int | None = None) -> list[dict]:
        return self._list(EXTRA_CATEGORY_CONFIG, company_id, search=search, recent_days=recent_days)

    def create_extra_category(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(EXTRA_CATEGORY_CONFIG, company_id, payload)

    def get_extra_category(self, company_id: str, item_id: str) -> dict:
        return self._get(EXTRA_CATEGORY_CONFIG, company_id, item_id)

    def update_extra_category(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        return self._update(EXTRA_CATEGORY_CONFIG, company_id, item_id, payload)

    def delete_extra_category(self, company_id: str, item_id: str) -> None:
        self._delete(EXTRA_CATEGORY_CONFIG, company_id, item_id)

    def list_extras(
        self,
        company_id: str,
        search: str | None = None,
        category_id: str | None = None,
        recent_days: int | None = None,
    ) -> list[dict]:
        filters = ["e.company_id = %s"]
        values: list[Any] = [company_id]
        search_value = _search_pattern(search)
        if search_value:
            filters.append(
                "(e.name ILIKE %s OR c.name ILIKE %s OR COALESCE(s.name, e.supplier, '') ILIKE %s OR e.code ILIKE %s OR e.notes ILIKE %s)"
            )
            values.extend([search_value] * 5)
        if category_id:
            filters.append("e.category_id = %s")
            values.append(category_id)
        recent_cutoff = _recent_cutoff(recent_days)
        if recent_cutoff:
            filters.append("e.updated_at >= %s")
            values.append(recent_cutoff)
        where_clause = " AND ".join(filters)
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT
                    e.id::text,
                    e.name,
                    e.category_id::text,
                    c.name AS category_name,
                    e.supplier_id::text,
                    COALESCE(s.name, e.supplier, '') AS supplier,
                    e.code,
                    e.notes,
                    e.created_at,
                    e.updated_at
                FROM extras e
                JOIN extra_categories c ON c.id = e.category_id
                LEFT JOIN suppliers s
                  ON s.company_id = e.company_id
                 AND s.id = e.supplier_id
                WHERE {where_clause}
                ORDER BY c.name ASC, e.name ASC, COALESCE(s.name, e.supplier, '') ASC, e.code ASC
                """,
                values,
            ).fetchall()

    def create_extra(self, company_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_extra_category(company_id, payload["category_id"])
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO extras (company_id, name, category_id, supplier_id, supplier, code, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        _clean(payload["name"]),
                        payload["category_id"],
                        *_extra_supplier_values(conn, company_id, payload),
                        _clean(payload.get("code", "")),
                        _clean(payload.get("notes", "")),
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        return self.get_extra(company_id, row["id"])

    def get_extra(self, company_id: str, item_id: str) -> dict:
        with self._connect() as conn:
            return self._get_extra_with_conn(conn, company_id, item_id)

    def update_extra(self, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_extra_category(company_id, payload["category_id"])
        try:
            with self._connect() as conn:
                row = self._update_extra_with_conn(conn, company_id, item_id, payload)
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        return row

    def delete_extra(self, company_id: str, item_id: str) -> None:
        self._delete(ResourceConfig("extras", (), "", ""), company_id, item_id)

    def bulk_update_catalog(self, company_id: str, payload: dict[str, Any]) -> dict:
        resource = str(payload.get("resource") or "")
        item_ids = [str(item_id).strip() for item_id in payload.get("item_ids", []) if str(item_id).strip()]
        updates = _clean_payload(payload.get("updates") or {})
        confirm = bool(payload.get("confirm"))
        allowed_fields = CATALOG_BULK_ALLOWED_FIELDS.get(resource)
        if not allowed_fields:
            raise LibraryValidationError("Unsupported catalog bulk resource")
        changed_fields = sorted(field for field in updates if field in allowed_fields)
        rejected_fields = sorted(field for field in updates if field not in allowed_fields)
        if rejected_fields:
            raise LibraryValidationError(f"Bulk update does not support: {', '.join(rejected_fields)}")
        if not changed_fields:
            raise LibraryValidationError("Choose at least one supported field to update")
        if not item_ids:
            raise LibraryValidationError("Choose at least one row to update")
        if resource == "extras" and "category_id" in changed_fields:
            self._ensure_extra_category(company_id, str(updates["category_id"]))
        if resource == "handles" and updates.get("supplier_id"):
            self._ensure_supplier(company_id, str(updates["supplier_id"]))

        rows: list[dict[str, Any]] = []
        with self._connect() as conn:
            for item_id in item_ids:
                try:
                    current = self._get_catalog_bulk_row_with_conn(conn, resource, company_id, item_id)
                    label = _catalog_bulk_label(resource, current)
                    next_payload = _catalog_bulk_payload(resource, current)
                    for field in changed_fields:
                        next_payload[field] = updates[field]
                    if confirm:
                        updated = self._update_catalog_bulk_row_with_conn(conn, resource, company_id, item_id, next_payload)
                        rows.append(
                            {
                                "item_id": item_id,
                                "label": _catalog_bulk_label(resource, updated),
                                "status": "updated",
                                "message": f"Updated {len(changed_fields)} field{'s' if len(changed_fields) != 1 else ''}.",
                                "changed_fields": changed_fields,
                            }
                        )
                    else:
                        rows.append(
                            {
                                "item_id": item_id,
                                "label": label,
                                "status": "preview",
                                "message": f"Will update {len(changed_fields)} field{'s' if len(changed_fields) != 1 else ''}.",
                                "changed_fields": changed_fields,
                            }
                        )
                except LibraryError as exc:
                    rows.append(
                        {
                            "item_id": item_id,
                            "label": item_id,
                            "status": "failed",
                            "message": str(exc) or "Could not update this row.",
                            "changed_fields": [],
                        }
                    )

        return _bulk_update_response(
            resource=resource,
            confirm=confirm,
            requested_count=len(item_ids),
            rows=rows,
        )

    def list_item_suppliers(
        self,
        company_id: str,
        item_type: str | None = None,
        item_ref_id: str | None = None,
        search: str | None = None,
        recent_days: int | None = None,
        supplier_id: str | None = None,
        has_active_cost: bool | None = None,
    ) -> list[dict]:
        with self._connect() as conn:
            return self._list_item_suppliers_with_conn(
                conn,
                company_id,
                item_type=item_type,
                item_ref_id=item_ref_id,
                search=search,
                recent_days=recent_days,
                supplier_id=supplier_id,
                has_active_cost=has_active_cost,
            )

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
        as_of: datetime | None = None,
    ) -> list[dict]:
        self._ensure_item_supplier(company_id, item_supplier_id)
        as_of_dt = _coerce_effective_datetime(as_of)
        history_filter = "" if include_history else "AND effective_from <= %s AND (effective_to IS NULL OR effective_to > %s)"
        values: list[Any] = [company_id, item_supplier_id]
        if not include_history:
            values.extend([as_of_dt, as_of_dt])
        with self._connect() as conn:
            rows = conn.execute(
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
                values,
            ).fetchall()
        return _with_effective_statuses(rows, as_of_dt)

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
                  AND effective_from <= COALESCE(%s, now())
                  AND (effective_to IS NULL OR effective_to > COALESCE(%s, now()))
                ORDER BY effective_from DESC, id DESC
                LIMIT 1
                FOR UPDATE
                """,
                (company_id, item_supplier_id, replacement_time, replacement_time),
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
        return _with_effective_status(row)

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
        refresh_time = payload.get("effective_from")
        if selection_mode not in {"preferred_then_cheapest", "preferred_only", "cheapest"}:
            raise LibraryValidationError("Unsupported supplier cost selection mode")
        unsupported_types = [item_type for item_type in item_types if item_type not in PRICE_ITEM_TYPE_TABLES]
        if unsupported_types:
            raise LibraryValidationError(f"Unsupported item_types: {', '.join(unsupported_types)}")

        with self._connect() as conn:
            item_rows = self._fetch_supplier_generation_rows(conn, company_id, item_types, refresh_time)
            selected_rows, missing_price_count = _select_supplier_generation_rows(item_rows, selection_mode)

            created_count = 0
            updated_count = 0
            unchanged_count = 0
            skipped_override_count = 0

            for selected in selected_rows:
                item_key = f"{selected['item_type']}::{selected['item_ref_id']}"
                try:
                    price_component = normalize_price_component(selected["price_component"], default="unit")
                    uom = normalize_order_uom(selected["order_uom"], field="uom")
                    validate_pricing_combination(
                        item_type=selected["item_type"],
                        price_component=price_component,
                        uom=uom,
                        uom_field="uom",
                    )
                except PricingFieldValidationError as exc:
                    raise _pricing_library_validation_error(exc) from exc
                current = conn.execute(
                    """
                    SELECT id::text, unit_price_cents, uom, source_supplier_item_cost_id::text, cost_source
                    FROM price_list_items
                    WHERE company_id = %s
                      AND price_list_id = %s
                      AND item_type = %s
                      AND item_key = %s
                      AND price_component = %s
                      AND effective_from <= COALESCE(%s, now())
                      AND (effective_to IS NULL OR effective_to > COALESCE(%s, now()))
                    ORDER BY effective_from DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (
                        company_id,
                        price_list_id,
                        selected["item_type"],
                        item_key,
                        price_component,
                        refresh_time,
                        refresh_time,
                    ),
                ).fetchone()

                if current and preserve_manual_overrides and current["cost_source"] != "supplier":
                    skipped_override_count += 1
                    continue

                source_cost_id = selected["supplier_item_cost_id"]
                unit_cost_cents = int(selected["unit_cost_cents"])
                if current and _generated_price_item_matches(current, source_cost_id, unit_cost_cents, uom):
                    unchanged_count += 1
                    continue

                if current:
                    conn.execute(
                        """
                        UPDATE price_list_items
                        SET effective_to = COALESCE(%s, now())
                        WHERE company_id = %s
                          AND price_list_id = %s
                          AND id = %s
                        """,
                        (refresh_time, company_id, price_list_id, current["id"]),
                    )
                    updated_count += 1
                else:
                    created_count += 1

                conn.execute(
                    """
                    INSERT INTO price_list_items
                        (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                         uom, unit_price_cents, source_supplier_item_cost_id, cost_source, effective_from, replaces_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'supplier', COALESCE(%s, now()), %s)
                    """,
                    (
                        company_id,
                        price_list_id,
                        selected["item_type"],
                        selected["item_ref_id"],
                        item_key,
                        price_component,
                        uom,
                        unit_cost_cents,
                        source_cost_id,
                        refresh_time,
                        current["id"] if current else None,
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

    def get_active_price_list(self, company_id: str, as_of: datetime | date | None = None) -> dict:
        as_of_date = _coerce_effective_date(as_of)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {PRICE_LIST_CONFIG.select_clause}
                FROM price_lists
                WHERE company_id = %s
                  AND status = 'active'
                  AND (effective_from IS NULL OR effective_from <= %s)
                  AND (effective_to IS NULL OR effective_to >= %s)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (company_id, as_of_date, as_of_date),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Active price list not found")
        return row

    def create_price_list(self, company_id: str, payload: dict[str, Any]) -> dict:
        return self._create(PRICE_LIST_CONFIG, company_id, payload)

    def get_price_list(self, company_id: str, price_list_id: str) -> dict:
        return self._get(PRICE_LIST_CONFIG, company_id, price_list_id)

    def get_price_list_coverage(self, company_id: str, price_list_id: str) -> dict:
        with self._connect() as conn:
            price_list = conn.execute(
                """
                SELECT id::text, name
                FROM price_lists
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, price_list_id),
            ).fetchone()
            if not price_list:
                raise LibraryNotFound("Price list not found")

            rows = _price_list_coverage_rows(conn, company_id, price_list_id)

        coverage_rows = _build_price_list_coverage_rows(rows)
        groups = _price_coverage_groups(coverage_rows)
        summary_counts = _price_coverage_counts(coverage_rows)
        return {
            "price_list_id": price_list["id"],
            "price_list_name": price_list["name"],
            "generated_at": datetime.now(UTC),
            **summary_counts,
            "groups": groups,
        }

    def update_price_list(self, company_id: str, price_list_id: str, payload: dict[str, Any]) -> dict:
        return self._update(PRICE_LIST_CONFIG, company_id, price_list_id, payload)

    def delete_price_list(self, company_id: str, price_list_id: str) -> None:
        self._delete(PRICE_LIST_CONFIG, company_id, price_list_id)

    def list_price_list_items(
        self,
        company_id: str,
        price_list_id: str,
        include_history: bool = False,
        as_of: datetime | None = None,
        search: str | None = None,
        item_type: str | None = None,
        effective_status: str | None = None,
        recent_days: int | None = None,
    ) -> list[dict]:
        self._ensure_price_list(company_id, price_list_id)
        as_of_dt = _coerce_effective_datetime(as_of)
        history_filter = "" if include_history else "AND effective_from <= %s AND (effective_to IS NULL OR effective_to > %s)"
        values: list[Any] = [company_id, price_list_id]
        if not include_history:
            values.extend([as_of_dt, as_of_dt])
        extra_filters: list[str] = []
        if item_type:
            extra_filters.append("item_type = %s")
            values.append(item_type)
        search_value = _search_pattern(search)
        if search_value:
            extra_filters.append("(item_type ILIKE %s OR item_key ILIKE %s OR price_component ILIKE %s OR uom ILIKE %s OR cost_source ILIKE %s)")
            values.extend([search_value] * 5)
        recent_cutoff = _recent_cutoff(recent_days)
        if recent_cutoff:
            extra_filters.append("updated_at >= %s")
            values.append(recent_cutoff)
        extra_where = f"AND {' AND '.join(extra_filters)}" if extra_filters else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
                FROM price_list_items
                WHERE company_id = %s
                  AND price_list_id = %s
                  {history_filter}
                  {extra_where}
                ORDER BY {PRICE_LIST_ITEM_CONFIG.order_by}
                """,
                values,
            ).fetchall()
        rows = _with_effective_statuses(rows, as_of_dt)
        if effective_status:
            if effective_status not in PRICE_EFFECTIVE_STATUS_VALUES:
                raise LibraryValidationError("Unsupported effective_status filter")
            rows = [row for row in rows if row.get("effective_status") == effective_status]
        return rows

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
        return _with_effective_status(row)

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
        replacement_time = data.get("effective_from")

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
                  AND effective_from <= COALESCE(%s, now())
                  AND (effective_to IS NULL OR effective_to > COALESCE(%s, now()))
                ORDER BY effective_from DESC
                LIMIT 1
                """,
                (
                    company_id,
                    price_list_id,
                    data["item_type"],
                    data["item_key"],
                    data["price_component"],
                    replacement_time,
                    replacement_time,
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
                  AND (effective_to IS NULL OR effective_to > now())
                RETURNING id::text
                """,
                (company_id, price_list_id, item_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Price list item not found")

    def bulk_update_price_list_items(self, company_id: str, price_list_id: str, payload: dict[str, Any]) -> dict:
        self._ensure_price_list(company_id, price_list_id)
        item_ids = [str(item_id).strip() for item_id in payload.get("item_ids", []) if str(item_id).strip()]
        updates = _price_bulk_updates(payload)
        confirm = bool(payload.get("confirm"))
        if not item_ids:
            raise LibraryValidationError("Choose at least one price row to update")
        if not updates:
            raise LibraryValidationError("Choose at least one price field to update")

        changed_fields = sorted(updates)
        rows: list[dict[str, Any]] = []
        with self._connect() as conn:
            for item_id in item_ids:
                current = _with_effective_status(
                    self._get_price_list_item_with_conn(conn, company_id, price_list_id, item_id)
                )
                label = _price_bulk_label(current)
                if current["effective_status"] != "current":
                    rows.append(
                        {
                            "item_id": item_id,
                            "label": label,
                            "status": "failed",
                            "message": "Only current price rows can be bulk edited.",
                            "changed_fields": changed_fields,
                        }
                    )
                    continue

                next_payload = _price_bulk_payload(current)
                next_payload.update(updates)
                next_payload["price_list_id"] = price_list_id
                if updates.get("cost_source") in {"manual", "override"}:
                    next_payload["source_supplier_item_cost_id"] = None

                if confirm:
                    updated = self._update_price_list_item_with_conn(conn, company_id, item_id, next_payload)
                    rows.append(
                        {
                            "item_id": item_id,
                            "label": _price_bulk_label(updated),
                            "status": "updated",
                            "message": f"Updated {len(changed_fields)} field{'s' if len(changed_fields) != 1 else ''}.",
                            "changed_fields": changed_fields,
                        }
                    )
                else:
                    rows.append(
                        {
                            "item_id": item_id,
                            "label": label,
                            "status": "preview",
                            "message": f"Will create a replacement price row with {len(changed_fields)} changed field{'s' if len(changed_fields) != 1 else ''}.",
                            "changed_fields": changed_fields,
                        }
                    )

        return _bulk_update_response(
            resource="price_list_items",
            confirm=confirm,
            requested_count=len(item_ids),
            rows=rows,
        )

    def get_setup_checklist(self, company_id: str) -> dict:
        with self._connect() as conn:
            summary = conn.execute(
                """
                SELECT
                    (SELECT count(*)::int FROM board_types WHERE company_id = %(company_id)s) AS board_count,
                    (SELECT count(*)::int FROM slides WHERE company_id = %(company_id)s) AS slide_count,
                    (SELECT count(*)::int FROM hinges WHERE company_id = %(company_id)s) AS hinge_count,
                    (SELECT count(*)::int FROM handles WHERE company_id = %(company_id)s) AS handle_count,
                    (SELECT count(*)::int FROM extra_categories WHERE company_id = %(company_id)s) AS extra_category_count,
                    (SELECT count(*)::int FROM extras WHERE company_id = %(company_id)s) AS extra_count,
                    (SELECT count(*)::int FROM suppliers WHERE company_id = %(company_id)s) AS supplier_count,
                    (
                        SELECT count(*)::int
                        FROM item_suppliers item
                        JOIN supplier_item_costs cost
                          ON cost.company_id = item.company_id
                         AND cost.item_supplier_id = item.id
                         AND cost.effective_from <= now()
                         AND (cost.effective_to IS NULL OR cost.effective_to > now())
                        WHERE item.company_id = %(company_id)s
                    ) AS active_supplier_cost_count,
                    (
                        SELECT count(*)::int
                        FROM price_lists
                        WHERE company_id = %(company_id)s
                          AND status = 'active'
                    ) AS active_price_list_count,
                    (
                        SELECT count(*)::int
                        FROM price_lists list
                        JOIN price_list_items item
                         ON item.company_id = list.company_id
                         AND item.price_list_id = list.id
                         AND item.effective_from <= now()
                         AND (item.effective_to IS NULL OR item.effective_to > now())
                        WHERE list.company_id = %(company_id)s
                          AND list.status = 'active'
                    ) AS active_price_count,
                    (
                        SELECT count(*)::int
                        FROM pricing_settings
                        WHERE company_id = %(company_id)s
                    ) AS pricing_settings_count,
                    (
                        SELECT vat_rate_bps
                        FROM pricing_settings
                        WHERE company_id = %(company_id)s
                        LIMIT 1
                    ) AS vat_rate_bps,
                    (
                        SELECT default_markup_bps
                        FROM pricing_settings
                        WHERE company_id = %(company_id)s
                        LIMIT 1
                    ) AS default_markup_bps,
                    (SELECT count(*)::int FROM quotes WHERE company_id = %(company_id)s) AS quote_count,
                    (
                        SELECT count(*)::int
                        FROM quotes
                        WHERE company_id = %(company_id)s
                          AND default_carcass_board_type_id IS NOT NULL
                          AND default_door_board_type_id IS NOT NULL
                          AND default_panel_board_type_id IS NOT NULL
                          AND default_slide_id IS NOT NULL
                          AND default_hinge_id IS NOT NULL
                          AND default_base_handle_id IS NOT NULL
                          AND default_wall_handle_id IS NOT NULL
                          AND default_tall_handle_id IS NOT NULL
                          AND default_drawer_handle_id IS NOT NULL
                    ) AS quote_with_defaults_count
                """,
                {"company_id": company_id},
            ).fetchone()
        return _build_setup_checklist(summary)

    def preview_library_import(self, company_id: str, payload: dict[str, Any]) -> dict:
        with self._connect() as conn:
            preview, _, _ = self._preview_library_import_with_conn(conn, company_id, payload)
        return preview

    def apply_library_import(self, company_id: str, user_id: str, payload: dict[str, Any]) -> dict:
        source_ref = str(payload.get("source_ref") or "").strip()
        content = str(payload.get("content") or "")
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        try:
            with self._connect() as conn:
                preview, references, price_list_id = self._preview_library_import_with_conn(conn, company_id, payload)
                batch = conn.execute(
                    """
                    INSERT INTO library_import_batches
                        (company_id, user_id, resource, source_format, filename, sheet_name, source_ref,
                         price_list_id, content_sha256)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        user_id,
                        preview["resource"],
                        preview["source_format"],
                        str(payload.get("filename") or "").strip(),
                        preview.get("sheet_name"),
                        source_ref,
                        price_list_id or None,
                        content_sha256,
                    ),
                ).fetchone()
                batch_id = batch["id"]

                rows: list[dict[str, Any]] = []
                summary = {
                    "total_rows": 0,
                    "created_count": 0,
                    "updated_count": 0,
                    "skipped_count": 0,
                    "failed_count": 0,
                }
                for row in preview["rows"]:
                    outcome = self._apply_import_preview_row(
                        conn,
                        company_id,
                        preview["resource"],
                        row,
                        references,
                        source_ref,
                    )
                    rows.append(outcome)
                    summary["total_rows"] += 1
                    if outcome["status"] == "created":
                        summary["created_count"] += 1
                    elif outcome["status"] == "updated":
                        summary["updated_count"] += 1
                    elif outcome["status"] == "skipped":
                        summary["skipped_count"] += 1
                    else:
                        summary["failed_count"] += 1

                    conn.execute(
                        """
                        INSERT INTO library_import_rows
                            (batch_id, company_id, row_number, row_status, import_identity, target_table,
                             target_id, message, payload, problems)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            batch_id,
                            company_id,
                            outcome["row_number"],
                            outcome["status"],
                            outcome["identity"],
                            IMPORT_TARGET_TABLES[preview["resource"]],
                            outcome["target_id"] or None,
                            outcome["message"],
                            Jsonb(row.get("payload") or {}),
                            Jsonb(outcome.get("problems") or []),
                        ),
                    )

                conn.execute(
                    """
                    UPDATE library_import_batches
                    SET total_rows = %s,
                        created_count = %s,
                        updated_count = %s,
                        skipped_count = %s,
                        failed_count = %s,
                        status = %s
                    WHERE company_id = %s
                      AND id = %s
                    """,
                    (
                        summary["total_rows"],
                        summary["created_count"],
                        summary["updated_count"],
                        summary["skipped_count"],
                        summary["failed_count"],
                        "completed",
                        company_id,
                        batch_id,
                    ),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Import failed; no rows were applied.") from exc
        except psycopg.errors.ForeignKeyViolation as exc:
            raise LibraryValidationError("Import references a row outside this company library.") from exc

        return {
            "batch_id": batch_id,
            "resource": preview["resource"],
            "source_format": preview["source_format"],
            "summary": summary,
            "rows": rows,
        }

    def _preview_library_import_with_conn(self, conn, company_id: str, payload: dict[str, Any]) -> tuple[dict, dict, str]:
        resource = str(payload.get("resource") or "").strip().lower().replace("-", "_")
        price_list_id = str(payload.get("price_list_id") or "").strip()
        if not price_list_id and resource == "price_list_items":
            active_price_list = self._get_active_price_list_with_conn(conn, company_id)
            price_list_id = active_price_list["id"] if active_price_list else ""

        price_items: list[dict] = []
        if price_list_id:
            if not self._price_list_exists_with_conn(conn, company_id, price_list_id):
                price_list_id = ""
            else:
                price_items = self._list_price_list_items_with_conn(conn, company_id, price_list_id)

        snapshot = {
            "boards": self._list_with_conn(conn, BOARD_CONFIG, company_id),
            "slides": self._list_with_conn(conn, SLIDE_CONFIG, company_id),
            "hinges": self._list_with_conn(conn, HINGE_CONFIG, company_id),
            "handles": self._list_with_conn(conn, HANDLE_CONFIG, company_id),
            "suppliers": self._list_with_conn(conn, SUPPLIER_CONFIG, company_id),
            "extra_categories": self._list_with_conn(conn, EXTRA_CATEGORY_CONFIG, company_id),
            "extras": self._list_extras_with_conn(conn, company_id),
            "item_suppliers": self._list_item_suppliers_with_conn(conn, company_id),
            "price_items": price_items,
            "price_list_id": price_list_id,
        }
        references = build_reference_maps(snapshot)
        return build_import_preview(payload, references), references, price_list_id

    def _apply_import_preview_row(
        self,
        conn,
        company_id: str,
        resource: str,
        row: dict[str, Any],
        references: dict[str, Any],
        source_ref: str,
    ) -> dict[str, Any]:
        if row["status"] in {"blocked", "duplicate"}:
            return _import_apply_row(
                row,
                "failed",
                row["message"],
                problems=row.get("problems") or [],
            )
        existing = _import_existing(resource, row["identity"], references)
        if row["status"] == "skipped":
            return _import_apply_row(
                row,
                "skipped",
                row["message"],
                target_id=str(existing.get("id") or "") if existing else "",
            )
        if row["status"] == "update" and not existing:
            raise LibraryConflict("Import target changed before apply; preview the file again.")

        if resource in IMPORT_CATALOG_CONFIGS:
            config = IMPORT_CATALOG_CONFIGS[resource]
            if resource == "handles" and (row["payload"].get("supplier_id")):
                self._ensure_supplier(company_id, str(row["payload"]["supplier_id"]))
            if row["status"] == "create":
                target = self._create_with_conn(conn, config, company_id, row["payload"])
                return _import_apply_row(row, "created", "Created library row.", target_id=target["id"])
            target = self._update_with_conn(conn, config, company_id, existing["id"], row["payload"])
            return _import_apply_row(row, "updated", "Updated library row.", target_id=target["id"])

        if resource == "extras":
            if row["status"] == "create":
                target = self._create_extra_with_conn(conn, company_id, row["payload"])
                return _import_apply_row(row, "created", "Created library row.", target_id=target["id"])
            target = self._update_extra_with_conn(conn, company_id, existing["id"], row["payload"])
            return _import_apply_row(row, "updated", "Updated library row.", target_id=target["id"])

        if resource == "supplier_item_costs":
            target_id = self._apply_supplier_item_cost_import(conn, company_id, row, existing, source_ref)
            status = "created" if row["status"] == "create" else "updated"
            return _import_apply_row(row, status, f"{status.capitalize()} supplier cost source.", target_id=target_id)

        if resource == "price_list_items":
            target_id = self._apply_price_list_item_import(conn, company_id, row, existing)
            status = "created" if row["status"] == "create" else "updated"
            return _import_apply_row(row, status, f"{status.capitalize()} price list row.", target_id=target_id)

        raise LibraryValidationError("Unsupported import type")

    def _list(
        self,
        config: ResourceConfig,
        company_id: str,
        search: str | None = None,
        recent_days: int | None = None,
    ) -> list[dict]:
        with self._connect() as conn:
            return self._list_with_conn(conn, config, company_id, search=search, recent_days=recent_days)

    def _list_with_conn(
        self,
        conn,
        config: ResourceConfig,
        company_id: str,
        search: str | None = None,
        recent_days: int | None = None,
    ) -> list[dict]:
        filters = ["company_id = %s"]
        values: list[Any] = [company_id]
        search_value = _search_pattern(search)
        if search_value and config.search_fields:
            filters.append("(" + " OR ".join(f"{field}::text ILIKE %s" for field in config.search_fields) + ")")
            values.extend([search_value] * len(config.search_fields))
        recent_cutoff = _recent_cutoff(recent_days)
        if recent_cutoff:
            filters.append("updated_at >= %s")
            values.append(recent_cutoff)
        where_clause = " AND ".join(filters)
        return conn.execute(
            f"""
            SELECT {config.select_clause}
            FROM {config.table}
            WHERE {where_clause}
            ORDER BY {config.order_by}
            """,
            values,
        ).fetchall()

    def _list_extras_with_conn(self, conn, company_id: str) -> list[dict]:
        return conn.execute(
            """
            SELECT
                e.id::text,
                e.name,
                e.category_id::text,
                c.name AS category_name,
                e.supplier_id::text,
                COALESCE(s.name, e.supplier, '') AS supplier,
                e.code,
                e.notes,
                e.created_at,
                e.updated_at
            FROM extras e
            JOIN extra_categories c ON c.id = e.category_id
            LEFT JOIN suppliers s
              ON s.company_id = e.company_id
             AND s.id = e.supplier_id
            WHERE e.company_id = %s
            ORDER BY c.name ASC, e.name ASC, COALESCE(s.name, e.supplier, '') ASC, e.code ASC
            """,
            (company_id,),
        ).fetchall()

    def _list_item_suppliers_with_conn(
        self,
        conn,
        company_id: str,
        item_type: str | None = None,
        item_ref_id: str | None = None,
        search: str | None = None,
        recent_days: int | None = None,
        supplier_id: str | None = None,
        has_active_cost: bool | None = None,
    ) -> list[dict]:
        filters = ["item.company_id = %s"]
        values: list[Any] = [company_id]
        if item_type:
            filters.append("item.item_type = %s")
            values.append(item_type)
        if item_ref_id:
            filters.append("item.item_ref_id = %s")
            values.append(item_ref_id)
        if supplier_id:
            filters.append("item.supplier_id = %s")
            values.append(supplier_id)
        search_value = _search_pattern(search)
        if search_value:
            filters.append(
                "("
                "item.item_type ILIKE %s OR item.supplier_sku ILIKE %s OR item.supplier_description ILIKE %s "
                "OR item.price_component ILIKE %s OR item.order_uom ILIKE %s OR item.notes ILIKE %s "
                "OR supplier.name ILIKE %s"
                ")"
            )
            values.extend([search_value] * 7)
        recent_cutoff = _recent_cutoff(recent_days)
        if recent_cutoff:
            filters.append("(item.updated_at >= %s OR cost.updated_at >= %s)")
            values.extend([recent_cutoff, recent_cutoff])
        if has_active_cost is not None:
            filters.append("cost.id IS NOT NULL" if has_active_cost else "cost.id IS NULL")
        where_clause = " AND ".join(filters)
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
             AND cost.effective_from <= now()
             AND (cost.effective_to IS NULL OR cost.effective_to > now())
            WHERE {where_clause}
            ORDER BY item.item_type ASC, supplier.name ASC, item.supplier_sku ASC, item.id ASC
            """,
            values,
        ).fetchall()

    def _list_price_list_items_with_conn(
        self,
        conn,
        company_id: str,
        price_list_id: str,
        include_history: bool = False,
        as_of: datetime | None = None,
    ) -> list[dict]:
        as_of_dt = _coerce_effective_datetime(as_of)
        history_filter = "" if include_history else "AND effective_from <= %s AND (effective_to IS NULL OR effective_to > %s)"
        values: list[Any] = [company_id, price_list_id]
        if not include_history:
            values.extend([as_of_dt, as_of_dt])
        rows = conn.execute(
            f"""
            SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
            FROM price_list_items
            WHERE company_id = %s
              AND price_list_id = %s
              {history_filter}
            ORDER BY {PRICE_LIST_ITEM_CONFIG.order_by}
            """,
            values,
        ).fetchall()
        return _with_effective_statuses(rows, as_of_dt)

    def _get_active_price_list_with_conn(self, conn, company_id: str, as_of: datetime | date | None = None) -> dict | None:
        as_of_date = _coerce_effective_date(as_of)
        return conn.execute(
            f"""
            SELECT {PRICE_LIST_CONFIG.select_clause}
            FROM price_lists
            WHERE company_id = %s
              AND status = 'active'
              AND (effective_from IS NULL OR effective_from <= %s)
              AND (effective_to IS NULL OR effective_to >= %s)
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (company_id, as_of_date, as_of_date),
        ).fetchone()

    def _price_list_exists_with_conn(self, conn, company_id: str, price_list_id: str) -> bool:
        row = conn.execute(
            """
            SELECT id::text
            FROM price_lists
            WHERE company_id = %s
              AND id = %s
            """,
            (company_id, price_list_id),
        ).fetchone()
        return bool(row)

    def _create(self, config: ResourceConfig, company_id: str, payload: dict[str, Any]) -> dict:
        with self._connect() as conn:
            return self._create_with_conn(conn, config, company_id, payload)

    def _create_with_conn(self, conn, config: ResourceConfig, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        columns = ("company_id", *config.fields)
        values = [company_id, *[_db_value(data[field]) for field in config.fields]]
        if config.table in BRAND_TABLES:
            columns = (*columns, "brand_id")
            values.append(self._get_or_create_brand_with_conn(conn, company_id, data["brand"])["id"])
        placeholders = ", ".join(["%s"] * len(columns))
        try:
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
            return self._get_with_conn(conn, config, company_id, item_id)

    def _get_with_conn(self, conn, config: ResourceConfig, company_id: str, item_id: str) -> dict:
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
        with self._connect() as conn:
            return self._update_with_conn(conn, config, company_id, item_id, payload)

    def _update_with_conn(self, conn, config: ResourceConfig, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        assignments = ", ".join([f"{field} = %s" for field in config.fields])
        values = [*[_db_value(data[field]) for field in config.fields], company_id, item_id]
        if config.table in BRAND_TABLES:
            assignments = f"{assignments}, brand_id = %s"
            values = [
                *[_db_value(data[field]) for field in config.fields],
                self._get_or_create_brand_with_conn(conn, company_id, data["brand"])["id"],
                company_id,
                item_id,
            ]
        try:
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

    def _create_extra_with_conn(self, conn, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            row = conn.execute(
                """
                INSERT INTO extras (company_id, name, category_id, supplier_id, supplier, code, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id::text
                """,
                (
                    company_id,
                    _clean(data["name"]),
                    data["category_id"],
                    *_extra_supplier_values(conn, company_id, data),
                    _clean(data.get("code", "")),
                    _clean(data.get("notes", "")),
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        return self._get_extra_with_conn(conn, company_id, row["id"])

    def _get_extra_with_conn(self, conn, company_id: str, item_id: str) -> dict:
        row = conn.execute(
            """
            SELECT
                e.id::text,
                e.name,
                e.category_id::text,
                c.name AS category_name,
                e.supplier_id::text,
                COALESCE(s.name, e.supplier, '') AS supplier,
                e.code,
                e.notes,
                e.created_at,
                e.updated_at
            FROM extras e
            JOIN extra_categories c ON c.id = e.category_id
            LEFT JOIN suppliers s
              ON s.company_id = e.company_id
             AND s.id = e.supplier_id
            WHERE e.company_id = %s
              AND e.id = %s
            """,
            (company_id, item_id),
        ).fetchone()
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def _update_extra_with_conn(self, conn, company_id: str, item_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            row = conn.execute(
                """
                UPDATE extras
                SET name = %s,
                    category_id = %s,
                    supplier_id = %s,
                    supplier = %s,
                    code = %s,
                    notes = %s
                WHERE company_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (
                    _clean(data["name"]),
                    data["category_id"],
                    *_extra_supplier_values(conn, company_id, data),
                    _clean(data.get("code", "")),
                    _clean(data.get("notes", "")),
                    company_id,
                    item_id,
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise LibraryConflict("Library row already exists") from exc
        if not row:
            raise LibraryNotFound("Library row not found")
        return self._get_extra_with_conn(conn, company_id, row["id"])

    def _get_catalog_bulk_row_with_conn(self, conn, resource: str, company_id: str, item_id: str) -> dict:
        if resource == "extras":
            return self._get_extra_with_conn(conn, company_id, item_id)
        config = CATALOG_BULK_CONFIGS.get(resource)
        if not config:
            raise LibraryValidationError("Unsupported catalog bulk resource")
        return self._get_with_conn(conn, config, company_id, item_id)

    def _update_catalog_bulk_row_with_conn(
        self,
        conn,
        resource: str,
        company_id: str,
        item_id: str,
        payload: dict[str, Any],
    ) -> dict:
        if resource == "extras":
            return self._update_extra_with_conn(conn, company_id, item_id, payload)
        config = CATALOG_BULK_CONFIGS.get(resource)
        if not config:
            raise LibraryValidationError("Unsupported catalog bulk resource")
        return self._update_with_conn(conn, config, company_id, item_id, payload)

    def _apply_supplier_item_cost_import(
        self,
        conn,
        company_id: str,
        row: dict[str, Any],
        existing: dict[str, Any] | None,
        source_ref: str,
    ) -> str:
        data = _clean_payload(row["payload"])
        if row["status"] == "create":
            item_supplier_id = self._create_item_supplier_with_conn(conn, company_id, data)
        else:
            item_supplier_id = existing["id"]
            self._update_item_supplier_with_conn(conn, company_id, item_supplier_id, data)
        self._upsert_supplier_item_cost_with_conn(conn, company_id, item_supplier_id, data, source_ref)
        return item_supplier_id

    def _create_item_supplier_with_conn(self, conn, company_id: str, data: dict[str, Any]) -> str:
        if bool(data.get("is_preferred", True)):
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
                data.get("supplier_sku", ""),
                data.get("supplier_description", ""),
                data.get("price_component") or "unit",
                data.get("order_uom") or "pcs",
                bool(data.get("is_preferred", True)),
                data.get("notes", ""),
            ),
        ).fetchone()
        return row["id"]

    def _update_item_supplier_with_conn(self, conn, company_id: str, item_supplier_id: str, data: dict[str, Any]) -> None:
        if bool(data.get("is_preferred", True)):
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
                data.get("supplier_sku", ""),
                data.get("supplier_description", ""),
                data.get("price_component") or "unit",
                data.get("order_uom") or "pcs",
                bool(data.get("is_preferred", True)),
                data.get("notes", ""),
                company_id,
                item_supplier_id,
            ),
        ).fetchone()
        if not row:
            raise LibraryNotFound("Item supplier not found")

    def _upsert_supplier_item_cost_with_conn(
        self,
        conn,
        company_id: str,
        item_supplier_id: str,
        data: dict[str, Any],
        source_ref: str,
    ) -> str:
        old_row = conn.execute(
            """
            SELECT id::text, list_price_cents, discount_bps, unit_cost_cents, currency_code
            FROM supplier_item_costs
            WHERE company_id = %s
              AND item_supplier_id = %s
              AND effective_from <= now()
              AND (effective_to IS NULL OR effective_to > now())
            FOR UPDATE
            """,
            (company_id, item_supplier_id),
        ).fetchone()
        if old_row and _supplier_import_cost_values_match(old_row, data):
            return old_row["id"]

        replaces_id = None
        if old_row:
            old = conn.execute(
                """
                UPDATE supplier_item_costs
                SET effective_to = now()
                WHERE company_id = %s
                  AND item_supplier_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (company_id, item_supplier_id, old_row["id"]),
            ).fetchone()
            replaces_id = old["id"]

        new_row = conn.execute(
            """
            INSERT INTO supplier_item_costs
                (company_id, item_supplier_id, list_price_cents, discount_bps, unit_cost_cents,
                 currency_code, source, source_ref, replaces_id)
            VALUES (%s, %s, %s, %s, %s, %s, 'import', %s, %s)
            RETURNING id::text
            """,
            (
                company_id,
                item_supplier_id,
                data.get("list_price_cents", 0),
                data.get("discount_bps", 0),
                data["unit_cost_cents"],
                data.get("currency_code", "ZAR"),
                source_ref,
                replaces_id,
            ),
        ).fetchone()
        return new_row["id"]

    def _apply_price_list_item_import(
        self,
        conn,
        company_id: str,
        row: dict[str, Any],
        existing: dict[str, Any] | None,
    ) -> str:
        data = _clean_payload(row["payload"])
        if row["status"] == "create":
            target = self._create_price_list_item_with_conn(conn, company_id, data)
        else:
            target = self._update_price_list_item_with_conn(conn, company_id, existing["id"], data)
        return target["id"]

    def _create_price_list_item_with_conn(self, conn, company_id: str, data: dict[str, Any]) -> dict:
        row = conn.execute(
            """
            INSERT INTO price_list_items
                (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                 uom, unit_price_cents, source_supplier_item_cost_id, cost_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text
            """,
            (
                company_id,
                data["price_list_id"],
                data["item_type"],
                data.get("item_ref_id") or None,
                data["item_key"],
                data["price_component"],
                data["uom"],
                data["unit_price_cents"],
                data.get("source_supplier_item_cost_id"),
                data.get("cost_source", "import"),
            ),
        ).fetchone()
        return self._get_price_list_item_with_conn(conn, company_id, data["price_list_id"], row["id"])

    def _update_price_list_item_with_conn(self, conn, company_id: str, item_id: str, data: dict[str, Any]) -> dict:
        old_row = conn.execute(
            f"""
            SELECT {PRICE_LIST_ITEM_CONFIG.select_clause}
            FROM price_list_items
            WHERE company_id = %s
              AND price_list_id = %s
              AND id = %s
              AND effective_from <= now()
              AND (effective_to IS NULL OR effective_to > now())
            FOR UPDATE
            """,
            (company_id, data["price_list_id"], item_id),
        ).fetchone()
        if not old_row:
            raise LibraryNotFound("Price list item not found")
        conn.execute(
            """
            UPDATE price_list_items
            SET effective_to = now()
            WHERE company_id = %s
              AND price_list_id = %s
              AND id = %s
            """,
            (company_id, data["price_list_id"], item_id),
        )
        new_row = conn.execute(
            """
            INSERT INTO price_list_items
                (company_id, price_list_id, item_type, item_ref_id, item_key, price_component,
                 uom, unit_price_cents, source_supplier_item_cost_id, cost_source, replaces_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text
            """,
            (
                company_id,
                data["price_list_id"],
                data["item_type"],
                data.get("item_ref_id") or None,
                data["item_key"],
                data["price_component"],
                data["uom"],
                data["unit_price_cents"],
                data.get("source_supplier_item_cost_id"),
                data.get("cost_source", "import"),
                old_row["id"],
            ),
        ).fetchone()
        return self._get_price_list_item_with_conn(conn, company_id, data["price_list_id"], new_row["id"])

    def _get_price_list_item_with_conn(self, conn, company_id: str, price_list_id: str, item_id: str) -> dict:
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
        data["supplier_sku"] = str(data.get("supplier_sku") or "").strip()
        data["supplier_description"] = str(data.get("supplier_description") or "").strip()
        data["notes"] = str(data.get("notes") or "").strip()
        data["is_preferred"] = bool(data.get("is_preferred", False))
        item_row = self._ensure_price_item_reference(company_id, item_type, data["item_ref_id"])
        _normalize_pricing_fields_for_library(
            data,
            item_type=item_type,
            uom_field="order_uom",
            default_uom="pcs",
            board_costing_mode=item_row.get("costing_mode"),
        )
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

    def _fetch_supplier_generation_rows(
        self,
        conn,
        company_id: str,
        item_types: list[str],
        as_of: datetime | None = None,
    ) -> list[dict]:
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
             AND cost.effective_from <= COALESCE(%s, now())
             AND (cost.effective_to IS NULL OR cost.effective_to > COALESCE(%s, now()))
            WHERE {where_clause}
            ORDER BY item.item_type ASC, item.item_ref_id ASC, item.price_component ASC, item.is_preferred DESC
            """,
            [as_of, as_of, *values],
        ).fetchall()

    def _normalize_price_item_payload(self, company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = _clean_payload(payload)
        item_type = str(data.get("item_type") or "").strip().lower()
        item_ref_id = str(data.get("item_ref_id") or "").strip()
        item_key = str(data.get("item_key") or "").strip()
        source_supplier_item_cost_id = str(data.get("source_supplier_item_cost_id") or "").strip()
        if item_type not in PRICE_ITEM_TYPE_TABLES:
            raise LibraryValidationError(f"Unsupported item_type: {item_type}")
        data["item_type"] = item_type
        _normalize_pricing_fields_for_library(
            data,
            item_type=item_type,
            uom_field="uom",
            default_uom=None,
        )
        data["cost_source"] = str(data.get("cost_source") or "manual").strip().lower()
        data["source_supplier_item_cost_id"] = source_supplier_item_cost_id or None
        if data["source_supplier_item_cost_id"]:
            self._ensure_supplier_item_cost(company_id, data["source_supplier_item_cost_id"])

        if item_ref_id:
            item_row = self._ensure_price_item_reference(company_id, item_type, item_ref_id)
            _normalize_pricing_fields_for_library(
                data,
                item_type=item_type,
                uom_field="uom",
                default_uom=None,
                board_costing_mode=item_row.get("costing_mode"),
            )
            data["item_ref_id"] = item_ref_id
            data["item_key"] = f"{item_type}::{item_ref_id}"
            return data

        if not item_key:
            raise LibraryValidationError("Either item_ref_id or item_key is required")

        data["item_key"] = item_key
        derived_ref = _try_extract_ref_id(item_type, item_key)
        if derived_ref:
            item_row = self._ensure_price_item_reference(company_id, item_type, derived_ref)
            _normalize_pricing_fields_for_library(
                data,
                item_type=item_type,
                uom_field="uom",
                default_uom=None,
                board_costing_mode=item_row.get("costing_mode"),
            )
            data["item_ref_id"] = derived_ref

        return data

    def _ensure_price_item_reference(self, company_id: str, item_type: str, item_ref_id: str) -> dict[str, Any]:
        table = PRICE_ITEM_TYPE_TABLES.get(item_type)
        if not table:
            raise LibraryValidationError(f"Unsupported item_type: {item_type}")
        select_clause = "id::text, costing_mode" if table == "board_types" else "id::text"

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {select_clause}
                FROM {table}
                WHERE company_id = %s
                  AND id = %s
                """,
                (company_id, item_ref_id),
            ).fetchone()
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for library database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _get_or_create_brand(self, company_id: str, name: str) -> str:
        clean_name = _clean(name)
        with self._connect() as conn:
            row = self._get_or_create_brand_with_conn(conn, company_id, clean_name)
        return row["id"]

    def _get_or_create_brand_with_conn(self, conn, company_id: str, name: str) -> dict:
        clean_name = _clean(name)
        return conn.execute(
            """
            INSERT INTO brands (company_id, name)
            VALUES (%s, %s)
            ON CONFLICT (company_id, name) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id::text
            """,
            (company_id, clean_name),
        ).fetchone()


def _coerce_effective_datetime(value: Any | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _coerce_effective_date(value: Any | None) -> date:
    if value is None:
        return datetime.now(UTC).date()
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=UTC)).date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _effective_status(effective_from: Any, effective_to: Any | None, as_of: Any | None = None) -> str:
    as_of_dt = _coerce_effective_datetime(as_of)
    start = _coerce_effective_datetime(effective_from)
    end = _coerce_effective_datetime(effective_to) if effective_to is not None else None
    if start > as_of_dt:
        return "future"
    if end is not None and end <= as_of_dt:
        return "retired"
    return "current"


def _with_effective_status(row: dict[str, Any], as_of: Any | None = None) -> dict[str, Any]:
    result = dict(row)
    status = _effective_status(result["effective_from"], result.get("effective_to"), as_of)
    result["effective_status"] = status
    result["is_current"] = status == "current"
    result["is_active"] = result.get("effective_to") is None
    return result


def _with_effective_statuses(rows: list[dict[str, Any]], as_of: Any | None = None) -> list[dict[str, Any]]:
    return [_with_effective_status(row, as_of) for row in rows]


def _search_pattern(search: str | None) -> str | None:
    value = str(search or "").strip()
    if not value:
        return None
    return f"%{value}%"


def _recent_cutoff(recent_days: int | None) -> datetime | None:
    if recent_days is None:
        return None
    return datetime.now(UTC) - timedelta(days=int(recent_days))


def _bulk_update_response(
    *,
    resource: str,
    confirm: bool,
    requested_count: int,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    updated_count = sum(1 for row in rows if row["status"] == "updated")
    failed_count = sum(1 for row in rows if row["status"] == "failed")
    matched_count = len(rows) - failed_count
    if failed_count:
        summary_message = (
            f"{updated_count} row{'s' if updated_count != 1 else ''} updated; "
            f"{failed_count} row{'s' if failed_count != 1 else ''} need attention."
            if confirm
            else f"{matched_count} row{'s' if matched_count != 1 else ''} ready; {failed_count} cannot be edited."
        )
    elif confirm:
        summary_message = f"Updated {updated_count} selected row{'s' if updated_count != 1 else ''}."
    else:
        summary_message = f"Preview ready for {matched_count} selected row{'s' if matched_count != 1 else ''}."
    return {
        "resource": resource,
        "confirm": confirm,
        "requested_count": requested_count,
        "matched_count": matched_count,
        "updated_count": updated_count,
        "failed_count": failed_count,
        "summary_message": summary_message,
        "rows": rows,
    }


def _catalog_bulk_label(resource: str, row: dict[str, Any]) -> str:
    if resource == "boards":
        return f"{row['brand']} {row['material']} {row['thickness']}mm"
    if resource == "slides":
        return f"{row['brand']} {row['model']} {row['length']}mm"
    if resource == "hinges":
        return f"{row['brand']} {row['model']} {row['opening_angle_deg']}deg"
    if resource == "handles":
        return f"{row['name']} ({row.get('supplier_name') or 'No supplier'})"
    if resource == "extras":
        return f"{row['name']} ({row.get('category_name') or 'Extra'})"
    if resource == "suppliers":
        return str(row["name"])
    return str(row.get("id") or "")


def _catalog_bulk_payload(resource: str, row: dict[str, Any]) -> dict[str, Any]:
    if resource == "extras":
        fields = ("name", "category_id", "supplier", "code", "notes")
    else:
        config = CATALOG_BULK_CONFIGS.get(resource)
        if not config:
            raise LibraryValidationError("Unsupported catalog bulk resource")
        fields = config.fields
    return {field: row.get(field) for field in fields}


def _price_bulk_updates(payload: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if payload.get("unit_price_cents") is not None:
        updates["unit_price_cents"] = int(payload["unit_price_cents"])
    if payload.get("uom") is not None:
        try:
            updates["uom"] = normalize_order_uom(payload["uom"], field="uom")
        except PricingFieldValidationError as exc:
            raise _pricing_library_validation_error(exc) from exc
    if payload.get("cost_source") is not None:
        cost_source = str(payload["cost_source"]).strip().lower()
        if cost_source not in {"manual", "override"}:
            raise LibraryValidationError("Bulk price edits can only set manual or override cost sources")
        updates["cost_source"] = cost_source
    return updates


def _price_bulk_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_type": row["item_type"],
        "item_ref_id": row.get("item_ref_id"),
        "item_key": row["item_key"],
        "price_component": row["price_component"],
        "uom": row["uom"],
        "unit_price_cents": row["unit_price_cents"],
        "source_supplier_item_cost_id": row.get("source_supplier_item_cost_id"),
        "cost_source": row["cost_source"],
    }


def _price_bulk_label(row: dict[str, Any]) -> str:
    return f"{row['item_key']} {row['price_component']} ({row['uom']})"


def _build_setup_checklist(summary: dict[str, Any]) -> dict[str, Any]:
    board_count = _summary_count(summary, "board_count")
    slide_count = _summary_count(summary, "slide_count")
    hinge_count = _summary_count(summary, "hinge_count")
    handle_count = _summary_count(summary, "handle_count")
    extra_category_count = _summary_count(summary, "extra_category_count")
    extra_count = _summary_count(summary, "extra_count")
    supplier_count = _summary_count(summary, "supplier_count")
    active_supplier_cost_count = _summary_count(summary, "active_supplier_cost_count")
    active_price_list_count = _summary_count(summary, "active_price_list_count")
    active_price_count = _summary_count(summary, "active_price_count")
    pricing_settings_count = _summary_count(summary, "pricing_settings_count")
    quote_count = _summary_count(summary, "quote_count")
    quote_with_defaults_count = _summary_count(summary, "quote_with_defaults_count")
    vat_rate_bps = int(summary.get("vat_rate_bps") or DEFAULT_VAT_RATE_BPS)
    default_markup_bps = int(summary.get("default_markup_bps") or DEFAULT_MARKUP_BPS)

    items: list[dict[str, Any]] = []

    if board_count == 0:
        items.append(
            _setup_item(
                "boards",
                "Boards",
                "missing",
                board_count,
                "Add carcass, door, and visible panel boards before quoting real jobs.",
                "Add boards",
                "boards",
            )
        )
    elif board_count < 3:
        items.append(
            _setup_item(
                "boards",
                "Boards",
                "warning",
                board_count,
                "You have some boards, but the Smith Kitchen setup needs separate carcass, door, and visible panel choices.",
                "Review boards",
                "boards",
            )
        )
    else:
        items.append(
            _setup_item(
                "boards",
                "Boards",
                "complete",
                board_count,
                "Board choices are available for carcasses, doors, and panels.",
                "Review boards",
                "boards",
            )
        )

    items.append(
        _setup_item(
            "slides",
            "Drawer slides",
            "complete" if slide_count > 0 else "missing",
            slide_count,
            "Drawer slide choices are ready." if slide_count > 0 else "Add at least one drawer slide pair for drawer units.",
            "Review slides" if slide_count > 0 else "Add slides",
            "slides",
        )
    )
    items.append(
        _setup_item(
            "hinges",
            "Hinges",
            "complete" if hinge_count > 0 else "missing",
            hinge_count,
            "Hinge choices are ready." if hinge_count > 0 else "Add at least one concealed hinge for door units.",
            "Review hinges" if hinge_count > 0 else "Add hinges",
            "hinges",
        )
    )

    if handle_count == 0:
        handle_status = "missing"
        handle_message = "Add handles before setting base, wall, tall, and drawer handle defaults."
        handle_action = "Add handles"
    elif handle_count < 4:
        handle_status = "warning"
        handle_message = "You have handles, but the Smith Kitchen setup expects base, wall, tall, and drawer handle choices."
        handle_action = "Review handles"
    else:
        handle_status = "complete"
        handle_message = "Handle choices are available for the main cabinet types."
        handle_action = "Review handles"
    items.append(_setup_item("handles", "Handles", handle_status, handle_count, handle_message, handle_action, "handles"))

    if extra_count > 0:
        extra_status = "complete"
        extra_message = "Extras are available for delivery, installation, appliances, or other job charges."
        extra_action = "Review extras"
        extra_target = "extras"
    elif extra_category_count > 0:
        extra_status = "warning"
        extra_message = "Extra categories exist, but no extras are ready to add to a quote yet."
        extra_action = "Add extras"
        extra_target = "extras"
    else:
        extra_status = "missing"
        extra_message = "Add an extra category and at least one extra for delivery, installation, or other job charges."
        extra_action = "Add extra categories"
        extra_target = "extra-categories"
    items.append(_setup_item("extras", "Extras", extra_status, extra_count, extra_message, extra_action, extra_target))

    if supplier_count == 0:
        supplier_status = "missing"
        supplier_message = "Add suppliers so price refreshes can show where costs came from."
        supplier_action = "Add suppliers"
    elif active_supplier_cost_count == 0:
        supplier_status = "warning"
        supplier_message = "Suppliers exist, but no active supplier costs are linked to catalog items yet."
        supplier_action = "Add supplier costs"
    else:
        supplier_status = "complete"
        supplier_message = "Supplier costs are linked and ready to feed price lists."
        supplier_action = "Review suppliers"
    items.append(
        _setup_item(
            "supplier-costs",
            "Supplier cost sources",
            supplier_status,
            active_supplier_cost_count,
            supplier_message,
            supplier_action,
            "suppliers",
        )
    )

    if active_price_list_count == 0:
        price_status = "missing"
        price_message = "Create one active price list before relying on quote totals."
        price_action = "Create price list"
    elif active_price_count == 0:
        price_status = "warning"
        price_message = "An active price list exists, but it does not have active prices yet."
        price_action = "Add prices"
    else:
        price_status = "complete"
        price_message = "An active price list has prices available for new and recalculated quotes."
        price_action = "Review prices"
    items.append(
        _setup_item(
            "active-price-list",
            "Active price list",
            price_status,
            active_price_count,
            price_message,
            price_action,
            "pricing",
        )
    )

    pricing_status = "complete" if pricing_settings_count > 0 else "warning"
    pricing_message = (
        f"Company pricing settings are saved with {vat_rate_bps / 100:.2f}% VAT and {default_markup_bps / 100:.2f}% default markup."
        if pricing_settings_count > 0
        else f"CoreQuote can use defaults ({DEFAULT_VAT_RATE_BPS / 100:.2f}% VAT and {DEFAULT_MARKUP_BPS / 100:.2f}% markup), but review them before a real quote."
    )
    items.append(
        _setup_item(
            "pricing-settings",
            "VAT and markups",
            pricing_status,
            pricing_settings_count,
            pricing_message,
            "Review pricing settings",
            "pricing",
        )
    )

    if quote_with_defaults_count > 0:
        quote_status = "complete"
        quote_message = "At least one quote has board, slide, hinge, and handle defaults selected."
        quote_action = "Review quotes"
    elif quote_count > 0:
        quote_status = "warning"
        quote_message = "Quotes exist, but none has all the main board and hardware defaults selected yet."
        quote_action = "Set quote defaults"
    else:
        quote_status = "action_needed"
        quote_message = "Create a quote and choose default boards, slides, hinges, and handles before the first real job."
        quote_action = "Open projects"
    items.append(
        _setup_item(
            "quote-defaults",
            "Quote defaults",
            quote_status,
            quote_with_defaults_count,
            quote_message,
            quote_action,
            "projects",
        )
    )

    complete_count = sum(1 for item in items if item["status"] == "complete")
    total_count = len(items)
    status = "ready" if complete_count == total_count else "needs_attention"
    remaining_count = total_count - complete_count
    return {
        "status": status,
        "summary_title": "Library setup is ready" if status == "ready" else "Library setup needs attention",
        "summary_message": (
            "Boards, hardware, supplier costs, prices, settings, and quote defaults are ready for real quoting."
            if status == "ready"
            else f"{remaining_count} setup item{'s' if remaining_count != 1 else ''} still need attention before the Smith Kitchen library refresh is fully ready."
        ),
        "complete_count": complete_count,
        "total_count": total_count,
        "items": items,
    }


def _setup_item(
    item_id: str,
    label: str,
    status: str,
    count: int,
    message: str,
    action_label: str,
    action_target: str,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "label": label,
        "status": status,
        "count": count,
        "message": message,
        "action_label": action_label,
        "action_target": action_target,
    }


def _price_list_coverage_rows(conn, company_id: str, price_list_id: str) -> list[dict[str, Any]]:
    active_quote_statuses = ["draft", "ready", "sent", "accepted"]
    profile_handle_keys = list(PROFILE_HANDLE_ID_KEYS)
    return conn.execute(
        """
        WITH active_quotes AS (
            SELECT
                q.id::text AS quote_id,
                q.company_id::text AS company_id,
                q.project_id::text AS project_id,
                p.name AS project_name,
                q.name AS quote_name,
                q.quote_number,
                q.revision,
                q.status AS quote_status,
                q.default_carcass_board_type_id::text AS default_carcass_board_type_id,
                q.default_door_board_type_id::text AS default_door_board_type_id,
                q.default_panel_board_type_id::text AS default_panel_board_type_id,
                q.default_slide_id::text AS default_slide_id,
                q.default_hinge_id::text AS default_hinge_id,
                q.default_base_handle_id::text AS default_base_handle_id,
                q.default_wall_handle_id::text AS default_wall_handle_id,
                q.default_tall_handle_id::text AS default_tall_handle_id,
                q.default_drawer_handle_id::text AS default_drawer_handle_id
            FROM quotes q
            JOIN projects p
              ON p.company_id = q.company_id
             AND p.id = q.project_id
            WHERE q.company_id = %s
              AND q.status = ANY(%s)
        ),
        required_refs AS (
            SELECT *, 'board' AS item_type, default_carcass_board_type_id AS item_ref_id, 'Quote carcass default' AS usage_label
            FROM active_quotes
            WHERE default_carcass_board_type_id IS NOT NULL
            UNION ALL
            SELECT *, 'board' AS item_type, default_door_board_type_id AS item_ref_id, 'Quote door/drawer default' AS usage_label
            FROM active_quotes
            WHERE default_door_board_type_id IS NOT NULL
            UNION ALL
            SELECT *, 'board' AS item_type, default_panel_board_type_id AS item_ref_id, 'Quote visible panel default' AS usage_label
            FROM active_quotes
            WHERE default_panel_board_type_id IS NOT NULL
            UNION ALL
            SELECT *, 'slide' AS item_type, default_slide_id AS item_ref_id, 'Quote drawer hardware default' AS usage_label
            FROM active_quotes
            WHERE default_slide_id IS NOT NULL
            UNION ALL
            SELECT *, 'hinge' AS item_type, default_hinge_id AS item_ref_id, 'Quote hinge default' AS usage_label
            FROM active_quotes
            WHERE default_hinge_id IS NOT NULL
            UNION ALL
            SELECT *, 'handle' AS item_type, default_base_handle_id AS item_ref_id, 'Quote base handle default' AS usage_label
            FROM active_quotes
            WHERE default_base_handle_id IS NOT NULL
            UNION ALL
            SELECT *, 'handle' AS item_type, default_wall_handle_id AS item_ref_id, 'Quote wall handle default' AS usage_label
            FROM active_quotes
            WHERE default_wall_handle_id IS NOT NULL
            UNION ALL
            SELECT *, 'handle' AS item_type, default_tall_handle_id AS item_ref_id, 'Quote tall handle default' AS usage_label
            FROM active_quotes
            WHERE default_tall_handle_id IS NOT NULL
            UNION ALL
            SELECT *, 'handle' AS item_type, default_drawer_handle_id AS item_ref_id, 'Quote drawer handle default' AS usage_label
            FROM active_quotes
            WHERE default_drawer_handle_id IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'board' AS item_type,
                COALESCE(u.carcass_board_type_id::text, q.default_carcass_board_type_id) AS item_ref_id,
                'Unit ' || u.unit_number::text || ' carcass board' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            WHERE COALESCE(u.carcass_board_type_id::text, q.default_carcass_board_type_id) IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'board' AS item_type,
                COALESCE(u.door_board_type_id::text, q.default_door_board_type_id) AS item_ref_id,
                'Unit ' || u.unit_number::text || ' door/drawer board' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            WHERE COALESCE(u.door_board_type_id::text, q.default_door_board_type_id) IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'slide' AS item_type,
                COALESCE(NULLIF(u.extra_params->>'slide_id', ''), q.default_slide_id) AS item_ref_id,
                'Unit ' || u.unit_number::text || ' drawer hardware' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            WHERE COALESCE(NULLIF(u.extra_params->>'slide_id', ''), q.default_slide_id) IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'hinge' AS item_type,
                COALESCE(NULLIF(u.extra_params->>'hinge_id', ''), q.default_hinge_id) AS item_ref_id,
                'Unit ' || u.unit_number::text || ' hinge' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            WHERE COALESCE(NULLIF(u.extra_params->>'hinge_id', ''), q.default_hinge_id) IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'handle' AS item_type,
                COALESCE(
                    NULLIF(u.extra_params->>'handle_id', ''),
                    CASE
                        WHEN lower(u.unit_type_key) LIKE '%%draw%%' THEN q.default_drawer_handle_id
                        WHEN lower(u.unit_type_key) LIKE '%%wall%%' THEN q.default_wall_handle_id
                        WHEN lower(u.unit_type_key) LIKE '%%tall%%' THEN q.default_tall_handle_id
                        ELSE q.default_base_handle_id
                    END
                ) AS item_ref_id,
                'Unit ' || u.unit_number::text || ' handle' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            WHERE COALESCE(
                NULLIF(u.extra_params->>'handle_id', ''),
                CASE
                    WHEN lower(u.unit_type_key) LIKE '%%draw%%' THEN q.default_drawer_handle_id
                    WHEN lower(u.unit_type_key) LIKE '%%wall%%' THEN q.default_wall_handle_id
                    WHEN lower(u.unit_type_key) LIKE '%%tall%%' THEN q.default_tall_handle_id
                    ELSE q.default_base_handle_id
                END
            ) IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'handle' AS item_type,
                NULLIF(profile.value, '') AS item_ref_id,
                'Unit ' || u.unit_number::text || ' profile handle' AS usage_label
            FROM quote_units u
            JOIN active_quotes q
              ON q.company_id = u.company_id::text
             AND q.quote_id = u.quote_id::text
            JOIN LATERAL jsonb_each_text(u.extra_params) profile(key, value)
              ON profile.key = ANY(%s)
            WHERE NULLIF(profile.value, '') IS NOT NULL
            UNION ALL
            SELECT
                q.*,
                'extra' AS item_type,
                qe.extra_id::text AS item_ref_id,
                'Quote extra' AS usage_label
            FROM quote_extras qe
            JOIN active_quotes q
              ON q.company_id = qe.company_id::text
             AND q.quote_id = qe.quote_id::text
        ),
        catalog_refs AS (
            SELECT
                refs.project_id,
                refs.project_name,
                refs.quote_id,
                refs.quote_name,
                refs.quote_number,
                refs.revision,
                refs.quote_status,
                refs.usage_label,
                refs.item_type,
                refs.item_ref_id,
                refs.item_type || '::' || refs.item_ref_id AS item_key,
                CASE
                    WHEN refs.item_type = 'board' THEN NULLIF(trim(concat_ws(' ', board.brand, board.material, board.thickness::text || 'mm')), '')
                    WHEN refs.item_type = 'slide' THEN NULLIF(trim(concat_ws(' ', slide.brand, slide.model, CASE WHEN length(trim(slide.code)) > 0 THEN '(' || slide.code || ')' END)), '')
                    WHEN refs.item_type = 'hinge' THEN NULLIF(trim(concat_ws(' ', hinge.brand, hinge.model, CASE WHEN length(trim(hinge.code)) > 0 THEN '(' || hinge.code || ')' END)), '')
                    WHEN refs.item_type = 'handle' THEN NULLIF(trim(CASE WHEN length(trim(COALESCE(handle_supplier.name, ''))) > 0 THEN handle.name || ' (' || handle_supplier.name || ')' ELSE handle.name END), '')
                    WHEN refs.item_type = 'extra' THEN NULLIF(trim(CASE WHEN length(trim(COALESCE(category.name, ''))) > 0 THEN extra.name || ' (' || category.name || ')' ELSE extra.name END), '')
                END AS item_name,
                CASE
                    WHEN refs.item_type = 'board' AND board.costing_mode = 'sqm' THEN 'sqm'
                    WHEN refs.item_type = 'board' THEN 'sheet'
                    ELSE 'unit'
                END AS price_component,
                CASE
                    WHEN refs.item_type = 'board' AND board.costing_mode = 'sqm' THEN 'm2'
                    WHEN refs.item_type = 'board' THEN 'sheet'
                    WHEN refs.item_type = 'slide' THEN 'pairs'
                    ELSE 'pcs'
                END AS uom
            FROM required_refs refs
            LEFT JOIN board_types board
              ON refs.item_type = 'board'
             AND board.company_id = refs.company_id::uuid
             AND board.id::text = refs.item_ref_id
            LEFT JOIN slides slide
              ON refs.item_type = 'slide'
             AND slide.company_id = refs.company_id::uuid
             AND slide.id::text = refs.item_ref_id
            LEFT JOIN hinges hinge
              ON refs.item_type = 'hinge'
             AND hinge.company_id = refs.company_id::uuid
             AND hinge.id::text = refs.item_ref_id
            LEFT JOIN handles handle
              ON refs.item_type = 'handle'
             AND handle.company_id = refs.company_id::uuid
             AND handle.id::text = refs.item_ref_id
            LEFT JOIN suppliers handle_supplier
              ON handle_supplier.company_id = handle.company_id
             AND handle_supplier.id = handle.supplier_id
            LEFT JOIN extras extra
              ON refs.item_type = 'extra'
             AND extra.company_id = refs.company_id::uuid
             AND extra.id::text = refs.item_ref_id
            LEFT JOIN extra_categories category
              ON category.company_id = extra.company_id
             AND category.id = extra.category_id
            WHERE refs.item_ref_id IS NOT NULL
              AND refs.item_ref_id <> ''
        )
        SELECT
            refs.*,
            price.id::text AS active_price_list_item_id,
            price.unit_price_cents,
            price.uom AS active_price_uom,
            price.cost_source,
            price.source_supplier_item_cost_id::text,
            supplier.item_supplier_id,
            supplier.supplier_item_cost_id,
            supplier.unit_cost_cents AS supplier_unit_cost_cents,
            supplier.order_uom AS supplier_order_uom
        FROM catalog_refs refs
        LEFT JOIN LATERAL (
            SELECT
                item.id,
                item.unit_price_cents,
                item.uom,
                item.cost_source,
                item.source_supplier_item_cost_id
            FROM price_list_items item
            WHERE item.company_id = %s
              AND item.price_list_id = %s
              AND item.item_type = refs.item_type
              AND item.item_key = refs.item_key
              AND item.price_component = refs.price_component
              AND item.effective_from <= now()
              AND (item.effective_to IS NULL OR item.effective_to > now())
            ORDER BY item.effective_from DESC, item.id DESC
            LIMIT 1
        ) price ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                item.id::text AS item_supplier_id,
                cost.id::text AS supplier_item_cost_id,
                cost.unit_cost_cents,
                item.order_uom
            FROM item_suppliers item
            JOIN supplier_item_costs cost
              ON cost.company_id = item.company_id
             AND cost.item_supplier_id = item.id
             AND cost.effective_from <= now()
             AND (cost.effective_to IS NULL OR cost.effective_to > now())
            WHERE item.company_id = %s
              AND item.item_type = refs.item_type
              AND item.item_ref_id::text = refs.item_ref_id
              AND item.price_component = refs.price_component
            ORDER BY item.is_preferred DESC, cost.unit_cost_cents ASC, item.id ASC
            LIMIT 1
        ) supplier ON TRUE
        WHERE refs.item_name IS NOT NULL
          AND refs.item_name <> ''
        ORDER BY refs.item_type ASC, refs.item_name ASC, refs.price_component ASC, refs.project_name ASC, refs.quote_number ASC, refs.usage_label ASC
        """,
        (company_id, active_quote_statuses, profile_handle_keys, company_id, price_list_id, company_id),
    ).fetchall()


def _build_price_list_coverage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    quote_contexts: dict[tuple[str, str, str], dict[tuple[str, str, str], dict[str, Any]]] = {}

    for row in rows:
        key = (str(row["item_type"]), str(row["item_ref_id"]), str(row["price_component"]))
        coverage = grouped.get(key)
        if coverage is None:
            has_current_price = bool(row.get("active_price_list_item_id"))
            cost_source = str(row.get("cost_source") or "").strip().lower() or None
            has_supplier_cost = bool(row.get("supplier_item_cost_id"))
            is_stale = _coverage_row_is_stale(row, has_current_price=has_current_price, cost_source=cost_source)
            is_override = has_current_price and cost_source in {"manual", "override"}
            grouped[key] = {
                "item_type": row["item_type"],
                "item_type_label": _coverage_item_type_label(str(row["item_type"])),
                "item_ref_id": row["item_ref_id"],
                "item_key": row["item_key"],
                "item_name": row["item_name"],
                "price_component": row["price_component"],
                "component": _coverage_component_label(str(row["price_component"])),
                "uom": row.get("active_price_uom") or row["uom"],
                "status": _coverage_row_status(
                    has_current_price=has_current_price,
                    is_stale=is_stale,
                    is_override=is_override,
                ),
                "has_current_price": has_current_price,
                "active_price_list_item_id": row.get("active_price_list_item_id"),
                "unit_price_cents": row.get("unit_price_cents"),
                "cost_source": cost_source,
                "source_supplier_item_cost_id": row.get("source_supplier_item_cost_id"),
                "has_supplier_cost": has_supplier_cost,
                "active_supplier_item_id": row.get("item_supplier_id"),
                "active_supplier_item_cost_id": row.get("supplier_item_cost_id"),
                "supplier_unit_cost_cents": row.get("supplier_unit_cost_cents"),
                "supplier_order_uom": row.get("supplier_order_uom"),
                "quote_count": 0,
                "used_in": [],
            }
            quote_contexts[key] = {}

        context_key = (
            str(row["project_id"]),
            str(row["quote_id"]),
            str(row["usage_label"]),
        )
        quote_contexts[key][context_key] = {
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "quote_id": row["quote_id"],
            "quote_name": row["quote_name"],
            "quote_number": row["quote_number"],
            "revision": int(row["revision"]),
            "quote_status": row["quote_status"],
            "usage_label": row["usage_label"],
        }

    coverage_rows = []
    for key, coverage in grouped.items():
        contexts = sorted(
            quote_contexts[key].values(),
            key=lambda item: (str(item["project_name"]), str(item["quote_number"]), int(item["revision"]), str(item["usage_label"])),
        )
        coverage["used_in"] = contexts
        coverage["quote_count"] = len({context["quote_id"] for context in contexts})
        coverage_rows.append(coverage)

    return sorted(
        coverage_rows,
        key=lambda row: (
            _coverage_item_type_sort(str(row["item_type"])),
            str(row["item_name"]),
            str(row["price_component"]),
        ),
    )


def _price_coverage_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["item_type"]), []).append(row)
    return [
        {
            "item_type": item_type,
            "item_type_label": _coverage_item_type_label(item_type),
            **_price_coverage_counts(group_rows),
            "rows": group_rows,
        }
        for item_type, group_rows in sorted(grouped.items(), key=lambda item: _coverage_item_type_sort(item[0]))
    ]


def _price_coverage_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "used_count": len(rows),
        "covered_count": sum(1 for row in rows if row["has_current_price"]),
        "missing_count": sum(1 for row in rows if not row["has_current_price"]),
        "stale_count": sum(1 for row in rows if row["status"] == "stale"),
        "override_count": sum(1 for row in rows if row["status"] == "override"),
    }


def _coverage_row_is_stale(row: dict[str, Any], *, has_current_price: bool, cost_source: str | None) -> bool:
    if not has_current_price or cost_source != "supplier":
        return False
    if not row.get("supplier_item_cost_id"):
        return True
    return (
        str(row.get("source_supplier_item_cost_id") or "") != str(row.get("supplier_item_cost_id") or "")
        or int(row.get("unit_price_cents") or 0) != int(row.get("supplier_unit_cost_cents") or 0)
        or str(row.get("active_price_uom") or "") != str(row.get("supplier_order_uom") or "")
    )


def _coverage_row_status(*, has_current_price: bool, is_stale: bool, is_override: bool) -> str:
    if not has_current_price:
        return "missing"
    if is_stale:
        return "stale"
    if is_override:
        return "override"
    return "covered"


def _coverage_item_type_label(item_type: str) -> str:
    labels = {
        "board": "Board",
        "slide": "Drawer hardware",
        "hinge": "Hinge",
        "handle": "Handle",
        "extra": "Extra",
    }
    return labels.get(item_type, item_type.replace("_", " ").title())


def _coverage_component_label(price_component: str) -> str:
    labels = {
        "unit": "Unit price",
        "sqm": "Square metre price",
        "sheet": "Sheet price",
        "edging_m": "Edging per metre",
        "labour_board": "Labour per board",
    }
    return labels.get(price_component, price_component.replace("_", " ").title())


def _coverage_item_type_sort(item_type: str) -> int:
    order = {"board": 10, "slide": 20, "hinge": 30, "handle": 40, "extra": 50}
    return order.get(item_type, 999)


def _summary_count(summary: dict[str, Any], key: str) -> int:
    return int(summary.get(key) or 0)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _db_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return value


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _extra_supplier_values(conn, company_id: str, payload: dict[str, Any]) -> tuple[str | None, str]:
    supplier_id = payload.get("supplier_id")
    if supplier_id in (None, ""):
        return None, ""
    row = conn.execute(
        """
        SELECT name
        FROM suppliers
        WHERE company_id = %s
          AND id = %s
        """,
        (company_id, supplier_id),
    ).fetchone()
    if not row:
        raise LibraryValidationError("Supplier must be an existing company supplier or null")
    return str(supplier_id), str(row["name"] or "").strip()


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = {key: _clean(value) for key, value in payload.items()}
    if "costing_mode" in data:
        data["costing_mode"] = str(data["costing_mode"] or "sheet").strip().lower()
    if "grain_policy" in data:
        data["grain_policy"] = str(data["grain_policy"] or "required").strip().lower()
        if data["grain_policy"] not in GRAIN_POLICY_VALUES:
            raise LibraryValidationError("Grain policy must be none, optional, or required")
    if "mount_type" in data:
        data["mount_type"] = str(data["mount_type"] or "side_mount").strip().lower()
        if data["mount_type"] not in {"side_mount", "undermount", "metal_system", "custom"}:
            raise LibraryValidationError("Mount type must be side_mount, undermount, metal_system, or custom")
    if "price_component" in data:
        data["price_component"] = str(data["price_component"] or "unit").strip().lower()
    if "cost_source" in data:
        data["cost_source"] = str(data["cost_source"] or "manual").strip().lower()
    if "currency_code" in data:
        data["currency_code"] = str(data["currency_code"] or "ZAR").strip().upper()
    if "drawer_system_kind" in data:
        data["drawer_system_kind"] = str(data["drawer_system_kind"] or "conventional").strip().lower()
        if data["drawer_system_kind"] not in {"conventional", "metal", "custom"}:
            raise LibraryValidationError("Drawer system kind must be conventional, metal, or custom")
    if "drawer_system_config" in data:
        config = data.get("drawer_system_config") or {}
        if not isinstance(config, dict):
            raise LibraryValidationError("Drawer system config must be an object")
        data["drawer_system_config"] = config
    if "accessory_config" in data:
        config = data.get("accessory_config") or {}
        if not isinstance(config, dict):
            raise LibraryValidationError("Accessory config must be an object")
        data["accessory_config"] = config
    if data.get("item_ref_id") == "":
        data["item_ref_id"] = None
    if data.get("supplier_id") == "":
        data["supplier_id"] = None
    if data.get("source_supplier_item_cost_id") == "":
        data["source_supplier_item_cost_id"] = None
    return data


def _pricing_library_validation_error(error: PricingFieldValidationError) -> LibraryValidationError:
    return LibraryValidationError(str(error), field_errors=pricing_issues_as_fastapi_errors(error))


def _normalize_pricing_fields_for_library(
    data: dict[str, Any],
    *,
    item_type: str,
    uom_field: str,
    default_uom: str | None,
    board_costing_mode: str | None = None,
) -> None:
    try:
        data["price_component"] = normalize_price_component(data.get("price_component"), default="unit")
        data[uom_field] = normalize_order_uom(data.get(uom_field), field=uom_field, default=default_uom)
        validate_pricing_combination(
            item_type=item_type,
            price_component=data["price_component"],
            uom=data[uom_field],
            uom_field=uom_field,
            board_costing_mode=board_costing_mode,
        )
    except PricingFieldValidationError as exc:
        raise _pricing_library_validation_error(exc) from exc


def build_slide_range_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = _clean_payload(payload)
    brand = str(data["brand"]).strip()
    product_family = str(data["product_family"]).strip()
    mount_type = str(data.get("mount_type") or "side_mount").strip().lower()
    drawer_system_kind = str(data.get("drawer_system_kind") or ("metal" if mount_type == "metal_system" else "conventional")).strip().lower()
    if mount_type == "metal_system":
        drawer_system_kind = "metal"
    elif mount_type == "custom" and drawer_system_kind == "conventional":
        drawer_system_kind = "custom"
    code_pattern = str(data.get("code_pattern") or "").strip()
    side_clearance_total = _non_negative_int(data.get("side_clearance_total"), 0)
    default_depth_deduction = _non_negative_int(data.get("drawer_depth_deduction_mm"), 0)
    configured_box_width_deduction = _non_negative_int(data.get("box_width_deduction_mm"), 0)
    default_box_width_deduction = configured_box_width_deduction if configured_box_width_deduction > 0 else 2 * side_clearance_total
    default_required_depth = _non_negative_int(data.get("required_depth_mm"), 0)
    side_height_uplift = _non_negative_int(data.get("side_height_uplift"), 0)
    drawer_system_config = data.get("drawer_system_config") or {}
    accessory_config = data.get("accessory_config") or {}
    if not isinstance(drawer_system_config, dict):
        raise LibraryValidationError("Drawer system config must be an object")
    if not isinstance(accessory_config, dict):
        raise LibraryValidationError("Accessory config must be an object")

    payloads: list[dict[str, Any]] = []
    for raw_length in data.get("lengths") or []:
        if not isinstance(raw_length, dict):
            raise LibraryValidationError("Each range length must be an object")
        length = _non_negative_int(raw_length.get("length"), 0)
        if length <= 0:
            raise LibraryValidationError("Runner lengths must be positive")
        depth_deduction = _non_negative_int(raw_length.get("drawer_depth_deduction_mm"), default_depth_deduction)
        side_length = _non_negative_int(raw_length.get("side_length"), max(0, length - depth_deduction))
        configured_row_width_deduction = _non_negative_int(raw_length.get("box_width_deduction_mm"), 0)
        box_width_deduction = configured_row_width_deduction if configured_row_width_deduction > 0 else default_box_width_deduction
        required_depth = _non_negative_int(raw_length.get("required_depth_mm"), default_required_depth or length)
        code = str(raw_length.get("code") or "").strip() or _range_code(code_pattern, length)
        payloads.append(
            {
                "brand": brand,
                "model": f"{product_family} {length}",
                "code": code,
                "length": length,
                "side_length": side_length,
                "side_clearance_total": side_clearance_total,
                "side_height_uplift": side_height_uplift,
                "mount_type": mount_type,
                "product_family": product_family,
                "required_depth_mm": required_depth,
                "drawer_depth_deduction_mm": depth_deduction,
                "box_width_deduction_mm": box_width_deduction,
                "drawer_system_kind": drawer_system_kind,
                "drawer_system_config": _range_drawer_system_config(drawer_system_config, mount_type, product_family, length),
                "accessory_config": accessory_config,
            }
        )
    return payloads


def _range_code(pattern: str, length: int) -> str:
    if not pattern:
        return ""
    if "{length}" in pattern:
        return pattern.replace("{length}", str(length))
    return f"{pattern}-{length}"


def _range_drawer_system_config(config: dict[str, Any], mount_type: str, product_family: str, length: int) -> dict[str, Any]:
    if mount_type != "metal_system":
        return dict(config)
    next_config = dict(config)
    next_config.setdefault("product_family", product_family)
    compatible_lengths = next_config.get("compatible_nominal_lengths")
    if not isinstance(compatible_lengths, list) or not compatible_lengths:
        next_config["compatible_nominal_lengths"] = [length]
    return next_config


def _import_existing(resource: str, identity: str, references: dict[str, Any]) -> dict[str, Any] | None:
    key = {
        "boards": "boards_by_identity",
        "slides": "slides_by_identity",
        "hinges": "hinges_by_identity",
        "handles": "handles_by_identity",
        "suppliers": "suppliers_by_identity",
        "extra_categories": "extra_categories_by_identity",
        "extras": "extras_by_identity",
        "supplier_item_costs": "item_suppliers_by_identity",
        "price_list_items": "price_items_by_identity",
    }[resource]
    return references[key].get(identity)


def _import_apply_row(
    preview_row: dict[str, Any],
    status: str,
    message: str,
    *,
    target_id: str = "",
    problems: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "row_number": preview_row["row_number"],
        "status": status,
        "identity": preview_row["identity"],
        "message": message,
        "target_id": target_id,
        "problems": problems or [],
    }


def _supplier_import_cost_values_match(row: dict[str, Any], data: dict[str, Any]) -> bool:
    return (
        int(row["list_price_cents"]) == int(data.get("list_price_cents", 0))
        and int(row["discount_bps"]) == int(data.get("discount_bps", 0))
        and int(row["unit_cost_cents"]) == int(data["unit_cost_cents"])
        and str(row["currency_code"]) == str(data.get("currency_code", "ZAR"))
    )


def _try_extract_ref_id(item_type: str, item_key: str) -> str | None:
    prefix = f"{item_type}::"
    if not item_key.startswith(prefix):
        return None
    raw_ref = item_key[len(prefix) :].strip()
    if not raw_ref or "::" in raw_ref:
        return None
    return raw_ref


def _calculate_discounted_cost_cents(list_price_cents: int, discount_bps: int) -> int:
    return (int(list_price_cents) * (10000 - int(discount_bps)) + 5000) // 10000


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
