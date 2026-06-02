from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile

import psycopg
from psycopg.rows import dict_row

from corequote_api.libraries import LibraryNotFound, LibraryStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKBOOK = REPO_ROOT / "docs/guidelines/FLIP QUOTE UPDATED prices- SHAUN MAY 2026.xlsx"
DEFAULT_COMPANY_NAME = "CoreQuote Test Co"
DEFAULT_SUPPLIER_NAME = "Grass ZA"
DEFAULT_PRICE_LIST_NAME = "Supplier Cost Import"
NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass(frozen=True)
class GrassHardwareRow:
    item_type: str
    brand: str
    model: str
    code: str
    nominal_length: int
    side_length: int
    side_clearance_total: int
    side_height_uplift: int
    opening_angle_deg: int
    supplier_sku: str
    supplier_description: str
    price_component: str
    order_uom: str
    list_price_cents: int
    discount_bps: int
    unit_cost_cents: int
    source_ref: str


class XlsxWorkbook:
    def __init__(self, path: Path):
        self.path = path
        self._zip = ZipFile(path)
        self._shared_strings = self._load_shared_strings()
        self._sheet_paths = self._load_sheet_paths()

    def close(self) -> None:
        self._zip.close()

    def rows(self, sheet_name: str) -> list[dict[int, Any]]:
        sheet_path = self._sheet_paths[sheet_name]
        root = ElementTree.fromstring(self._zip.read(sheet_path))
        result: list[dict[int, Any]] = []
        for row in root.findall(".//main:sheetData/main:row", NS):
            values: dict[int, Any] = {}
            for cell in row.findall("main:c", NS):
                reference = cell.attrib.get("r", "")
                column = _column_index(reference)
                if column <= 0:
                    continue
                value = self._cell_value(cell)
                if value is not None:
                    values[column] = value
            result.append(values)
        return result

    def _load_shared_strings(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self._zip.namelist():
            return []
        root = ElementTree.fromstring(self._zip.read("xl/sharedStrings.xml"))
        strings: list[str] = []
        for item in root.findall("main:si", NS):
            text_parts = [node.text or "" for node in item.findall(".//main:t", NS)]
            strings.append("".join(text_parts))
        return strings

    def _load_sheet_paths(self) -> dict[str, str]:
        workbook = ElementTree.fromstring(self._zip.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(self._zip.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall("pkgrel:Relationship", NS)
        }

        paths: dict[str, str] = {}
        for sheet in workbook.findall(".//main:sheets/main:sheet", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
            target = relationship_targets[rel_id]
            paths[name] = "xl/" + target.lstrip("/")
        return paths

    def _cell_value(self, cell) -> Any:
        value_node = cell.find("main:v", NS)
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            text_node = cell.find(".//main:t", NS)
            return text_node.text if text_node is not None else None
        if value_node is None or value_node.text is None:
            return None
        raw_value = value_node.text
        if cell_type == "s":
            try:
                return self._shared_strings[int(raw_value)]
            except (IndexError, ValueError):
                return None
        if cell_type == "str":
            return raw_value
        return _parse_number(raw_value)


def parse_grass_rows(workbook_path: Path) -> list[GrassHardwareRow]:
    workbook = XlsxWorkbook(workbook_path)
    try:
        return [*parse_drawslides(workbook), *parse_hinges(workbook)]
    finally:
        workbook.close()


def parse_drawslides(workbook: XlsxWorkbook) -> list[GrassHardwareRow]:
    rows: list[GrassHardwareRow] = []
    for row_number, row in enumerate(workbook.rows("DRAWSLIDES"), start=1):
        name = _clean_text(row.get(1))
        if not name.upper().startswith("GRASS "):
            continue
        list_price_cents = _money_to_cents(row.get(3))
        unit_cost_cents = _money_to_cents(row.get(4))
        if unit_cost_cents <= 0:
            continue
        nominal_length = _extract_last_int(name) or _positive_int(row.get(9)) or _positive_int(row.get(8))
        side_length = _positive_int(row.get(8)) or nominal_length
        side_clearance_total = _positive_abs_int(row.get(12)) or _positive_abs_int(row.get(7))
        supplier_sku = _clean_text(row.get(13))
        model = name.removeprefix("GRASS ").strip()
        rows.append(
            GrassHardwareRow(
                item_type="slide",
                brand="Grass",
                model=model,
                code=supplier_sku,
                nominal_length=nominal_length,
                side_length=side_length,
                side_clearance_total=side_clearance_total,
                side_height_uplift=0,
                opening_angle_deg=0,
                supplier_sku=supplier_sku,
                supplier_description=name,
                price_component="unit",
                order_uom="pairs",
                list_price_cents=list_price_cents,
                discount_bps=_discount_bps(list_price_cents, unit_cost_cents),
                unit_cost_cents=unit_cost_cents,
                source_ref=f"DRAWSLIDES!A{row_number}:D{row_number}",
            )
        )
    return rows


def parse_hinges(workbook: XlsxWorkbook) -> list[GrassHardwareRow]:
    rows: list[GrassHardwareRow] = []
    for row_number, row in enumerate(workbook.rows("HINGESFLAPS"), start=1):
        name = _clean_text(row.get(1))
        if not name.upper().startswith("GRASS "):
            continue
        list_price_cents = _money_to_cents(row.get(3))
        unit_cost_cents = _money_to_cents(row.get(4))
        if unit_cost_cents <= 0:
            continue
        model = name.removeprefix("GRASS ").strip()
        rows.append(
            GrassHardwareRow(
                item_type="hinge",
                brand="Grass",
                model=model,
                code="",
                nominal_length=0,
                side_length=0,
                side_clearance_total=0,
                side_height_uplift=0,
                opening_angle_deg=_extract_first_int(model) or 0,
                supplier_sku="",
                supplier_description=name,
                price_component="unit",
                order_uom="pcs",
                list_price_cents=list_price_cents,
                discount_bps=_discount_bps(list_price_cents, unit_cost_cents),
                unit_cost_cents=unit_cost_cents,
                source_ref=f"HINGESFLAPS!A{row_number}:D{row_number}",
            )
        )
    return rows


def import_grass_hardware(
    *,
    company_id: str,
    database_url: str,
    rows: list[GrassHardwareRow],
    supplier_name: str,
    generate_price_list: bool,
    price_list_name: str,
) -> dict[str, int | str]:
    store = LibraryStore(database_url)
    supplier = _get_or_create_supplier(store, company_id, supplier_name)
    created_items = 0
    updated_items = 0
    created_links = 0
    updated_links = 0
    upserted_costs = 0

    for row in rows:
        item, item_created = _upsert_catalog_item(store, company_id, row)
        created_items += int(item_created)
        updated_items += int(not item_created)
        link, link_created = _upsert_item_supplier(store, company_id, row, item["id"], supplier["id"])
        created_links += int(link_created)
        updated_links += int(not link_created)
        store.upsert_supplier_item_cost(
            company_id,
            link["id"],
            {
                "list_price_cents": row.list_price_cents,
                "discount_bps": row.discount_bps,
                "unit_cost_cents": row.unit_cost_cents,
                "currency_code": _company_currency(database_url, company_id),
                "source": "spreadsheet",
                "source_ref": row.source_ref,
                "effective_from": None,
            },
        )
        upserted_costs += 1

    generated_count = 0
    price_list_id = ""
    if generate_price_list:
        price_list = _get_or_create_active_price_list(store, company_id, price_list_name)
        price_list_id = price_list["id"]
        summary = store.generate_price_list_from_supplier_costs(
            company_id,
            price_list_id,
            {
                "selection_mode": "preferred_then_cheapest",
                "item_types": ["slide", "hinge"],
                "preserve_manual_overrides": True,
            },
        )
        generated_count = int(summary["generated_count"])

    return {
        "supplier_id": supplier["id"],
        "rows": len(rows),
        "created_items": created_items,
        "updated_items": updated_items,
        "created_links": created_links,
        "updated_links": updated_links,
        "upserted_costs": upserted_costs,
        "generated_price_items": generated_count,
        "price_list_id": price_list_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Grass slides and hinges from the quote workbook.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--company-id")
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
    parser.add_argument("--supplier-name", default=DEFAULT_SUPPLIER_NAME)
    parser.add_argument("--price-list-name", default=DEFAULT_PRICE_LIST_NAME)
    parser.add_argument("--generate-price-list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    rows = parse_grass_rows(args.workbook)
    company_id = args.company_id or _resolve_company_id(database_url, args.company_name)

    if args.dry_run:
        print(f"Would import {len(rows)} Grass hardware rows for company {company_id}.")
        print(f"Slides: {sum(1 for row in rows if row.item_type == 'slide')}")
        print(f"Hinges: {sum(1 for row in rows if row.item_type == 'hinge')}")
        return

    summary = import_grass_hardware(
        company_id=company_id,
        database_url=database_url,
        rows=rows,
        supplier_name=args.supplier_name,
        generate_price_list=args.generate_price_list,
        price_list_name=args.price_list_name,
    )
    for key, value in summary.items():
        print(f"{key}: {value}")


def _get_or_create_supplier(store: LibraryStore, company_id: str, supplier_name: str) -> dict:
    clean_name = supplier_name.strip()
    for supplier in store.list_suppliers(company_id):
        if supplier["name"].casefold() == clean_name.casefold():
            return supplier
    return store.create_supplier(
        company_id,
        {
            "name": clean_name,
            "code": "GRASS-ZA",
            "contact_name": "",
            "email": "",
            "phone": "",
            "notes": "Imported Grass hardware supplier.",
        },
    )


def _upsert_catalog_item(store: LibraryStore, company_id: str, row: GrassHardwareRow) -> tuple[dict, bool]:
    if row.item_type == "slide":
        payload = {
            "brand": row.brand,
            "model": row.model,
            "code": row.code,
            "length": row.nominal_length,
            "side_length": row.side_length,
            "side_clearance_total": row.side_clearance_total,
            "side_height_uplift": row.side_height_uplift,
        }
        existing = _find_catalog_item(store.list_slides(company_id), payload)
        if existing:
            return store.update_slide(company_id, existing["id"], payload), False
        return store.create_slide(company_id, payload), True

    payload = {
        "brand": row.brand,
        "model": row.model,
        "code": row.code,
        "opening_angle_deg": row.opening_angle_deg,
    }
    existing = _find_catalog_item(store.list_hinges(company_id), payload)
    if existing:
        return store.update_hinge(company_id, existing["id"], payload), False
    return store.create_hinge(company_id, payload), True


def _upsert_item_supplier(
    store: LibraryStore,
    company_id: str,
    row: GrassHardwareRow,
    item_ref_id: str,
    supplier_id: str,
) -> tuple[dict, bool]:
    payload = {
        "item_type": row.item_type,
        "item_ref_id": item_ref_id,
        "supplier_id": supplier_id,
        "supplier_sku": row.supplier_sku,
        "supplier_description": row.supplier_description,
        "price_component": row.price_component,
        "order_uom": row.order_uom,
        "is_preferred": True,
        "notes": row.source_ref,
    }
    existing = next(
        (
            item
            for item in store.list_item_suppliers(company_id, item_type=row.item_type, item_ref_id=item_ref_id)
            if item["supplier_id"] == supplier_id
            and item["supplier_sku"] == row.supplier_sku
            and item["price_component"] == row.price_component
        ),
        None,
    )
    if existing:
        return store.update_item_supplier(company_id, existing["id"], payload), False
    return store.create_item_supplier(company_id, payload), True


def _get_or_create_active_price_list(store: LibraryStore, company_id: str, name: str) -> dict:
    try:
        return store.get_active_price_list(company_id)
    except LibraryNotFound:
        return store.create_price_list(
            company_id,
            {
                "name": name,
                "status": "active",
                "effective_from": None,
                "effective_to": None,
            },
        )


def _find_catalog_item(rows: list[dict], payload: dict[str, Any]) -> dict | None:
    for row in rows:
        if (
            row["brand"].casefold() == payload["brand"].casefold()
            and row["model"].casefold() == payload["model"].casefold()
            and row.get("code", "").casefold() == payload.get("code", "").casefold()
        ):
            return row
    return None


def _resolve_company_id(database_url: str, company_name: str) -> str:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        row = conn.execute(
            """
            SELECT id::text
            FROM companies
            WHERE id::text = %s
               OR name = %s
               OR slug = %s
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (company_name, company_name, company_name),
        ).fetchone()
    if not row:
        raise SystemExit(f"Company not found: {company_name}")
    return row["id"]


def _company_currency(database_url: str, company_id: str) -> str:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT currency_code FROM companies WHERE id = %s",
            (company_id,),
        ).fetchone()
    return str(row["currency_code"] if row else "ZAR")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_number(value: str) -> Any:
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        return value
    if decimal == decimal.to_integral_value():
        return int(decimal)
    return float(decimal)


def _money_to_cents(value: Any) -> int:
    if value in (None, ""):
        return 0
    decimal = Decimal(str(value))
    return int((decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _discount_bps(list_price_cents: int, unit_cost_cents: int) -> int:
    if list_price_cents <= 0 or unit_cost_cents >= list_price_cents:
        return 0
    discount = Decimal(list_price_cents - unit_cost_cents) / Decimal(list_price_cents)
    return int((discount * 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    result = 0
    for char in letters.upper():
        result = result * 26 + (ord(char) - ord("A") + 1)
    return result


def _extract_first_int(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _extract_last_int(value: str) -> int | None:
    matches = re.findall(r"\d+", value)
    return int(matches[-1]) if matches else None


def _positive_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def _positive_abs_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return abs(int(round(float(value))))
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    main()
