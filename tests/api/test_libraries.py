from __future__ import annotations

import base64
from contextlib import nullcontext
from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from corequote_api.auth import AuthenticatedUser
from corequote_api.library_imports import build_import_preview, build_reference_maps
from corequote_api.libraries import (
    BOARD_CONFIG,
    LibraryConflict,
    LibraryNotFound,
    LibraryStore,
    LibraryValidationError,
    _build_setup_checklist,
    _calculate_discounted_cost_cents,
    _effective_status,
    build_slide_range_payloads,
)
from corequote_api.main import app
from corequote_api.routers import auth, libraries


client = TestClient(app)
NOW = datetime(2026, 5, 28, 12, 0, tzinfo=UTC)


class FakeAuthStore:
    def __init__(self, *, role: str = "owner"):
        self.user = AuthenticatedUser(
            id="user-1",
            company_id="company-1",
            company_name="Core Cabinets",
            name="Dylan Payne",
            email="dylan@example.com",
            role=role,
        )

    def get_user_for_token(self, token: str) -> AuthenticatedUser | None:
        if token == "test-token":
            return self.user
        return None


class FakeLibraryStore:
    def __init__(self):
        self.deleted: list[tuple[str, str]] = []
        self.price_item_deleted: tuple[str, str, str] | None = None
        self.active_price_list_requested = False
        self.pricing_settings_payload: dict | None = None
        self.catalog_list_payload: tuple[str, str, str | None, int | None] | None = None
        self.catalog_bulk_payload: tuple[str, dict] | None = None
        self.created_payload: tuple[str, dict] | None = None
        self.updated_payload: tuple[str, str, dict] | None = None
        self.price_list_payload: dict | None = None
        self.price_item_payload: tuple[str, dict] | None = None
        self.item_supplier_payload: dict | None = None
        self.item_supplier_list_payload: tuple[str, str | None, str | None, str | None, int | None, str | None, bool | None] | None = None
        self.supplier_cost_payload: tuple[str, dict] | None = None
        self.supplier_cost_list_payload: tuple[str, str, bool, datetime | None] | None = None
        self.supplier_discount_payload: tuple[str, dict] | None = None
        self.generation_payload: tuple[str, dict] | None = None
        self.price_item_list_payload: tuple[str, str, bool, datetime | None, str | None, str | None, str | None, int | None] | None = None
        self.price_coverage_payload: tuple[str, str] | None = None
        self.price_item_bulk_update_payload: tuple[str, str, dict] | None = None
        self.setup_checklist_company_id: str | None = None
        self.import_preview_company_id: str | None = None
        self.import_preview_payload: dict | None = None
        self.import_apply_company_id: str | None = None
        self.import_apply_user_id: str | None = None
        self.import_apply_payload: dict | None = None

    def list_boards(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        self.catalog_list_payload = ("boards", company_id, search, recent_days)
        return [board("board-1")]

    def get_setup_checklist(self, company_id: str):
        self.setup_checklist_company_id = company_id
        return _build_setup_checklist(
            {
                "board_count": 3,
                "slide_count": 1,
                "hinge_count": 1,
                "handle_count": 4,
                "extra_category_count": 1,
                "extra_count": 1,
                "supplier_count": 1,
                "active_supplier_cost_count": 1,
                "active_price_list_count": 1,
                "active_price_count": 5,
                "pricing_settings_count": 1,
                "vat_rate_bps": 1500,
                "default_markup_bps": 2500,
                "quote_count": 1,
                "quote_with_defaults_count": 1,
            }
        )

    def preview_library_import(self, company_id: str, payload: dict):
        self.import_preview_company_id = company_id
        self.import_preview_payload = payload
        return build_import_preview(
            payload,
            build_reference_maps(
                {
                    "boards": [board("board-1")],
                    "slides": [slide("slide-1")],
                    "hinges": [hinge("hinge-1")],
                    "handles": [handle("handle-1")],
                    "suppliers": [supplier("supplier-1")],
                    "extra_categories": [extra_category("category-1")],
                    "extras": [extra("extra-1")],
                    "item_suppliers": [item_supplier("item-supplier-1")],
                    "price_items": [price_item("price-item-1", "price-list-1", item_ref_id="slide-1")],
                    "price_list_id": "price-list-1",
                }
            ),
        )

    def apply_library_import(self, company_id: str, user_id: str, payload: dict):
        self.import_apply_company_id = company_id
        self.import_apply_user_id = user_id
        self.import_apply_payload = payload
        preview = self.preview_library_import(company_id, payload)
        rows = []
        summary = {"total_rows": 0, "created_count": 0, "updated_count": 0, "skipped_count": 0, "failed_count": 0}
        for row in preview["rows"]:
            summary["total_rows"] += 1
            if row["status"] == "create":
                status = "created"
                target_id = f"created-{row['row_number']}"
                summary["created_count"] += 1
            elif row["status"] == "update":
                status = "updated"
                target_id = f"updated-{row['row_number']}"
                summary["updated_count"] += 1
            elif row["status"] == "skipped":
                status = "skipped"
                target_id = ""
                summary["skipped_count"] += 1
            else:
                status = "failed"
                target_id = ""
                summary["failed_count"] += 1
            rows.append(
                {
                    "row_number": row["row_number"],
                    "status": status,
                    "identity": row["identity"],
                    "message": row["message"],
                    "target_id": target_id,
                    "problems": row["problems"],
                }
            )
        return {
            "batch_id": "import-batch-1",
            "resource": preview["resource"],
            "source_format": preview["source_format"],
            "summary": summary,
            "rows": rows,
        }

    def create_board(self, company_id: str, payload: dict):
        self.created_payload = ("boards", payload)
        return board("board-2", brand=payload["brand"], grain_policy=payload.get("grain_policy", "required"))

    def get_board(self, company_id: str, item_id: str):
        if not item_id.startswith("board-"):
            raise LibraryNotFound()
        return board(item_id)

    def update_board(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("boards", item_id, payload)
        return board(item_id, brand=payload["brand"], grain_policy=payload.get("grain_policy", "required"))

    def delete_board(self, company_id: str, item_id: str):
        self.deleted.append(("boards", item_id))

    def bulk_update_catalog(self, company_id: str, payload: dict):
        self.catalog_bulk_payload = (company_id, payload)
        confirm = bool(payload.get("confirm", False))
        return {
            "resource": payload["resource"],
            "confirm": confirm,
            "requested_count": len(payload["item_ids"]),
            "matched_count": len(payload["item_ids"]),
            "updated_count": len(payload["item_ids"]) if confirm else 0,
            "failed_count": 0,
            "summary_message": "Preview ready." if not confirm else "Bulk update applied.",
            "rows": [
                {
                    "item_id": item_id,
                    "label": f"{payload['resource']} {index + 1}",
                    "status": "updated" if confirm else "preview",
                    "message": "Updated selected fields." if confirm else "Will update selected fields.",
                    "changed_fields": sorted(payload["updates"]),
                }
                for index, item_id in enumerate(payload["item_ids"])
            ],
        }

    def list_slides(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        return [slide("slide-1")]

    def create_slide(self, company_id: str, payload: dict):
        self.created_payload = ("slides", payload)
        return slide(
            "slide-2",
            brand=payload["brand"],
            mount_type=payload.get("mount_type", "side_mount"),
            product_family=payload.get("product_family", ""),
            drawer_system_kind=payload.get("drawer_system_kind", "conventional"),
            drawer_system_config=payload.get("drawer_system_config") or {},
            accessory_config=payload.get("accessory_config") or {},
        )

    def create_slide_range(self, company_id: str, payload: dict):
        self.created_payload = ("slide_range", payload)
        rows = [
            slide(
                f"slide-range-{index + 1}",
                brand=payload["brand"],
                model=f"{payload['product_family']} {row['length']}",
                length=row["length"],
                mount_type=payload.get("mount_type", "side_mount"),
                product_family=payload["product_family"],
                drawer_system_kind="metal" if payload.get("mount_type") == "metal_system" else "conventional",
                drawer_system_config=payload.get("drawer_system_config") or {},
                accessory_config=payload.get("accessory_config") or {},
            )
            for index, row in enumerate(payload["lengths"])
        ]
        return {"created_count": len(rows), "slides": rows}

    def get_slide(self, company_id: str, item_id: str):
        return slide(item_id)

    def update_slide(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("slides", item_id, payload)
        return slide(
            item_id,
            brand=payload["brand"],
            drawer_system_kind=payload.get("drawer_system_kind", "conventional"),
            drawer_system_config=payload.get("drawer_system_config") or {},
            accessory_config=payload.get("accessory_config") or {},
        )

    def delete_slide(self, company_id: str, item_id: str):
        self.deleted.append(("slides", item_id))

    def list_hinges(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        return [hinge("hinge-1")]

    def create_hinge(self, company_id: str, payload: dict):
        self.created_payload = ("hinges", payload)
        return hinge("hinge-2", brand=payload["brand"], accessory_config=payload.get("accessory_config") or {})

    def get_hinge(self, company_id: str, item_id: str):
        return hinge(item_id)

    def update_hinge(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("hinges", item_id, payload)
        return hinge(item_id, brand=payload["brand"], accessory_config=payload.get("accessory_config") or {})

    def delete_hinge(self, company_id: str, item_id: str):
        self.deleted.append(("hinges", item_id))

    def list_suppliers(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        self.catalog_list_payload = ("suppliers", company_id, search, recent_days)
        return [supplier("supplier-1")]

    def create_supplier(self, company_id: str, payload: dict):
        self.created_payload = ("suppliers", payload)
        return supplier("supplier-2", name=payload["name"])

    def get_supplier(self, company_id: str, supplier_id: str):
        return supplier(supplier_id)

    def update_supplier(self, company_id: str, supplier_id: str, payload: dict):
        self.updated_payload = ("suppliers", supplier_id, payload)
        return supplier(supplier_id, name=payload["name"])

    def delete_supplier(self, company_id: str, supplier_id: str):
        self.deleted.append(("suppliers", supplier_id))

    def apply_supplier_discount(self, company_id: str, supplier_id: str, payload: dict):
        self.supplier_discount_payload = (supplier_id, payload)
        return {
            "supplier_id": supplier_id,
            "discount_bps": payload["discount_bps"],
            "matched_item_supplier_count": 3,
            "updated_cost_count": 2,
            "unchanged_cost_count": 1,
            "skipped_without_active_cost_count": 0,
        }

    def list_handles(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        return [handle("handle-1")]

    def create_handle(self, company_id: str, payload: dict):
        self.created_payload = ("handles", payload)
        return handle(
            "handle-2",
            name=payload["name"],
            handle_type=payload.get("handle_type", "standard"),
            front_reduction_mm=payload.get("front_reduction_mm", 0),
        )

    def get_handle(self, company_id: str, item_id: str):
        return handle(item_id)

    def update_handle(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("handles", item_id, payload)
        return handle(
            item_id,
            name=payload["name"],
            handle_type=payload.get("handle_type", "standard"),
            front_reduction_mm=payload.get("front_reduction_mm", 0),
        )

    def delete_handle(self, company_id: str, item_id: str):
        self.deleted.append(("handles", item_id))

    def list_extra_categories(self, company_id: str, search: str | None = None, recent_days: int | None = None):
        return [extra_category("category-1")]

    def create_extra_category(self, company_id: str, payload: dict):
        self.created_payload = ("extra-categories", payload)
        return extra_category("category-2", name=payload["name"])

    def get_extra_category(self, company_id: str, item_id: str):
        return extra_category(item_id)

    def update_extra_category(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("extra-categories", item_id, payload)
        return extra_category(item_id, name=payload["name"])

    def delete_extra_category(self, company_id: str, item_id: str):
        self.deleted.append(("extra-categories", item_id))

    def list_extras(
        self,
        company_id: str,
        search: str | None = None,
        category_id: str | None = None,
        recent_days: int | None = None,
    ):
        return [extra("extra-1")]

    def create_extra(self, company_id: str, payload: dict):
        self.created_payload = ("extras", payload)
        return extra("extra-2", name=payload["name"], supplier_id=payload.get("supplier_id"))

    def get_extra(self, company_id: str, item_id: str):
        return extra(item_id)

    def update_extra(self, company_id: str, item_id: str, payload: dict):
        self.updated_payload = ("extras", item_id, payload)
        return extra(item_id, name=payload["name"], supplier_id=payload.get("supplier_id"))

    def delete_extra(self, company_id: str, item_id: str):
        self.deleted.append(("extras", item_id))

    def list_item_suppliers(
        self,
        company_id: str,
        item_type: str | None = None,
        item_ref_id: str | None = None,
        search: str | None = None,
        recent_days: int | None = None,
        supplier_id: str | None = None,
        has_active_cost: bool | None = None,
    ):
        self.item_supplier_list_payload = (
            company_id,
            item_type,
            item_ref_id,
            search,
            recent_days,
            supplier_id,
            has_active_cost,
        )
        rows = [item_supplier("item-supplier-1")]
        if item_type:
            rows = [row for row in rows if row["item_type"] == item_type]
        if item_ref_id:
            rows = [row for row in rows if row["item_ref_id"] == item_ref_id]
        return rows

    def create_item_supplier(self, company_id: str, payload: dict):
        self.item_supplier_payload = payload
        return item_supplier("item-supplier-2", **payload)

    def get_item_supplier(self, company_id: str, item_supplier_id: str):
        return item_supplier(item_supplier_id)

    def update_item_supplier(self, company_id: str, item_supplier_id: str, payload: dict):
        self.item_supplier_payload = payload
        return item_supplier(item_supplier_id, **payload)

    def delete_item_supplier(self, company_id: str, item_supplier_id: str):
        self.deleted.append(("item-suppliers", item_supplier_id))

    def list_supplier_item_costs(
        self,
        company_id: str,
        item_supplier_id: str,
        include_history: bool = False,
        as_of: datetime | None = None,
    ):
        self.supplier_cost_list_payload = (company_id, item_supplier_id, include_history, as_of)
        rows = [supplier_cost("supplier-cost-1", item_supplier_id)]
        if include_history:
            rows.append(supplier_cost("supplier-cost-old", item_supplier_id, effective_to=NOW))
            rows.append(supplier_cost("supplier-cost-future", item_supplier_id, effective_from=datetime(2026, 6, 30, 8, 0, tzinfo=UTC)))
        return rows

    def create_supplier_item_cost(self, company_id: str, item_supplier_id: str, payload: dict):
        self.supplier_cost_payload = (item_supplier_id, payload)
        return supplier_cost("supplier-cost-2", item_supplier_id, **payload)

    def upsert_supplier_item_cost(self, company_id: str, item_supplier_id: str, payload: dict):
        self.supplier_cost_payload = (item_supplier_id, payload)
        return supplier_cost("supplier-cost-upsert", item_supplier_id, **payload)

    def get_supplier_item_cost(self, company_id: str, item_supplier_id: str, cost_id: str):
        return supplier_cost(cost_id, item_supplier_id)

    def get_pricing_settings(self, company_id: str):
        return {
            "company_id": company_id,
            "vat_rate_bps": 1500,
            "default_markup_bps": 2500,
            "created_at": NOW,
            "updated_at": NOW,
        }

    def update_pricing_settings(self, company_id: str, payload: dict):
        self.pricing_settings_payload = payload
        return {
            "company_id": company_id,
            **payload,
            "created_at": NOW,
            "updated_at": NOW,
        }

    def list_price_lists(self, company_id: str):
        return [price_list("price-list-1")]

    def get_active_price_list(self, company_id: str, as_of: datetime | None = None):
        self.active_price_list_requested = True
        return price_list("price-list-1")

    def create_price_list(self, company_id: str, payload: dict):
        self.price_list_payload = payload
        return price_list("price-list-2", name=payload["name"], status=payload["status"])

    def get_price_list(self, company_id: str, price_list_id: str):
        return price_list(price_list_id)

    def get_price_list_coverage(self, company_id: str, price_list_id: str):
        self.price_coverage_payload = (company_id, price_list_id)
        return price_coverage(price_list_id)

    def update_price_list(self, company_id: str, price_list_id: str, payload: dict):
        self.price_list_payload = payload
        return price_list(price_list_id, name=payload["name"], status=payload["status"])

    def delete_price_list(self, company_id: str, price_list_id: str):
        self.deleted.append(("price-lists", price_list_id))

    def generate_price_list_from_supplier_costs(self, company_id: str, price_list_id: str, payload: dict):
        self.generation_payload = (price_list_id, payload)
        return {
            "price_list_id": price_list_id,
            "selection_mode": payload["selection_mode"],
            "generated_count": 2,
            "created_count": 1,
            "updated_count": 1,
            "unchanged_count": 0,
            "skipped_override_count": 0,
            "missing_price_count": 0,
        }

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
    ):
        self.price_item_list_payload = (
            company_id,
            price_list_id,
            include_history,
            as_of,
            search,
            item_type,
            effective_status,
            recent_days,
        )
        rows = [price_item("price-item-1", price_list_id)]
        if include_history:
            rows.append(price_item("price-item-old", price_list_id, effective_to=NOW))
            rows.append(price_item("price-item-future", price_list_id, effective_from=datetime(2026, 6, 30, 8, 0, tzinfo=UTC)))
        return rows

    def bulk_update_price_list_items(self, company_id: str, price_list_id: str, payload: dict):
        confirm = bool(payload.get("confirm", False))
        changed_fields = [field for field in ("unit_price_cents", "uom", "cost_source") if payload.get(field) is not None]
        if not changed_fields:
            raise LibraryValidationError("Choose at least one price field to update")
        self.price_item_bulk_update_payload = (company_id, price_list_id, payload)
        return {
            "resource": "price_list_items",
            "confirm": confirm,
            "requested_count": len(payload["item_ids"]),
            "matched_count": len(payload["item_ids"]),
            "updated_count": len(payload["item_ids"]) if confirm else 0,
            "failed_count": 0,
            "summary_message": "Preview ready." if not confirm else "Bulk update applied.",
            "rows": [
                {
                    "item_id": item_id,
                    "label": "handle::handle-1 unit",
                    "status": "updated" if confirm else "preview",
                    "message": "Updated selected fields." if confirm else "Will update selected fields.",
                    "changed_fields": changed_fields,
                }
                for item_id in payload["item_ids"]
            ],
        }

    def create_price_list_item(self, company_id: str, price_list_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-2",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
            source_supplier_item_cost_id=payload.get("source_supplier_item_cost_id"),
            cost_source=payload.get("cost_source", "manual"),
        )

    def get_price_list_item(self, company_id: str, price_list_id: str, item_id: str):
        return price_item(item_id, price_list_id)

    def update_price_list_item(self, company_id: str, price_list_id: str, item_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-3",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
            source_supplier_item_cost_id=payload.get("source_supplier_item_cost_id"),
            cost_source=payload.get("cost_source", "manual"),
            replaces_id=item_id,
        )

    def upsert_price_list_item(self, company_id: str, price_list_id: str, payload: dict):
        self.price_item_payload = (price_list_id, payload)
        if not payload.get("item_key") and not payload.get("item_ref_id"):
            raise LibraryValidationError("Either item_ref_id or item_key is required")
        item_key = payload.get("item_key") or f"{payload['item_type']}::{payload['item_ref_id']}"
        return price_item(
            "price-item-upsert",
            price_list_id,
            item_key=item_key,
            item_ref_id=payload.get("item_ref_id"),
            item_type=payload["item_type"],
            price_component=payload["price_component"],
            uom=payload["uom"],
            unit_price_cents=payload["unit_price_cents"],
            source_supplier_item_cost_id=payload.get("source_supplier_item_cost_id"),
            cost_source=payload.get("cost_source", "manual"),
        )

    def delete_price_list_item(self, company_id: str, price_list_id: str, item_id: str):
        self.price_item_deleted = (company_id, price_list_id, item_id)


class PricingValidationStore(LibraryStore):
    def __init__(self, item_rows: dict[tuple[str, str], dict]):
        super().__init__(database_url="postgresql://unused")
        self.item_rows = item_rows

    def _ensure_price_item_reference(self, company_id: str, item_type: str, item_ref_id: str):
        row = self.item_rows.get((item_type, item_ref_id))
        if not row:
            raise LibraryNotFound("Library row not found")
        return row

    def _ensure_supplier(self, company_id: str, supplier_id: str):
        return None

    def _ensure_supplier_item_cost(self, company_id: str, cost_id: str):
        return None


class _CaptureCursor:
    def __init__(self, row: dict):
        self.row = row

    def fetchone(self):
        return self.row


class _BrandCaptureConnection:
    def __init__(self):
        self.write_params: tuple | list = ()

    def execute(self, sql: str, params: tuple | list = ()):
        if "INSERT INTO brands" in sql:
            return _CaptureCursor({"id": "brand-uuid"})
        self.write_params = params
        return _CaptureCursor(board("board-1", brand="CoreBoard"))


def board(item_id: str, *, brand: str = "PG Bison", grain_policy: str = "required") -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "material": "MelaWood",
        "thickness": 16,
        "length_mm": 2750,
        "width_mm": 1830,
        "costing_mode": "sheet",
        "grain_policy": grain_policy,
        "created_at": NOW,
        "updated_at": NOW,
    }


def slide(
    item_id: str,
    *,
    brand: str = "Grass",
    model: str = "Dynapro",
    length: int = 500,
    mount_type: str = "side_mount",
    product_family: str = "",
    drawer_system_kind: str = "conventional",
    drawer_system_config: dict | None = None,
    accessory_config: dict | None = None,
) -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "model": model,
        "code": "DYN-500",
        "length": length,
        "side_length": 500,
        "side_clearance_total": 26,
        "side_height_uplift": 0,
        "mount_type": mount_type,
        "product_family": product_family,
        "required_depth_mm": length,
        "drawer_depth_deduction_mm": 10,
        "box_width_deduction_mm": 26,
        "drawer_system_kind": drawer_system_kind,
        "drawer_system_config": drawer_system_config or {},
        "accessory_config": accessory_config or {},
        "created_at": NOW,
        "updated_at": NOW,
    }


def hinge(item_id: str, *, brand: str = "Blum", accessory_config: dict | None = None) -> dict:
    return {
        "id": item_id,
        "brand": brand,
        "model": "Clip Top",
        "code": "BL-110",
        "opening_angle_deg": 110,
        "accessory_config": accessory_config or {},
        "created_at": NOW,
        "updated_at": NOW,
    }


def handle(
    item_id: str,
    *,
    name: str = "Slim Bar",
    supplier_id: str | None = "supplier-1",
    supplier_name: str = "Hafele",
    handle_type: str = "standard",
    front_reduction_mm: int = 0,
) -> dict:
    return {
        "id": item_id,
        "name": name,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name if supplier_id else "",
        "handle_type": handle_type,
        "front_reduction_mm": front_reduction_mm,
        "created_at": NOW,
        "updated_at": NOW,
    }


def supplier(item_id: str, *, name: str = "Grass ZA") -> dict:
    return {
        "id": item_id,
        "name": name,
        "code": "GRASS-ZA",
        "contact_name": "Sales",
        "email": "sales@example.com",
        "phone": "",
        "notes": "",
        "default_discount_bps": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }


def extra_category(item_id: str, *, name: str = "Appliances") -> dict:
    return {"id": item_id, "name": name, "created_at": NOW, "updated_at": NOW}


def extra(item_id: str, *, name: str = "Stove", supplier_id: str | None = "supplier-1") -> dict:
    return {
        "id": item_id,
        "name": name,
        "category_id": "category-1",
        "category_name": "Appliances",
        "supplier_id": supplier_id,
        "supplier": "Grass ZA" if supplier_id else "",
        "code": "DFY-600",
        "notes": "",
        "created_at": NOW,
        "updated_at": NOW,
    }


def price_list(item_id: str, *, name: str = "Default Price List", status: str = "active") -> dict:
    return {
        "id": item_id,
        "name": name,
        "status": status,
        "effective_from": None,
        "effective_to": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def price_item(
    item_id: str,
    price_list_id: str,
    *,
    item_key: str = "slide::Grass::Dynapro::DYN-500::500",
    item_ref_id: str | None = None,
    item_type: str = "slide",
    price_component: str = "unit",
    uom: str = "pairs",
    unit_price_cents: int = 12500,
    effective_to: datetime | None = None,
    effective_from: datetime | None = None,
    replaces_id: str | None = None,
    source_supplier_item_cost_id: str | None = None,
    cost_source: str = "manual",
) -> dict:
    effective_from = effective_from or NOW
    return {
        "id": item_id,
        "price_list_id": price_list_id,
        "item_type": item_type,
        "item_ref_id": item_ref_id,
        "item_key": item_key,
        "price_component": price_component,
        "uom": uom,
        "unit_price_cents": unit_price_cents,
        "source_supplier_item_cost_id": source_supplier_item_cost_id,
        "cost_source": cost_source,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "replaces_id": replaces_id,
        "is_active": effective_to is None,
        "is_current": _effective_status(effective_from, effective_to, NOW) == "current",
        "effective_status": _effective_status(effective_from, effective_to, NOW),
        "created_at": NOW,
        "updated_at": NOW,
    }


def price_coverage(price_list_id: str) -> dict:
    quote_context = {
        "project_id": "project-1",
        "project_name": "Smith Kitchen",
        "quote_id": "quote-1",
        "quote_name": "Main kitchen",
        "quote_number": "Q-001",
        "revision": 1,
        "quote_status": "draft",
        "usage_label": "Unit 1 drawer hardware",
    }
    covered_row = {
        "item_type": "slide",
        "item_type_label": "Drawer hardware",
        "item_ref_id": "slide-1",
        "item_key": "slide::slide-1",
        "item_name": "Grass Dynapro (DYN-500)",
        "price_component": "unit",
        "component": "Unit price",
        "uom": "pairs",
        "status": "covered",
        "has_current_price": True,
        "active_price_list_item_id": "price-item-1",
        "unit_price_cents": 12500,
        "cost_source": "supplier",
        "source_supplier_item_cost_id": "supplier-cost-1",
        "has_supplier_cost": True,
        "active_supplier_item_id": "item-supplier-1",
        "active_supplier_item_cost_id": "supplier-cost-1",
        "supplier_unit_cost_cents": 12500,
        "supplier_order_uom": "pairs",
        "quote_count": 1,
        "used_in": [quote_context],
    }
    missing_row = {
        "item_type": "handle",
        "item_type_label": "Handle",
        "item_ref_id": "handle-1",
        "item_key": "handle::handle-1",
        "item_name": "Core Bar Handle",
        "price_component": "unit",
        "component": "Unit price",
        "uom": "pcs",
        "status": "missing",
        "has_current_price": False,
        "active_price_list_item_id": None,
        "unit_price_cents": None,
        "cost_source": None,
        "source_supplier_item_cost_id": None,
        "has_supplier_cost": False,
        "active_supplier_item_id": None,
        "active_supplier_item_cost_id": None,
        "supplier_unit_cost_cents": None,
        "supplier_order_uom": None,
        "quote_count": 1,
        "used_in": [{**quote_context, "usage_label": "Quote base handle default"}],
    }
    return {
        "price_list_id": price_list_id,
        "price_list_name": "Default Price List",
        "generated_at": NOW,
        "used_count": 2,
        "covered_count": 1,
        "missing_count": 1,
        "stale_count": 0,
        "override_count": 0,
        "groups": [
            {
                "item_type": "slide",
                "item_type_label": "Drawer hardware",
                "used_count": 1,
                "covered_count": 1,
                "missing_count": 0,
                "stale_count": 0,
                "override_count": 0,
                "rows": [covered_row],
            },
            {
                "item_type": "handle",
                "item_type_label": "Handle",
                "used_count": 1,
                "covered_count": 0,
                "missing_count": 1,
                "stale_count": 0,
                "override_count": 0,
                "rows": [missing_row],
            },
        ],
    }


def item_supplier(
    item_id: str,
    *,
    item_type: str = "slide",
    item_ref_id: str = "slide-1",
    supplier_id: str = "supplier-1",
    supplier_sku: str = "F130107820204",
    supplier_description: str = "Dynapro 500",
    price_component: str = "unit",
    order_uom: str = "pairs",
    is_preferred: bool = True,
    notes: str = "",
) -> dict:
    return {
        "id": item_id,
        "item_type": item_type,
        "item_ref_id": item_ref_id,
        "supplier_id": supplier_id,
        "supplier_name": "Grass ZA",
        "supplier_sku": supplier_sku,
        "supplier_description": supplier_description,
        "price_component": price_component,
        "order_uom": order_uom,
        "is_preferred": is_preferred,
        "notes": notes,
        "active_supplier_item_cost_id": "supplier-cost-1",
        "active_list_price_cents": 68498,
        "active_discount_bps": 3000,
        "active_unit_cost_cents": 47949,
        "active_currency_code": "ZAR",
        "created_at": NOW,
        "updated_at": NOW,
    }


def supplier_cost(
    item_id: str,
    item_supplier_id: str,
    *,
    list_price_cents: int = 68498,
    discount_bps: int = 3000,
    unit_cost_cents: int = 47949,
    currency_code: str = "ZAR",
    source: str = "manual",
    source_ref: str = "",
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
) -> dict:
    effective_from = effective_from or NOW
    effective_status = _effective_status(effective_from, effective_to, NOW)
    return {
        "id": item_id,
        "item_supplier_id": item_supplier_id,
        "list_price_cents": list_price_cents,
        "discount_bps": discount_bps,
        "unit_cost_cents": unit_cost_cents,
        "currency_code": currency_code,
        "source": source,
        "source_ref": source_ref,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "replaces_id": None,
        "is_active": effective_to is None,
        "is_current": effective_status == "current",
        "effective_status": effective_status,
        "created_at": NOW,
        "updated_at": NOW,
    }


CATALOG_CASES = [
    (
        "boards",
        {"brand": "Sonae", "material": "MDF", "thickness": 18, "length_mm": 2440, "width_mm": 1220, "costing_mode": "sqm", "grain_policy": "none"},
        "brand",
        "Sonae",
    ),
    (
        "slides",
        {
            "brand": "Blum",
            "model": "Movento",
            "code": "MOV-500",
            "length": 500,
            "side_length": 500,
            "side_clearance_total": 26,
            "side_height_uplift": 0,
        },
        "brand",
        "Blum",
    ),
    (
        "hinges",
        {"brand": "Hettich", "model": "Sensys", "code": "HS-110", "opening_angle_deg": 110},
        "brand",
        "Hettich",
    ),
    (
        "suppliers",
        {
            "name": "Grass ZA",
            "code": "GRASS-ZA",
            "contact_name": "Sales",
            "email": "sales@example.com",
            "phone": "",
            "notes": "",
        },
        "name",
        "Grass ZA",
    ),
    ("handles", {"name": "Cup Pull", "supplier_id": "supplier-1"}, "name", "Cup Pull"),
    ("extra-categories", {"name": "Lighting"}, "name", "Lighting"),
    (
        "extras",
        {"name": "LED Strip", "category_id": "category-1", "supplier_id": "supplier-1", "code": "LED-5M", "notes": "Warm white"},
        "name",
        "LED Strip",
    ),
]


def test_setup_checklist_flags_blank_company_gaps():
    checklist = _build_setup_checklist({})

    statuses = {item["id"]: item["status"] for item in checklist["items"]}
    assert checklist["status"] == "needs_attention"
    assert checklist["complete_count"] == 0
    assert statuses["boards"] == "missing"
    assert statuses["slides"] == "missing"
    assert statuses["hinges"] == "missing"
    assert statuses["handles"] == "missing"
    assert statuses["extras"] == "missing"
    assert statuses["supplier-costs"] == "missing"
    assert statuses["active-price-list"] == "missing"
    assert statuses["pricing-settings"] == "warning"
    assert statuses["quote-defaults"] == "action_needed"


def test_setup_checklist_is_ready_for_phase_4_fixture_shape():
    checklist = _build_setup_checklist(
        {
            "board_count": 3,
            "slide_count": 1,
            "hinge_count": 1,
            "handle_count": 4,
            "extra_category_count": 1,
            "extra_count": 1,
            "supplier_count": 1,
            "active_supplier_cost_count": 7,
            "active_price_list_count": 1,
            "active_price_count": 9,
            "pricing_settings_count": 1,
            "vat_rate_bps": 1500,
            "default_markup_bps": 3000,
            "quote_count": 1,
            "quote_with_defaults_count": 1,
        }
    )

    assert checklist["status"] == "ready"
    assert checklist["complete_count"] == checklist["total_count"]
    assert {item["status"] for item in checklist["items"]} == {"complete"}


def test_setup_checklist_endpoint_uses_pricing_read_and_company_scope():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/setup-checklist", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert store.setup_checklist_company_id == "company-1"


def test_setup_checklist_endpoint_requires_pricing_read_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/setup-checklist", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:read"}


def test_import_preview_classifies_board_rows_from_csv():
    content = "\n".join(
        [
            "Brand,Material,Thickness,Length,Width,Costing Mode,Grain Policy",
            "PG Bison,MelaWood,16,2750,1830,sqm,optional",
            "PG Bison,MelaWood,16,2750,1830,sqm,optional",
            "Sonae,MDF,18,2440,1220,sheet,none",
            "Bad Board,MDF,0,2440,1220,sheet,required",
        ]
    )

    preview = build_import_preview(
        {"resource": "boards", "source_format": "csv", "content": content},
        build_reference_maps(
            {
                "boards": [board("board-1")],
                "slides": [],
                "hinges": [],
                "handles": [],
                "suppliers": [],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [],
                "price_items": [],
                "price_list_id": "",
            }
        ),
    )

    assert preview["summary"] == {
        "total_rows": 4,
        "create_count": 1,
        "update_count": 1,
        "skipped_count": 0,
        "duplicate_count": 1,
        "blocked_count": 1,
    }
    assert [row["status"] for row in preview["rows"]] == ["update", "duplicate", "create", "blocked"]
    assert preview["rows"][0]["payload"]["grain_policy"] == "optional"
    assert preview["rows"][2]["payload"]["grain_policy"] == "none"
    assert preview["rows"][3]["problems"][0]["code"] == "invalid_number"


def test_import_preview_normalizes_slide_runner_metadata_from_csv():
    content = "\n".join(
        [
            "Brand,Model,Code,Length,Mount Type,Product Family,Required Depth,Depth Deduction,Width Deduction,Drawer System Kind",
            "Blum,Tandem 500,TAN-500,500,undermount,Tandem,510,10,42,conventional",
        ]
    )

    preview = build_import_preview(
        {"resource": "slides", "source_format": "csv", "content": content},
        build_reference_maps(
            {
                "boards": [],
                "slides": [],
                "hinges": [],
                "handles": [],
                "suppliers": [],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [],
                "price_items": [],
                "price_list_id": "",
            }
        ),
    )

    payload = preview["rows"][0]["payload"]

    assert preview["rows"][0]["status"] == "create"
    assert payload["mount_type"] == "undermount"
    assert payload["product_family"] == "Tandem"
    assert payload["required_depth_mm"] == 510
    assert payload["drawer_depth_deduction_mm"] == 10
    assert payload["box_width_deduction_mm"] == 42


def test_brand_backed_catalog_writes_brand_id_not_brand_row():
    store = LibraryStore(database_url="postgresql://unused")
    payload = {
        "brand": "CoreBoard",
        "material": "White melamine",
        "thickness": 16,
        "length_mm": 2750,
        "width_mm": 1830,
        "costing_mode": "sheet",
        "grain_policy": "required",
    }

    create_conn = _BrandCaptureConnection()
    store._create_with_conn(create_conn, BOARD_CONFIG, "company-1", payload)

    assert create_conn.write_params[-1] == "brand-uuid"

    update_conn = _BrandCaptureConnection()
    store._update_with_conn(update_conn, BOARD_CONFIG, "company-1", "board-1", payload)

    assert update_conn.write_params[-3] == "brand-uuid"


def test_import_preview_blocks_supplier_cost_rows_with_missing_refs_and_bad_units():
    content = "\n".join(
        [
            "Item Type,Brand,Model,Code,Supplier,Supplier SKU,Price Component,Order UOM,Unit Cost",
            "slide,Grass,Dynapro,DYN-500,Grass ZA,F130107820204, Unit ,pair,479.49",
            "hinge,Grass,Missing,,Unknown Supplier,,unit,box,100",
        ]
    )
    preview = build_import_preview(
        {"resource": "supplier_item_costs", "source_format": "csv", "content": content},
        build_reference_maps(
            {
                "boards": [],
                "slides": [slide("slide-1")],
                "hinges": [],
                "handles": [],
                "suppliers": [supplier("supplier-1", name="Grass ZA")],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [item_supplier("item-supplier-1")],
                "price_items": [],
                "price_list_id": "",
            }
        ),
    )

    assert [row["status"] for row in preview["rows"]] == ["update", "blocked"]
    assert preview["rows"][0]["payload"]["unit_cost_cents"] == 47949
    assert preview["rows"][0]["payload"]["price_component"] == "unit"
    assert preview["rows"][0]["payload"]["order_uom"] == "pairs"
    problem_codes = {problem["code"] for problem in preview["rows"][1]["problems"]}
    assert problem_codes == {"missing_catalog_item", "missing_supplier", "invalid_uom"}


def test_import_preview_blocks_non_board_price_components():
    content = "\n".join(
        [
            "Item Type,Brand,Model,Code,Price Component,UOM,Unit Price",
            "slide,Grass,Dynapro,DYN-500,sheet,sheet,125.00",
        ]
    )
    preview = build_import_preview(
        {"resource": "price_list_items", "source_format": "csv", "content": content},
        build_reference_maps(
            {
                "boards": [],
                "slides": [slide("slide-1")],
                "hinges": [],
                "handles": [],
                "suppliers": [],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [],
                "price_items": [],
                "price_list_id": "price-list-1",
            }
        ),
    )

    assert preview["rows"][0]["status"] == "blocked"
    assert preview["rows"][0]["payload"]["price_component"] == "sheet"
    assert {problem["code"] for problem in preview["rows"][0]["problems"]} == {"forbidden_price_component"}


def test_import_preview_reads_xlsx_upload_content():
    xlsx_content = _xlsx_base64(
        [
            ["Name", "Code"],
            ["Board Store", "BS"],
        ]
    )

    preview = build_import_preview(
        {"resource": "suppliers", "source_format": "xlsx", "content": xlsx_content},
        build_reference_maps(
            {
                "boards": [],
                "slides": [],
                "hinges": [],
                "handles": [],
                "suppliers": [],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [],
                "price_items": [],
                "price_list_id": "",
            }
        ),
    )

    assert preview["source_format"] == "xlsx"
    assert preview["sheet_name"] == "Sheet1"
    assert preview["columns"] == ["Name", "Code"]
    assert preview["rows"][0]["status"] == "create"
    assert preview["rows"][0]["payload"]["name"] == "Board Store"


def test_import_preview_endpoint_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/imports/preview",
            json={"resource": "boards", "source_format": "csv", "content": "Brand,Material,Thickness,Length,Width\nA,B,16,1,1\n"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_import_preview_endpoint_uses_company_scope():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {"resource": "boards", "source_format": "csv", "content": "Brand,Material,Thickness,Length,Width\nA,B,16,1,1\n"}
    try:
        response = client.post("/api/v1/libraries/imports/preview", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["create_count"] == 1
    assert store.import_preview_company_id == "company-1"
    assert store.import_preview_payload == {**payload, "filename": "", "sheet_name": None, "column_mapping": {}, "price_list_id": None}


def test_import_apply_endpoint_commits_valid_rows_and_reports_failed_rows():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "resource": "boards",
        "source_format": "csv",
        "filename": "boards.csv",
        "content": "\n".join(
            [
                "Brand,Material,Thickness,Length,Width,Costing Mode",
                "PG Bison,MelaWood,16,2750,1830,sqm",
                "PG Bison,MelaWood,16,2750,1830,sqm",
                "Sonae,MDF,18,2440,1220,sheet",
                "Bad Board,MDF,0,2440,1220,sheet",
            ]
        ),
    }
    try:
        response = client.post("/api/v1/libraries/imports/apply", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["batch_id"] == "import-batch-1"
    assert body["summary"] == {
        "total_rows": 4,
        "created_count": 1,
        "updated_count": 1,
        "skipped_count": 0,
        "failed_count": 2,
    }
    assert [row["status"] for row in body["rows"]] == ["updated", "failed", "created", "failed"]
    assert body["rows"][1]["problems"][0]["code"] == "duplicate_in_file"
    assert body["rows"][3]["problems"][0]["code"] == "invalid_number"


def test_import_apply_endpoint_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/imports/apply",
            json={"resource": "boards", "source_format": "csv", "content": "Brand,Material,Thickness,Length,Width\nA,B,16,1,1\n"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_import_apply_endpoint_uses_company_scope_and_user_audit():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {"resource": "boards", "source_format": "csv", "content": "Brand,Material,Thickness,Length,Width\nA,B,16,1,1\n"}
    try:
        response = client.post("/api/v1/libraries/imports/apply", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["summary"]["created_count"] == 1
    assert store.import_apply_company_id == "company-1"
    assert store.import_apply_user_id == "user-1"
    assert store.import_apply_payload == {**payload, "filename": "", "sheet_name": None, "column_mapping": {}, "price_list_id": None, "source_ref": ""}


def test_import_apply_endpoint_rolls_back_on_store_conflict():
    class FailingImportStore(FakeLibraryStore):
        def apply_library_import(self, company_id: str, user_id: str, payload: dict):
            raise LibraryConflict("Import failed; no rows were applied.")

    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = FailingImportStore
    try:
        response = client.post(
            "/api/v1/libraries/imports/apply",
            json={"resource": "boards", "source_format": "csv", "content": "Brand,Material,Thickness,Length,Width\nA,B,16,1,1\n"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": "Import failed; no rows were applied."}


@pytest.mark.parametrize(("resource", "payload", "field", "value"), CATALOG_CASES)
def test_catalog_library_crud(resource: str, payload: dict, field: str, value: str):
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        list_response = client.get(f"/api/v1/libraries/{resource}", headers=auth_header())
        create_response = client.post(f"/api/v1/libraries/{resource}", json=payload, headers=auth_header())
        created_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/{resource}/{created_id}", headers=auth_header())
        patch_response = client.patch(f"/api/v1/libraries/{resource}/{created_id}", json=payload, headers=auth_header())
        delete_response = client.delete(f"/api/v1/libraries/{resource}/{created_id}", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert create_response.json()[field] == value
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()[field] == value
    assert delete_response.status_code == 204
    assert store.deleted[-1] == (resource, created_id)


@pytest.mark.parametrize("handle_type", ["standard", "full_length", "c_channel", "j_channel"])
def test_handle_catalog_accepts_typed_handles(handle_type: str):
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "name": "Profile Pull",
        "supplier_id": "supplier-1",
        "handle_type": handle_type,
        "front_reduction_mm": 0 if handle_type == "standard" else 24,
    }
    try:
        create_response = client.post("/api/v1/libraries/handles", json=payload, headers=auth_header())
        patch_response = client.patch("/api/v1/libraries/handles/handle-2", json={**payload, "front_reduction_mm": 30}, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["handle_type"] == handle_type
    assert create_response.json()["front_reduction_mm"] == payload["front_reduction_mm"]
    assert store.created_payload == ("handles", payload)
    assert patch_response.status_code == 200
    assert patch_response.json()["handle_type"] == handle_type
    assert patch_response.json()["front_reduction_mm"] == 30


def test_old_handle_payload_defaults_to_standard_profile_fields():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {"name": "Cup Pull", "supplier_id": "supplier-1"}
    try:
        response = client.post("/api/v1/libraries/handles", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["handle_type"] == "standard"
    assert response.json()["front_reduction_mm"] == 0
    assert store.created_payload == ("handles", {**payload, "handle_type": "standard", "front_reduction_mm": 0})


def test_import_preview_normalizes_typed_handle_rows_from_csv():
    content = "\n".join(
        [
            "Name,Supplier,Handle Type,Front Reduction (mm)",
            "Edge Pull,Core,full length,30",
            "Top J,Core,j_channel,24",
            "Old Cup,Hafele,,",
        ]
    )
    preview = build_import_preview(
        {"resource": "handles", "source_format": "csv", "content": content},
        build_reference_maps(
            {
                "boards": [],
                "slides": [],
                "hinges": [],
                "handles": [],
                "suppliers": [supplier("supplier-1", name="Core"), supplier("supplier-2", name="Hafele")],
                "extra_categories": [],
                "extras": [],
                "item_suppliers": [],
                "price_items": [],
                "price_list_id": "",
            }
        ),
    )

    payloads = [row["payload"] for row in preview["rows"]]

    assert [row["status"] for row in preview["rows"]] == ["create", "create", "create"]
    assert payloads[0]["handle_type"] == "full_length"
    assert payloads[0]["supplier_id"] == "supplier-1"
    assert payloads[0]["front_reduction_mm"] == 30
    assert payloads[1]["handle_type"] == "j_channel"
    assert payloads[1]["supplier_id"] == "supplier-1"
    assert payloads[1]["front_reduction_mm"] == 24
    assert payloads[2]["handle_type"] == "standard"
    assert payloads[2]["supplier_id"] == "supplier-2"
    assert payloads[2]["front_reduction_mm"] == 0


def test_board_type_grain_policy_round_trips_and_validates():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "brand": "Sonae",
        "material": "MDF",
        "thickness": 18,
        "length_mm": 2440,
        "width_mm": 1220,
        "costing_mode": "sqm",
        "grain_policy": "none",
    }
    invalid_payload = {**payload, "grain_policy": "sometimes"}
    try:
        create_response = client.post("/api/v1/libraries/boards", json=payload, headers=auth_header())
        invalid_response = client.post("/api/v1/libraries/boards", json=invalid_payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["grain_policy"] == "none"
    assert store.created_payload == ("boards", payload)
    assert invalid_response.status_code == 422


def test_slide_drawer_system_config_round_trips():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "brand": "Blum",
        "model": "Legrabox",
        "code": "LEG-500",
        "length": 500,
        "side_length": 500,
        "side_clearance_total": 26,
        "side_height_uplift": 0,
        "drawer_system_kind": "metal",
        "drawer_system_config": {
            "product_family": "Legrabox",
            "manufacturer": "Blum",
            "manufacturer_notes": "Custom metadata survives for vendor-specific drawer systems.",
            "installation_width_mm": 31,
            "compatible_side_thicknesses": [16, 18],
            "panel_formulas": [
                {
                    "name": "Metal Drawer Bottom",
                    "section": "carcass",
                    "length_formula": "inner_w - (2 * installation_width_mm)",
                    "width_formula": "slide_length - 19",
                    "qty_formula": "num_drawers",
                }
            ],
            "hardware_items": [
                {
                    "item_type": "extra",
                    "name": "Front bracket set",
                    "quantity_per_drawer": 2,
                    "uom": "pcs",
                }
            ],
        },
        "accessory_config": {
            "accessories": [
                {
                    "item_type": "extra",
                    "item_ref_id": "extra-locking-plate",
                    "quantity": 2,
                    "quantity_rule": "per_drawer",
                    "required": True,
                    "condition": {"field": "always", "operator": "always"},
                }
            ]
        },
    }
    try:
        create_response = client.post("/api/v1/libraries/slides", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["drawer_system_kind"] == "metal"
    assert create_response.json()["drawer_system_config"]["product_family"] == "Legrabox"
    assert create_response.json()["accessory_config"]["accessories"][0]["quantity_rule"] == "per_drawer"
    assert store.created_payload is not None
    resource, stored_payload = store.created_payload
    assert resource == "slides"
    assert stored_payload["drawer_system_kind"] == "metal"
    assert stored_payload["drawer_system_config"]["product_family"] == "Legrabox"
    assert stored_payload["drawer_system_config"]["manufacturer_notes"] == "Custom metadata survives for vendor-specific drawer systems."
    assert stored_payload["drawer_system_config"]["panel_formulas"][0]["length_formula"] == "inner_w - (2 * installation_width_mm)"
    assert stored_payload["drawer_system_config"]["hardware_items"][0]["quantity_per_drawer"] == 2
    assert stored_payload["accessory_config"]["accessories"][0]["item_ref_id"] == "extra-locking-plate"


def test_slide_range_payload_builder_generates_runner_rows():
    payloads = build_slide_range_payloads(
        {
            "brand": "Grass",
            "product_family": "Dynapro SC",
            "mount_type": "side_mount",
            "code_pattern": "DYN-{length}",
            "lengths": [{"length": 450}, {"length": 500, "code": "CUSTOM-500"}],
            "side_clearance_total": 26,
            "drawer_depth_deduction_mm": 10,
            "box_width_deduction_mm": 26,
            "side_height_uplift": 0,
            "accessory_config": {"accessories": []},
        }
    )

    assert payloads[0]["model"] == "Dynapro SC 450"
    assert payloads[0]["code"] == "DYN-450"
    assert payloads[0]["side_length"] == 440
    assert payloads[0]["required_depth_mm"] == 450
    assert payloads[0]["mount_type"] == "side_mount"
    assert payloads[0]["product_family"] == "Dynapro SC"
    assert payloads[1]["code"] == "CUSTOM-500"


def test_slide_range_payload_builder_derives_width_deduction_from_clearance():
    payloads = build_slide_range_payloads(
        {
            "brand": "Grass",
            "product_family": "Dynapro SC",
            "mount_type": "side_mount",
            "lengths": [{"length": 500}],
            "side_clearance_total": 26,
        }
    )

    assert payloads[0]["box_width_deduction_mm"] == 52


def test_slide_range_payload_builder_marks_metal_systems_and_lengths():
    payloads = build_slide_range_payloads(
        {
            "brand": "Grass",
            "product_family": "Nova Pro Scala H186",
            "mount_type": "metal_system",
            "lengths": [{"length": 500}],
            "side_clearance_total": 26,
            "drawer_depth_deduction_mm": 0,
            "box_width_deduction_mm": 58,
            "drawer_system_config": {"side_height_mm": 186},
            "accessory_config": {
                "accessories": [
                    {
                        "item_type": "extra",
                        "item_ref_id": "extra-rail",
                        "quantity": 1,
                        "quantity_rule": "per_drawer",
                        "condition": {"field": "metal_side_height", "operator": "greater_than_or_equal", "value_number": 186},
                    }
                ]
            },
        }
    )

    assert payloads[0]["drawer_system_kind"] == "metal"
    assert payloads[0]["mount_type"] == "metal_system"
    assert payloads[0]["drawer_system_config"]["product_family"] == "Nova Pro Scala H186"
    assert payloads[0]["drawer_system_config"]["compatible_nominal_lengths"] == [500]
    assert payloads[0]["accessory_config"]["accessories"][0]["condition"]["field"] == "metal_side_height"


def test_create_slide_range_endpoint_returns_generated_rows():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "brand": "Blum",
        "product_family": "Tandem",
        "mount_type": "undermount",
        "lengths": [{"length": 450}, {"length": 500}],
        "side_clearance_total": 0,
        "drawer_depth_deduction_mm": 10,
        "box_width_deduction_mm": 42,
        "accessory_config": {"accessories": []},
    }
    try:
        response = client.post("/api/v1/libraries/slides/ranges", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["created_count"] == 2
    assert response.json()["slides"][0]["mount_type"] == "undermount"
    assert store.created_payload is not None
    resource, stored_payload = store.created_payload
    assert resource == "slide_range"
    assert stored_payload["brand"] == payload["brand"]
    assert stored_payload["product_family"] == payload["product_family"]
    assert stored_payload["mount_type"] == "undermount"
    assert [row["length"] for row in stored_payload["lengths"]] == [450, 500]


def test_hinge_accessory_config_round_trips():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "brand": "Blum",
        "model": "Clip Top",
        "code": "BL-110",
        "opening_angle_deg": 110,
        "accessory_config": {
            "accessories": [
                {
                    "item_type": "extra",
                    "item_ref_id": "extra-mounting-plate",
                    "quantity": 1,
                    "quantity_rule": "per_hinge",
                    "required": True,
                }
            ]
        },
    }
    try:
        create_response = client.post("/api/v1/libraries/hinges", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["accessory_config"]["accessories"][0]["quantity_rule"] == "per_hinge"
    assert store.created_payload is not None
    resource, stored_payload = store.created_payload
    assert resource == "hinges"
    assert stored_payload["accessory_config"]["accessories"][0]["item_ref_id"] == "extra-mounting-plate"


def test_extra_supplier_must_be_null_or_existing_supplier_id():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    selected_payload = {
        "name": "LED strip",
        "category_id": "category-1",
        "supplier_id": "supplier-1",
        "code": "LED-5M",
        "notes": "Warm white",
    }
    null_payload = {
        "name": "Site delivery",
        "category_id": "category-1",
        "supplier_id": "",
        "code": "DEL",
        "notes": "",
    }
    try:
        selected_response = client.post("/api/v1/libraries/extras", json=selected_payload, headers=auth_header())
        selected_store_payload = store.created_payload
        null_response = client.post("/api/v1/libraries/extras", json=null_payload, headers=auth_header())
        null_store_payload = store.created_payload
        free_text_response = client.post(
            "/api/v1/libraries/extras",
            json={
                "name": "Typed supplier extra",
                "category_id": "category-1",
                "supplier": "Typed Supplier",
                "code": "TS",
                "notes": "",
            },
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert selected_response.status_code == 201
    assert selected_response.json()["supplier_id"] == "supplier-1"
    assert selected_store_payload == ("extras", selected_payload)
    assert null_response.status_code == 201
    assert null_response.json()["supplier_id"] is None
    assert null_store_payload == ("extras", {**null_payload, "supplier_id": None})
    assert free_text_response.status_code == 422


def test_catalog_list_accepts_search_and_recent_filters():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/libraries/boards?search=white&recent_days=14",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.catalog_list_payload == (
        "boards",
        "company-1",
        "white",
        14,
    )


def test_catalog_write_requires_catalog_write_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/handles",
            json={"name": "Cup Pull", "supplier_id": "supplier-1"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: catalog:write"}


def test_catalog_get_returns_404_when_row_is_not_visible():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/boards/missing-board", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_price_list_crud_requires_pricing_permissions():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {"name": "Trade 2026", "status": "draft", "effective_from": None, "effective_to": None}
    try:
        list_response = client.get("/api/v1/libraries/price-lists", headers=auth_header())
        create_response = client.post("/api/v1/libraries/price-lists", json=payload, headers=auth_header())
        price_list_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/price-lists/{price_list_id}", headers=auth_header())
        patch_response = client.patch(
            f"/api/v1/libraries/price-lists/{price_list_id}",
            json={"name": "Trade 2026 Active", "status": "active", "effective_from": None, "effective_to": None},
            headers=auth_header(),
        )
        delete_response = client.delete(f"/api/v1/libraries/price-lists/{price_list_id}", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "active"
    assert delete_response.status_code == 204
    assert store.deleted[-1] == ("price-lists", price_list_id)


def test_item_supplier_crud_and_active_cost_summary():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "item_ref_id": "slide-1",
        "supplier_id": "supplier-1",
        "supplier_sku": "F130107820204",
        "supplier_description": "Dynapro Undermount F/Ext 500mm",
        "price_component": "unit",
        "order_uom": "pairs",
        "is_preferred": True,
        "notes": "",
    }
    try:
        list_response = client.get(
            "/api/v1/libraries/item-suppliers?item_type=slide&item_ref_id=slide-1&search=dynapro&recent_days=30&supplier_id=supplier-1&has_active_cost=true",
            headers=auth_header(),
        )
        create_response = client.post("/api/v1/libraries/item-suppliers", json=payload, headers=auth_header())
        item_supplier_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/item-suppliers/{item_supplier_id}", headers=auth_header())
        patch_response = client.patch(
            f"/api/v1/libraries/item-suppliers/{item_supplier_id}",
            json={**payload, "supplier_description": "Dynapro 500"},
            headers=auth_header(),
        )
        delete_response = client.delete(f"/api/v1/libraries/item-suppliers/{item_supplier_id}", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()[0]["supplier_name"] == "Grass ZA"
    assert list_response.json()[0]["active_unit_cost_cents"] == 47949
    assert store.item_supplier_list_payload == (
        "company-1",
        "slide",
        "slide-1",
        "dynapro",
        30,
        "supplier-1",
        True,
    )
    assert create_response.status_code == 201
    assert create_response.json()["supplier_sku"] == "F130107820204"
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["supplier_description"] == "Dynapro 500"
    assert delete_response.status_code == 204
    assert store.deleted[-1] == ("item-suppliers", item_supplier_id)


def test_item_supplier_write_normalizes_component_and_order_uom_aliases():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "item_ref_id": "slide-1",
        "supplier_id": "supplier-1",
        "supplier_sku": "F130107820204",
        "supplier_description": "Dynapro Undermount F/Ext 500mm",
        "price_component": " Unit ",
        "order_uom": "pair",
        "is_preferred": True,
        "notes": "",
    }
    try:
        response = client.post("/api/v1/libraries/item-suppliers", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert store.item_supplier_payload["price_component"] == "unit"
    assert store.item_supplier_payload["order_uom"] == "pairs"


def test_item_supplier_write_rejects_non_board_price_component():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "item_ref_id": "slide-1",
        "supplier_id": "supplier-1",
        "price_component": "sheet",
        "order_uom": "pairs",
    }
    try:
        response = client.post("/api/v1/libraries/item-suppliers", json=payload, headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "price_component"
    assert "Non-board pricing rows" in response.json()["detail"][0]["msg"]
    assert store.item_supplier_payload is None


def test_supplier_item_cost_create_upsert_and_history():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "list_price_cents": 68498,
        "discount_bps": 3000,
        "unit_cost_cents": 47949,
        "currency_code": "ZAR",
        "source": "spreadsheet",
        "source_ref": "DRAWSLIDES!A19:D19",
    }
    try:
        list_response = client.get("/api/v1/libraries/item-suppliers/item-supplier-1/costs", headers=auth_header())
        history_response = client.get(
            "/api/v1/libraries/item-suppliers/item-supplier-1/costs?include_history=true&as_of=2026-06-12T12:00:00Z",
            headers=auth_header(),
        )
        create_response = client.post(
            "/api/v1/libraries/item-suppliers/item-supplier-1/costs",
            json=payload,
            headers=auth_header(),
        )
        upsert_response = client.post(
            "/api/v1/libraries/item-suppliers/item-supplier-1/costs/upsert",
            json={**payload, "unit_cost_cents": 48000},
            headers=auth_header(),
        )
        get_response = client.get(
            "/api/v1/libraries/item-suppliers/item-supplier-1/costs/supplier-cost-1",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert [row["is_active"] for row in list_response.json()] == [True]
    assert [row["effective_status"] for row in history_response.json()] == ["current", "retired", "future"]
    assert [row["is_current"] for row in history_response.json()] == [True, False, False]
    assert create_response.status_code == 201
    assert create_response.json()["source_ref"] == "DRAWSLIDES!A19:D19"
    assert upsert_response.status_code == 200
    assert upsert_response.json()["unit_cost_cents"] == 48000
    assert get_response.status_code == 200
    assert store.supplier_cost_list_payload == (
        "company-1",
        "item-supplier-1",
        True,
        datetime(2026, 6, 12, 12, 0, tzinfo=UTC),
    )
    assert store.supplier_cost_payload == ("item-supplier-1", {**payload, "unit_cost_cents": 48000, "effective_from": None})


def test_apply_supplier_discount_updates_default_and_active_costs():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "discount_bps": 3500,
        "apply_to_active_costs": True,
        "source": "supplier-discount",
        "source_ref": "libraries-ui",
    }
    try:
        response = client.post(
            "/api/v1/libraries/suppliers/supplier-1/discount",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["supplier_id"] == "supplier-1"
    assert response.json()["discount_bps"] == 3500
    assert response.json()["updated_cost_count"] == 2
    assert store.supplier_discount_payload == ("supplier-1", {**payload, "effective_from": None})


def test_apply_supplier_discount_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/suppliers/supplier-1/discount",
            json={"discount_bps": 3500},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_catalog_bulk_update_previews_and_applies_selected_rows():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "resource": "handles",
        "item_ids": ["handle-1", "handle-2"],
        "updates": {"supplier_id": "supplier-1", "handle_type": "full_length"},
        "confirm": False,
    }
    try:
        preview_response = client.patch(
            "/api/v1/libraries/catalog/bulk-update",
            json=payload,
            headers=auth_header(),
        )
        apply_response = client.patch(
            "/api/v1/libraries/catalog/bulk-update",
            json={**payload, "confirm": True},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert preview_response.status_code == 200
    assert preview_response.json()["confirm"] is False
    assert preview_response.json()["rows"][0]["status"] == "preview"
    assert apply_response.status_code == 200
    assert apply_response.json()["confirm"] is True
    assert apply_response.json()["updated_count"] == 2
    assert store.catalog_bulk_payload == (
        "company-1",
        {**payload, "confirm": True},
    )


def test_catalog_bulk_update_allows_handle_type_and_front_reduction():
    class BulkStore(LibraryStore):
        def _connect(self):
            return nullcontext("connection")

        def _get_catalog_bulk_row_with_conn(self, conn, resource: str, company_id: str, item_id: str) -> dict:
            return handle(item_id)

        def _update_catalog_bulk_row_with_conn(self, conn, resource: str, company_id: str, item_id: str, payload: dict) -> dict:
            return handle(
                item_id,
                name=payload["name"],
                handle_type=payload["handle_type"],
                front_reduction_mm=payload["front_reduction_mm"],
            )

    payload = {
        "resource": "handles",
        "item_ids": ["handle-1"],
        "updates": {"handle_type": "full_length", "front_reduction_mm": 35},
        "confirm": True,
    }

    response = BulkStore(database_url="postgresql://unused").bulk_update_catalog("company-1", payload)

    assert response["updated_count"] == 1
    assert response["rows"][0]["changed_fields"] == ["front_reduction_mm", "handle_type"]


def test_catalog_bulk_update_rejects_empty_selection():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="owner")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/catalog/bulk-update",
            json={"resource": "handles", "item_ids": [], "updates": {"supplier_id": "supplier-1"}},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert store.catalog_bulk_payload is None


def test_catalog_bulk_update_rejects_invalid_board_grain_policy_before_sql():
    store = LibraryStore(database_url="postgresql://unused")

    with pytest.raises(LibraryValidationError, match="Grain policy must be none, optional, or required"):
        store.bulk_update_catalog(
            "company-1",
            {
                "resource": "boards",
                "item_ids": ["board-1"],
                "updates": {"grain_policy": "sometimes"},
            },
        )


def test_catalog_bulk_update_requires_catalog_write_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="viewer")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/catalog/bulk-update",
            json={"resource": "handles", "item_ids": ["handle-1"], "updates": {"supplier_id": "supplier-1"}},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: catalog:write"}


def test_calculate_discounted_supplier_cost_rounds_to_cents():
    assert _calculate_discounted_cost_cents(68498, 3000) == 47949
    assert _calculate_discounted_cost_cents(68498, 10000) == 0


def test_effective_status_distinguishes_current_future_and_retired_prices():
    assert _effective_status(datetime(2026, 5, 1, tzinfo=UTC), None, NOW) == "current"
    assert _effective_status(datetime(2026, 6, 30, tzinfo=UTC), None, NOW) == "future"
    assert _effective_status(datetime(2026, 5, 1, tzinfo=UTC), datetime(2026, 5, 20, tzinfo=UTC), NOW) == "retired"
    assert _effective_status(datetime(2026, 5, 1, tzinfo=UTC), datetime(2026, 6, 30, tzinfo=UTC), NOW) == "current"


def test_supplier_cost_normalization_rejects_sheet_component_for_sqm_board():
    store = PricingValidationStore({("board", "board-1"): {**board("board-1"), "costing_mode": "sqm"}})
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "supplier_id": "supplier-1",
        "price_component": "sheet",
        "order_uom": "sheet",
    }

    with pytest.raises(LibraryValidationError) as exc_info:
        store._normalize_item_supplier_payload("company-1", payload)

    assert exc_info.value.field_errors[0]["loc"] == ["body", "price_component"]
    assert "not allowed for sqm board pricing" in exc_info.value.field_errors[0]["msg"]


def test_price_item_normalization_accepts_sheet_board_edging_aliases():
    store = PricingValidationStore({("board", "board-1"): board("board-1")})
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "price_component": "edging metre",
        "uom": "metre",
        "unit_price_cents": 1800,
    }

    data = store._normalize_price_item_payload("company-1", payload)

    assert data["item_key"] == "board::board-1"
    assert data["price_component"] == "edging_m"
    assert data["uom"] == "m"


def test_generate_price_list_from_supplier_costs():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "selection_mode": "preferred_then_cheapest",
        "item_types": ["slide", "hinge"],
        "preserve_manual_overrides": True,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/generate-from-supplier-costs",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["created_count"] == 1
    assert response.json()["updated_count"] == 1
    assert store.generation_payload == ("price-list-1", {**payload, "effective_from": None})


def test_generate_price_list_from_supplier_costs_accepts_refresh_effective_date():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "selection_mode": "preferred_only",
        "item_types": ["slide"],
        "preserve_manual_overrides": True,
        "effective_from": "2026-07-01T08:00:00Z",
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/generate-from-supplier-costs",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.generation_payload == (
        "price-list-1",
        {
            "selection_mode": "preferred_only",
            "item_types": ["slide"],
            "preserve_manual_overrides": True,
            "effective_from": datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        },
    )


def test_get_active_price_list():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/price-lists/active", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == "price-list-1"
    assert store.active_price_list_requested


def test_estimator_cannot_update_price_lists():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.post(
            "/api/v1/libraries/price-lists",
            json={"name": "Trade 2026", "status": "draft"},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_pricing_settings_read_and_update():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        read_response = client.get("/api/v1/libraries/pricing-settings", headers=auth_header())
        update_response = client.patch(
            "/api/v1/libraries/pricing-settings",
            json={"vat_rate_bps": 1550, "default_markup_bps": 3000},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert read_response.json()["vat_rate_bps"] == 1500
    assert update_response.status_code == 200
    assert update_response.json()["vat_rate_bps"] == 1550
    assert update_response.json()["default_markup_bps"] == 3000
    assert store.pricing_settings_payload["vat_rate_bps"] == 1550
    assert store.pricing_settings_payload["default_markup_bps"] == 3000
    assert store.pricing_settings_payload["carcass_markup_bps"] == 2500


def test_pricing_settings_update_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/pricing-settings",
            json={"vat_rate_bps": 1550, "default_markup_bps": 3000},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_price_list_item_crud():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "item_ref_id": None,
        "item_key": "slide::Blum::Movento::MOV-500::500",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 14500,
    }
    try:
        list_response = client.get("/api/v1/libraries/price-lists/price-list-1/items", headers=auth_header())
        history_response = client.get(
            "/api/v1/libraries/price-lists/price-list-1/items?include_history=true&as_of=2026-06-12T12:00:00Z",
            headers=auth_header(),
        )
        create_response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
        item_id = create_response.json()["id"]
        get_response = client.get(f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}", headers=auth_header())
        patch_response = client.patch(
            f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}",
            json={**payload, "unit_price_cents": 15500},
            headers=auth_header(),
        )
        delete_response = client.delete(
            f"/api/v1/libraries/price-lists/price-list-1/items/{item_id}",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert [row["is_active"] for row in list_response.json()] == [True]
    assert [row["effective_status"] for row in history_response.json()] == ["current", "retired", "future"]
    assert [row["is_current"] for row in history_response.json()] == [True, False, False]
    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["unit_price_cents"] == 15500
    assert patch_response.json()["id"] != item_id
    assert patch_response.json()["replaces_id"] == item_id
    assert patch_response.json()["is_active"] is True
    assert patch_response.json()["effective_status"] == "current"
    assert delete_response.status_code == 204
    assert store.price_item_list_payload == (
        "company-1",
        "price-list-1",
        True,
        datetime(2026, 6, 12, 12, 0, tzinfo=UTC),
        None,
        None,
        None,
        None,
    )
    assert store.price_item_deleted == ("company-1", "price-list-1", item_id)


def test_price_list_items_accept_search_status_and_recent_filters():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get(
            "/api/v1/libraries/price-lists/price-list-1/items?include_history=true&search=handle&item_type=handle&effective_status=current&recent_days=14",
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.price_item_list_payload == (
        "company-1",
        "price-list-1",
        True,
        None,
        "handle",
        "handle",
        "current",
        14,
    )


def test_price_list_coverage_returns_quote_context_and_groups():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/price-lists/price-list-1/coverage", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["price_list_id"] == "price-list-1"
    assert payload["covered_count"] == 1
    assert payload["missing_count"] == 1
    assert [group["item_type"] for group in payload["groups"]] == ["slide", "handle"]
    assert payload["groups"][0]["rows"][0]["used_in"][0]["project_name"] == "Smith Kitchen"
    assert payload["groups"][1]["rows"][0]["status"] == "missing"
    assert store.price_coverage_payload == ("company-1", "price-list-1")


def test_price_list_coverage_requires_pricing_read_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="production")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.get("/api/v1/libraries/price-lists/price-list-1/coverage", headers=auth_header())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:read"}
    assert store.price_coverage_payload is None


def test_bulk_price_update_previews_and_applies_selected_rows():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_ids": ["price-item-1"],
        "unit_price_cents": 13200,
        "cost_source": "override",
        "confirm": False,
    }
    try:
        preview_response = client.patch(
            "/api/v1/libraries/price-lists/price-list-1/items/bulk-update",
            json=payload,
            headers=auth_header(),
        )
        apply_response = client.patch(
            "/api/v1/libraries/price-lists/price-list-1/items/bulk-update",
            json={**payload, "confirm": True},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert preview_response.status_code == 200
    assert preview_response.json()["confirm"] is False
    assert preview_response.json()["rows"][0]["status"] == "preview"
    assert apply_response.status_code == 200
    assert apply_response.json()["confirm"] is True
    assert apply_response.json()["updated_count"] == 1
    assert store.price_item_bulk_update_payload == (
        "company-1",
        "price-list-1",
        {**payload, "confirm": True, "uom": None},
    )


def test_bulk_price_update_rejects_empty_update_fields():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/price-lists/price-list-1/items/bulk-update",
            json={"item_ids": ["price-item-1"]},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert store.price_item_bulk_update_payload is None


def test_bulk_price_update_requires_pricing_update_permission():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="estimator")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    try:
        response = client.patch(
            "/api/v1/libraries/price-lists/price-list-1/items/bulk-update",
            json={"item_ids": ["price-item-1"], "unit_price_cents": 13200},
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: pricing:update"}


def test_price_list_item_upsert_with_item_ref_id():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "price_component": "sheet",
        "uom": "sheet",
        "unit_price_cents": 359900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items/upsert",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item_key"] == "board::board-1"
    assert response.json()["item_ref_id"] == "board-1"
    assert response.json()["price_component"] == "sheet"
    assert store.price_item_payload == (
        "price-list-1",
        {
            **payload,
            "effective_from": None,
            "item_key": None,
            "source_supplier_item_cost_id": None,
            "cost_source": "manual",
        },
    )


def test_price_list_item_upsert_normalizes_board_sqm_aliases():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "price_component": "sq m",
        "uom": "sqm",
        "unit_price_cents": 18500,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items/upsert",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.price_item_payload[1]["price_component"] == "sqm"
    assert store.price_item_payload[1]["uom"] == "m2"


def test_price_list_item_upsert_rejects_component_uom_mismatch():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "board",
        "item_ref_id": "board-1",
        "price_component": "sheet",
        "uom": "m",
        "unit_price_cents": 359900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items/upsert",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "uom"
    assert "does not match price_component sheet" in response.json()["detail"][0]["msg"]
    assert store.price_item_payload is None


def test_price_list_item_create_with_item_ref_id():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "extra",
        "item_ref_id": "extra-1",
        "price_component": "unit",
        "uom": "pcs",
        "unit_price_cents": 9900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["item_key"] == "extra::extra-1"
    assert response.json()["item_ref_id"] == "extra-1"
    assert store.price_item_payload == (
        "price-list-1",
        {
            **payload,
            "effective_from": None,
            "item_key": None,
            "source_supplier_item_cost_id": None,
            "cost_source": "manual",
        },
    )


def test_price_list_item_write_rejects_missing_item_identity():
    store = FakeLibraryStore()
    app.dependency_overrides[auth.get_auth_store] = lambda: FakeAuthStore(role="manager")
    app.dependency_overrides[libraries.get_library_store] = lambda: store
    payload = {
        "item_type": "slide",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 14900,
    }
    try:
        response = client.post(
            "/api/v1/libraries/price-lists/price-list-1/items",
            json=payload,
            headers=auth_header(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Either item_ref_id or item_key is required"}


def _xlsx_base64(rows: list[list[str]]) -> str:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
              <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
            </Relationships>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>{''.join(_xlsx_row(index, row) for index, row in enumerate(rows, start=1))}</sheetData>
            </worksheet>
            """,
        )
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _xlsx_row(row_number: int, values: list[str]) -> str:
    cells = "".join(
        f'<c r="{chr(ord("A") + index)}{row_number}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        for index, value in enumerate(values)
    )
    return f'<row r="{row_number}">{cells}</row>'


def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
