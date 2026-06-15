from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO, StringIO
import re
from typing import Any, Literal
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


ImportResource = Literal[
    "boards",
    "slides",
    "hinges",
    "handles",
    "suppliers",
    "extra_categories",
    "extras",
    "supplier_item_costs",
    "price_list_items",
]
ImportSourceFormat = Literal["csv", "tsv", "xlsx"]
ImportRowStatus = Literal["create", "update", "skipped", "duplicate", "blocked"]
ImportProblemSeverity = Literal["error", "warning"]

XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

ALLOWED_ITEM_TYPES = {"board", "slide", "hinge", "handle", "extra"}
ALLOWED_UOMS = {"sheet", "m2", "m", "board", "pcs", "pairs", "pair", "each", "unit", "set", "day", "trip"}
ALLOWED_COSTING_MODES = {"sheet", "sqm"}
ALLOWED_GRAIN_POLICIES = {"none", "optional", "required"}


@dataclass(frozen=True)
class ImportField:
    key: str
    label: str
    aliases: tuple[str, ...]
    required: bool = False


@dataclass(frozen=True)
class ImportSpec:
    resource: ImportResource
    label: str
    fields: tuple[ImportField, ...]


RESOURCE_SPECS: dict[ImportResource, ImportSpec] = {
    "boards": ImportSpec(
        resource="boards",
        label="Boards",
        fields=(
            ImportField("brand", "Brand", ("brand", "board brand", "supplier brand", "product brand"), True),
            ImportField("material", "Material", ("material", "board material", "description", "board", "colour"), True),
            ImportField("thickness", "Thickness", ("thickness", "thickness mm", "thickness_mm", "thick"), True),
            ImportField("length_mm", "Length", ("length", "length mm", "length_mm", "sheet length"), True),
            ImportField("width_mm", "Width", ("width", "width mm", "width_mm", "sheet width"), True),
            ImportField("costing_mode", "Costing mode", ("costing mode", "costing_mode", "pricing mode")),
            ImportField("grain_policy", "Grain policy", ("grain policy", "grain_policy", "grain", "grain required")),
        ),
    ),
    "slides": ImportSpec(
        resource="slides",
        label="Drawer slides",
        fields=(
            ImportField("brand", "Brand", ("brand", "slide brand", "supplier brand"), True),
            ImportField("model", "Model", ("model", "description", "slide model", "name"), True),
            ImportField("code", "Code", ("code", "sku", "item code", "supplier sku")),
            ImportField("length", "Length", ("length", "nominal length", "length mm"), True),
            ImportField("side_length", "Side length", ("side length", "side_length", "runner length")),
            ImportField("side_clearance_total", "Side clearance", ("side clearance", "side_clearance_total", "clearance")),
            ImportField("side_height_uplift", "Side uplift", ("side uplift", "side_height_uplift", "uplift")),
        ),
    ),
    "hinges": ImportSpec(
        resource="hinges",
        label="Hinges",
        fields=(
            ImportField("brand", "Brand", ("brand", "hinge brand", "supplier brand"), True),
            ImportField("model", "Model", ("model", "description", "hinge model", "name"), True),
            ImportField("code", "Code", ("code", "sku", "item code", "supplier sku")),
            ImportField("opening_angle_deg", "Opening angle", ("opening angle", "opening angle deg", "opening_angle_deg", "angle")),
        ),
    ),
    "handles": ImportSpec(
        resource="handles",
        label="Handles",
        fields=(
            ImportField("name", "Name", ("name", "handle", "description", "model"), True),
            ImportField("supplier", "Supplier", ("supplier", "supplier name", "vendor")),
            ImportField("code", "Code", ("code", "sku", "item code", "supplier sku")),
        ),
    ),
    "suppliers": ImportSpec(
        resource="suppliers",
        label="Suppliers",
        fields=(
            ImportField("name", "Name", ("name", "supplier", "supplier name", "vendor"), True),
            ImportField("code", "Code", ("code", "supplier code", "account code")),
            ImportField("contact_name", "Contact", ("contact", "contact name", "rep")),
            ImportField("email", "Email", ("email", "email address")),
            ImportField("phone", "Phone", ("phone", "telephone", "mobile")),
            ImportField("notes", "Notes", ("notes", "comment", "comments")),
            ImportField("default_discount_bps", "Default discount", ("default discount", "discount", "discount %", "discount_bps")),
        ),
    ),
    "extra_categories": ImportSpec(
        resource="extra_categories",
        label="Extra categories",
        fields=(ImportField("name", "Name", ("name", "category", "extra category"), True),),
    ),
    "extras": ImportSpec(
        resource="extras",
        label="Extras",
        fields=(
            ImportField("name", "Name", ("name", "extra", "description"), True),
            ImportField("category_id", "Category ID", ("category id", "category_id")),
            ImportField("category_name", "Category", ("category", "category name", "extra category"), True),
            ImportField("supplier", "Supplier", ("supplier", "supplier name", "vendor")),
            ImportField("code", "Code", ("code", "sku", "item code")),
            ImportField("notes", "Notes", ("notes", "comment", "comments")),
        ),
    ),
    "supplier_item_costs": ImportSpec(
        resource="supplier_item_costs",
        label="Supplier item costs",
        fields=(
            ImportField("item_type", "Item type", ("item type", "item_type", "type"), True),
            ImportField("item_ref_id", "Item ID", ("item id", "item_ref_id", "item uuid")),
            ImportField("item_key", "Item key", ("item key", "item_key")),
            ImportField("brand", "Brand", ("brand", "product brand")),
            ImportField("model", "Model", ("model", "material", "description", "name")),
            ImportField("code", "Code", ("code", "sku", "item code")),
            ImportField("thickness", "Board thickness", ("thickness", "thickness mm", "thickness_mm")),
            ImportField("length_mm", "Board length", ("length", "length mm", "length_mm", "sheet length")),
            ImportField("width_mm", "Board width", ("width", "width mm", "width_mm", "sheet width")),
            ImportField("category_name", "Extra category", ("category", "category name", "extra category")),
            ImportField("supplier_id", "Supplier ID", ("supplier id", "supplier_id")),
            ImportField("supplier_name", "Supplier", ("supplier", "supplier name", "vendor"), True),
            ImportField("supplier_sku", "Supplier SKU", ("supplier sku", "supplier_sku", "sku", "code")),
            ImportField("supplier_description", "Supplier description", ("supplier description", "description", "name")),
            ImportField("price_component", "Price component", ("price component", "component", "price_component")),
            ImportField("order_uom", "Order unit", ("order uom", "order_uom", "uom", "unit"), True),
            ImportField("list_price_cents", "List price", ("list price", "list_price", "list price cents", "list_price_cents")),
            ImportField("discount_bps", "Discount", ("discount", "discount %", "discount_bps")),
            ImportField("unit_cost_cents", "Net cost", ("net cost", "unit cost", "unit_cost", "unit_cost_cents", "cost"), True),
            ImportField("currency_code", "Currency", ("currency", "currency code", "currency_code")),
        ),
    ),
    "price_list_items": ImportSpec(
        resource="price_list_items",
        label="Price list rows",
        fields=(
            ImportField("item_type", "Item type", ("item type", "item_type", "type"), True),
            ImportField("item_ref_id", "Item ID", ("item id", "item_ref_id", "item uuid")),
            ImportField("item_key", "Item key", ("item key", "item_key")),
            ImportField("brand", "Brand", ("brand", "product brand")),
            ImportField("model", "Model", ("model", "material", "description", "name")),
            ImportField("code", "Code", ("code", "sku", "item code")),
            ImportField("supplier_name", "Supplier", ("supplier", "supplier name", "vendor")),
            ImportField("thickness", "Board thickness", ("thickness", "thickness mm", "thickness_mm")),
            ImportField("length_mm", "Board length", ("length", "length mm", "length_mm", "sheet length")),
            ImportField("width_mm", "Board width", ("width", "width mm", "width_mm", "sheet width")),
            ImportField("category_name", "Extra category", ("category", "category name", "extra category")),
            ImportField("price_component", "Price component", ("price component", "component", "price_component"), True),
            ImportField("uom", "Unit", ("uom", "unit", "price unit"), True),
            ImportField("unit_price_cents", "Price", ("price", "unit price", "unit_price", "unit_price_cents", "sell price"), True),
            ImportField("cost_source", "Source", ("source", "cost source", "cost_source")),
        ),
    ),
}


def build_import_preview(request: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
    resource = _resource(request.get("resource"))
    spec = RESOURCE_SPECS[resource]
    rows, columns, sheet_name = _parse_source(
        request.get("source_format") or "csv",
        str(request.get("content") or ""),
        sheet_name=request.get("sheet_name"),
    )
    column_mapping = _clean_column_mapping(request.get("column_mapping") or {})
    mapped_fields = _mapped_fields(spec, columns, column_mapping)

    preview_rows: list[dict[str, Any]] = []
    seen_identities: dict[str, int] = {}
    for row in rows:
        preview = _preview_row(spec, row, mapped_fields, references, seen_identities)
        preview_rows.append(preview)

    summary = {
        "total_rows": len(preview_rows),
        "create_count": _count_status(preview_rows, "create"),
        "update_count": _count_status(preview_rows, "update"),
        "skipped_count": _count_status(preview_rows, "skipped"),
        "duplicate_count": _count_status(preview_rows, "duplicate"),
        "blocked_count": _count_status(preview_rows, "blocked"),
    }
    return {
        "resource": resource,
        "source_format": request.get("source_format") or "csv",
        "sheet_name": sheet_name,
        "columns": columns,
        "mapped_fields": [
            {
                "field": field["field"],
                "label": field["label"],
                "source_column": field["source_column"],
                "required": field["required"],
            }
            for field in mapped_fields
        ],
        "summary": summary,
        "rows": preview_rows,
    }


def _resource(value: Any) -> ImportResource:
    resource = str(value or "").strip().lower().replace("-", "_")
    if resource not in RESOURCE_SPECS:
        raise ValueError("Choose a supported import type.")
    return resource  # type: ignore[return-value]


def _parse_source(
    source_format: str,
    content: str,
    *,
    sheet_name: str | None,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    source_format = source_format.strip().lower()
    if source_format not in {"csv", "tsv", "xlsx"}:
        raise ValueError("Choose CSV, TSV, or XLSX as the import format.")
    if not content.strip():
        raise ValueError("Add pasted rows or upload a file before previewing.")
    if source_format == "xlsx":
        return _parse_xlsx_source(content, sheet_name=sheet_name)
    delimiter = "\t" if source_format == "tsv" else _sniff_delimiter(content)
    reader = csv.DictReader(StringIO(content), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("The import needs a header row with column names.")
    columns = [_clean_header_name(column) for column in reader.fieldnames if _clean_header_name(column)]
    rows = [
        {
            "row_number": index,
            "values": {_clean_header_name(key): value for key, value in row.items() if key is not None},
        }
        for index, row in enumerate(reader, start=2)
    ]
    return rows, columns, None


def _parse_xlsx_source(content: str, *, sheet_name: str | None) -> tuple[list[dict[str, Any]], list[str], str | None]:
    try:
        workbook = XlsxImportWorkbook(base64.b64decode(content))
    except (ValueError, BadZipFile) as exc:
        raise ValueError("Upload a valid XLSX workbook.") from exc
    try:
        if not workbook.sheet_names:
            raise ValueError("The uploaded workbook does not contain any sheets.")
        selected_sheet = sheet_name.strip() if isinstance(sheet_name, str) and sheet_name.strip() else workbook.sheet_names[0]
        raw_rows = workbook.rows(selected_sheet)
    finally:
        workbook.close()

    header_index = next((index for index, row in enumerate(raw_rows) if row), None)
    if header_index is None:
        raise ValueError("The selected workbook sheet is empty.")
    headers_by_column = {
        column: _clean_header_name(value)
        for column, value in raw_rows[header_index].items()
        if _clean_header_name(value)
    }
    if not headers_by_column:
        raise ValueError("The selected workbook sheet needs a header row with column names.")

    rows: list[dict[str, Any]] = []
    for offset, row in enumerate(raw_rows[header_index + 1 :], start=header_index + 2):
        values = {
            headers_by_column[column]: value
            for column, value in row.items()
            if column in headers_by_column
        }
        rows.append({"row_number": offset, "values": values})
    return rows, list(headers_by_column.values()), selected_sheet


class XlsxImportWorkbook:
    def __init__(self, data: bytes):
        self._zip = ZipFile(BytesIO(data))
        self._shared_strings = self._load_shared_strings()
        self._sheet_paths = self._load_sheet_paths()
        self.sheet_names = list(self._sheet_paths.keys())

    def close(self) -> None:
        self._zip.close()

    def rows(self, sheet_name: str) -> list[dict[int, Any]]:
        if sheet_name not in self._sheet_paths:
            raise ValueError(f"Workbook sheet not found: {sheet_name}")
        root = ElementTree.fromstring(self._zip.read(self._sheet_paths[sheet_name]))
        result: list[dict[int, Any]] = []
        for row in root.findall(".//main:sheetData/main:row", XLSX_NS):
            values: dict[int, Any] = {}
            for cell in row.findall("main:c", XLSX_NS):
                column = _column_index(cell.attrib.get("r", ""))
                value = self._cell_value(cell)
                if column > 0 and value is not None:
                    values[column] = value
            result.append(values)
        return result

    def _load_shared_strings(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self._zip.namelist():
            return []
        root = ElementTree.fromstring(self._zip.read("xl/sharedStrings.xml"))
        strings: list[str] = []
        for item in root.findall("main:si", XLSX_NS):
            strings.append("".join(node.text or "" for node in item.findall(".//main:t", XLSX_NS)))
        return strings

    def _load_sheet_paths(self) -> dict[str, str]:
        workbook = ElementTree.fromstring(self._zip.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(self._zip.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall("pkgrel:Relationship", XLSX_NS)
        }
        paths: dict[str, str] = {}
        for sheet in workbook.findall(".//main:sheets/main:sheet", XLSX_NS):
            rel_id = sheet.attrib[f"{{{XLSX_NS['rel']}}}id"]
            target = relationship_targets[rel_id]
            normalized_target = target.lstrip("/")
            paths[sheet.attrib["name"]] = normalized_target if normalized_target.startswith("xl/") else f"xl/{normalized_target}"
        return paths

    def _cell_value(self, cell) -> Any:
        value_node = cell.find("main:v", XLSX_NS)
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            text_node = cell.find(".//main:t", XLSX_NS)
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


def _preview_row(
    spec: ImportSpec,
    row: dict[str, Any],
    mapped_fields: list[dict[str, Any]],
    references: dict[str, Any],
    seen_identities: dict[str, int],
) -> dict[str, Any]:
    row_number = int(row["row_number"])
    source_values = row["values"]
    if not any(str(value or "").strip() for value in source_values.values()):
        return _row_result(row_number, "skipped", "", {}, "Skipped a blank row.", [])

    raw_values = _mapped_values(source_values, mapped_fields)
    payload, problems = _normalize_payload(spec.resource, raw_values, references)
    identity = _identity(spec.resource, payload)
    if not identity:
        problems.append(_problem("identity", "missing_identity", "This row does not have enough detail to identify the item.", "Fill in the required item details."))
    if problems:
        return _row_result(row_number, "blocked", identity, payload, "Fix this row before applying the import.", problems)

    if identity in seen_identities:
        return _row_result(
            row_number,
            "duplicate",
            identity,
            payload,
            f"This row looks like row {seen_identities[identity]} in the same import.",
            [
                _problem(
                    "identity",
                    "duplicate_in_file",
                    f"Another import row already uses {identity}.",
                    "Keep one copy of this item before applying the import.",
                    severity="warning",
                )
            ],
        )
    seen_identities[identity] = row_number

    existing = _find_existing(spec.resource, identity, references)
    if existing is None:
        return _row_result(row_number, "create", identity, payload, "This row will be created when the import is applied.", [])
    if _payload_matches(spec.resource, payload, existing):
        return _row_result(row_number, "skipped", identity, payload, "This row already matches the current library.", [])
    return _row_result(row_number, "update", identity, payload, "This row will update an existing library item when applied.", [])


def _normalize_payload(resource: ImportResource, raw: dict[str, Any], references: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    problems: list[dict[str, Any]] = []
    if resource == "boards":
        return _normalize_board(raw, problems), problems
    if resource == "slides":
        return _normalize_slide(raw, problems), problems
    if resource == "hinges":
        return _normalize_hinge(raw, problems), problems
    if resource == "handles":
        return _normalize_handle(raw, problems), problems
    if resource == "suppliers":
        return _normalize_supplier(raw, problems), problems
    if resource == "extra_categories":
        return _normalize_extra_category(raw, problems), problems
    if resource == "extras":
        return _normalize_extra(raw, references, problems), problems
    if resource == "supplier_item_costs":
        return _normalize_supplier_item_cost(raw, references, problems), problems
    if resource == "price_list_items":
        return _normalize_price_list_item(raw, references, problems), problems
    raise ValueError("Unsupported import type.")


def _normalize_board(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "brand": _required_text(raw, "brand", "Brand", problems),
        "material": _required_text(raw, "material", "Material", problems),
        "thickness": _positive_int(raw.get("thickness"), "thickness", "Thickness", problems),
        "length_mm": _positive_int(raw.get("length_mm"), "length_mm", "Length", problems),
        "width_mm": _positive_int(raw.get("width_mm"), "width_mm", "Width", problems),
        "costing_mode": _text(raw.get("costing_mode")) or "sheet",
        "grain_policy": _normalize_grain_policy(raw.get("grain_policy")),
    }
    if payload["costing_mode"] not in ALLOWED_COSTING_MODES:
        problems.append(_problem("costing_mode", "invalid_costing_mode", "Costing mode must be sheet or sqm.", "Use sheet for full board prices or sqm for square-metre prices."))
    if payload["grain_policy"] not in ALLOWED_GRAIN_POLICIES:
        problems.append(_problem("grain_policy", "invalid_grain_policy", "Grain policy must be none, optional, or required.", "Use none for MDF/utility boards, optional when grain notes are useful, or required for grained materials."))
    return payload


def _normalize_slide(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    length = _non_negative_int(raw.get("length"), "length", "Length", problems)
    return {
        "brand": _required_text(raw, "brand", "Brand", problems),
        "model": _required_text(raw, "model", "Model", problems),
        "code": _text(raw.get("code")),
        "length": length,
        "side_length": _non_negative_int(raw.get("side_length"), "side_length", "Side length", problems, default=length),
        "side_clearance_total": _non_negative_int(raw.get("side_clearance_total"), "side_clearance_total", "Side clearance", problems),
        "side_height_uplift": _non_negative_int(raw.get("side_height_uplift"), "side_height_uplift", "Side uplift", problems),
    }


def _normalize_hinge(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "brand": _required_text(raw, "brand", "Brand", problems),
        "model": _required_text(raw, "model", "Model", problems),
        "code": _text(raw.get("code")),
        "opening_angle_deg": _non_negative_int(raw.get("opening_angle_deg"), "opening_angle_deg", "Opening angle", problems),
    }


def _normalize_handle(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": _required_text(raw, "name", "Name", problems),
        "supplier": _text(raw.get("supplier")),
        "code": _text(raw.get("code")),
    }


def _normalize_supplier(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": _required_text(raw, "name", "Name", problems),
        "code": _text(raw.get("code")),
        "contact_name": _text(raw.get("contact_name")),
        "email": _text(raw.get("email")),
        "phone": _text(raw.get("phone")),
        "notes": _text(raw.get("notes")),
        "default_discount_bps": _bps(raw.get("default_discount_bps"), "default_discount_bps", "Default discount", problems),
    }


def _normalize_extra_category(raw: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": _required_text(raw, "name", "Name", problems)}


def _normalize_extra(raw: dict[str, Any], references: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    category_id = _text(raw.get("category_id"))
    category_name = _text(raw.get("category_name"))
    if not category_id and category_name:
        category = references["extra_categories_by_name"].get(_key(category_name))
        if category:
            category_id = category["id"]
    if not category_id:
        problems.append(_problem("category_name", "missing_category", "Choose an existing extra category for this row.", "Add the category first or map the category column."))
    elif category_id not in references["extra_categories_by_id"]:
        problems.append(_problem("category_id", "unknown_category", "That extra category is not in this company library.", "Use an existing category from Libraries."))
    return {
        "name": _required_text(raw, "name", "Name", problems),
        "category_id": category_id,
        "category_name": category_name,
        "supplier": _text(raw.get("supplier")),
        "code": _text(raw.get("code")),
        "notes": _text(raw.get("notes")),
    }


def _normalize_supplier_item_cost(raw: dict[str, Any], references: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    item_type = _item_type(raw.get("item_type"), problems)
    item_ref_id = _resolve_item_ref(item_type, raw, references, problems)
    supplier_id = _resolve_supplier(raw, references, problems)
    order_uom = _uom(raw.get("order_uom") or "pcs", "order_uom", "Order unit", problems)
    return {
        "item_type": item_type,
        "item_ref_id": item_ref_id,
        "supplier_id": supplier_id,
        "supplier_name": _text(raw.get("supplier_name")),
        "supplier_sku": _text(raw.get("supplier_sku")),
        "supplier_description": _text(raw.get("supplier_description")),
        "price_component": _text(raw.get("price_component")) or "unit",
        "order_uom": order_uom,
        "is_preferred": True,
        "list_price_cents": _money_cents(raw.get("list_price_cents"), "list_price_cents", "List price", problems, required=False),
        "discount_bps": _bps(raw.get("discount_bps"), "discount_bps", "Discount", problems),
        "unit_cost_cents": _money_cents(raw.get("unit_cost_cents"), "unit_cost_cents", "Net cost", problems),
        "currency_code": _currency(raw.get("currency_code"), problems),
    }


def _normalize_price_list_item(raw: dict[str, Any], references: dict[str, Any], problems: list[dict[str, Any]]) -> dict[str, Any]:
    if not references.get("price_list_id"):
        problems.append(_problem("price_list_id", "missing_price_list", "Choose an active price list before previewing price rows.", "Create or select an active price list in Pricing."))
    item_type = _item_type(raw.get("item_type"), problems)
    item_ref_id = _resolve_item_ref(item_type, raw, references, problems)
    item_key = _text(raw.get("item_key")) or (f"{item_type}::{item_ref_id}" if item_type and item_ref_id else "")
    return {
        "price_list_id": references.get("price_list_id") or "",
        "item_type": item_type,
        "item_ref_id": item_ref_id,
        "item_key": item_key,
        "price_component": _required_text(raw, "price_component", "Price component", problems),
        "uom": _uom(raw.get("uom"), "uom", "Unit", problems),
        "unit_price_cents": _money_cents(raw.get("unit_price_cents"), "unit_price_cents", "Price", problems),
        "cost_source": _text(raw.get("cost_source")) or "import",
    }


def build_reference_maps(snapshot: dict[str, Any]) -> dict[str, Any]:
    boards = list(snapshot.get("boards") or [])
    slides = list(snapshot.get("slides") or [])
    hinges = list(snapshot.get("hinges") or [])
    handles = list(snapshot.get("handles") or [])
    suppliers = list(snapshot.get("suppliers") or [])
    extra_categories = list(snapshot.get("extra_categories") or [])
    extras = list(snapshot.get("extras") or [])
    item_suppliers = list(snapshot.get("item_suppliers") or [])
    price_items = list(snapshot.get("price_items") or [])
    return {
        "boards_by_identity": {_identity("boards", row): row for row in boards},
        "slides_by_identity": {_identity("slides", row): row for row in slides},
        "hinges_by_identity": {_identity("hinges", row): row for row in hinges},
        "handles_by_identity": {_identity("handles", row): row for row in handles},
        "suppliers_by_identity": {_identity("suppliers", row): row for row in suppliers},
        "suppliers_by_id": {row["id"]: row for row in suppliers},
        "suppliers_by_name": {_key(row.get("name")): row for row in suppliers},
        "extra_categories_by_identity": {_identity("extra_categories", row): row for row in extra_categories},
        "extra_categories_by_id": {row["id"]: row for row in extra_categories},
        "extra_categories_by_name": {_key(row.get("name")): row for row in extra_categories},
        "extras_by_identity": {_identity("extras", row): row for row in extras},
        "items_by_type_id": _items_by_type_id(boards, slides, hinges, handles, extras),
        "item_refs_by_natural_key": _item_refs_by_natural_key(boards, slides, hinges, handles, extras),
        "item_suppliers_by_identity": {_identity("supplier_item_costs", row): row for row in item_suppliers},
        "price_items_by_identity": {_identity("price_list_items", row): row for row in price_items},
        "price_list_id": snapshot.get("price_list_id") or "",
    }


def _items_by_type_id(boards, slides, hinges, handles, extras) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        "board": {row["id"]: row for row in boards},
        "slide": {row["id"]: row for row in slides},
        "hinge": {row["id"]: row for row in hinges},
        "handle": {row["id"]: row for row in handles},
        "extra": {row["id"]: row for row in extras},
    }


def _item_refs_by_natural_key(boards, slides, hinges, handles, extras) -> dict[str, dict[str, str]]:
    return {
        "board": {_identity("boards", row): row["id"] for row in boards},
        "slide": {_identity("slides", row): row["id"] for row in slides},
        "hinge": {_identity("hinges", row): row["id"] for row in hinges},
        "handle": {_identity("handles", row): row["id"] for row in handles},
        "extra": {_identity("extras", row): row["id"] for row in extras},
    }


def _resolve_item_ref(item_type: str, raw: dict[str, Any], references: dict[str, Any], problems: list[dict[str, Any]]) -> str:
    item_ref_id = _text(raw.get("item_ref_id"))
    item_key = _text(raw.get("item_key"))
    if item_ref_id and item_ref_id in references["items_by_type_id"].get(item_type, {}):
        return item_ref_id
    if item_key.startswith(f"{item_type}::"):
        possible_ref = item_key.removeprefix(f"{item_type}::")
        if possible_ref in references["items_by_type_id"].get(item_type, {}):
            return possible_ref
    natural_key = _natural_item_key(item_type, raw, references)
    if natural_key:
        resolved = references["item_refs_by_natural_key"].get(item_type, {}).get(natural_key)
        if resolved:
            return resolved
    problems.append(_problem("item_ref_id", "missing_catalog_item", "This row does not match an item in the company library.", "Import or add the catalog item before previewing supplier costs or price rows."))
    return item_ref_id


def _resolve_supplier(raw: dict[str, Any], references: dict[str, Any], problems: list[dict[str, Any]]) -> str:
    supplier_id = _text(raw.get("supplier_id"))
    supplier_name = _text(raw.get("supplier_name"))
    if supplier_id and supplier_id in references["suppliers_by_id"]:
        return supplier_id
    if supplier_name:
        supplier = references["suppliers_by_name"].get(_key(supplier_name))
        if supplier:
            return supplier["id"]
    problems.append(_problem("supplier_name", "missing_supplier", "This supplier is not in the company library.", "Add the supplier first or map the supplier column."))
    return supplier_id


def _natural_item_key(item_type: str, raw: dict[str, Any], references: dict[str, Any]) -> str:
    if item_type == "board":
        return _identity(
            "boards",
            {
                "brand": raw.get("brand"),
                "material": raw.get("model"),
                "thickness": raw.get("thickness"),
                "length_mm": raw.get("length_mm"),
                "width_mm": raw.get("width_mm"),
            },
        )
    if item_type == "slide":
        return _identity("slides", {"brand": raw.get("brand"), "model": raw.get("model"), "code": raw.get("code")})
    if item_type == "hinge":
        return _identity("hinges", {"brand": raw.get("brand"), "model": raw.get("model"), "code": raw.get("code")})
    if item_type == "handle":
        return _identity("handles", {"name": raw.get("model"), "supplier": raw.get("supplier_name"), "code": raw.get("code")})
    if item_type == "extra":
        category_id = ""
        category_name = _text(raw.get("category_name"))
        if category_name:
            category = references["extra_categories_by_name"].get(_key(category_name))
            category_id = category["id"] if category else ""
        return _identity("extras", {"name": raw.get("model"), "category_id": category_id, "supplier": raw.get("supplier_name"), "code": raw.get("code")})
    return ""


def _find_existing(resource: ImportResource, identity: str, references: dict[str, Any]) -> dict[str, Any] | None:
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


def _payload_matches(resource: ImportResource, payload: dict[str, Any], existing: dict[str, Any]) -> bool:
    compare_fields = {
        "boards": ("brand", "material", "thickness", "length_mm", "width_mm", "costing_mode", "grain_policy"),
        "slides": ("brand", "model", "code", "length", "side_length", "side_clearance_total", "side_height_uplift"),
        "hinges": ("brand", "model", "code", "opening_angle_deg"),
        "handles": ("name", "supplier", "code"),
        "suppliers": ("name", "code", "contact_name", "email", "phone", "notes", "default_discount_bps"),
        "extra_categories": ("name",),
        "extras": ("name", "category_id", "supplier", "code", "notes"),
        "supplier_item_costs": ("item_type", "item_ref_id", "supplier_id", "supplier_sku", "price_component", "order_uom", "active_discount_bps", "active_unit_cost_cents", "active_currency_code"),
        "price_list_items": ("item_type", "item_ref_id", "price_component", "uom", "unit_price_cents", "cost_source"),
    }[resource]
    for field in compare_fields:
        payload_field = {
            "active_list_price_cents": "list_price_cents",
            "active_discount_bps": "discount_bps",
            "active_unit_cost_cents": "unit_cost_cents",
            "active_currency_code": "currency_code",
        }.get(field, field)
        if _compare_value(payload.get(payload_field)) != _compare_value(existing.get(field)):
            return False
    return True


def _identity(resource: ImportResource, payload: dict[str, Any]) -> str:
    if resource == "boards":
        return f"board:{_key(payload.get('brand'))}:{_key(payload.get('material'))}:{payload.get('thickness')}:{payload.get('length_mm')}:{payload.get('width_mm')}"
    if resource == "slides":
        return f"slide:{_key(payload.get('brand'))}:{_key(payload.get('model'))}:{_key(payload.get('code'))}"
    if resource == "hinges":
        return f"hinge:{_key(payload.get('brand'))}:{_key(payload.get('model'))}:{_key(payload.get('code'))}"
    if resource == "handles":
        return f"handle:{_key(payload.get('name'))}:{_key(payload.get('supplier'))}:{_key(payload.get('code'))}"
    if resource == "suppliers":
        return f"supplier:{_key(payload.get('name'))}"
    if resource == "extra_categories":
        return f"extra-category:{_key(payload.get('name'))}"
    if resource == "extras":
        return f"extra:{_key(payload.get('name'))}:{payload.get('category_id') or ''}:{_key(payload.get('supplier'))}:{_key(payload.get('code'))}"
    if resource == "supplier_item_costs":
        return f"supplier-cost:{payload.get('item_type')}:{payload.get('item_ref_id')}:{payload.get('supplier_id')}:{_key(payload.get('supplier_sku'))}:{_key(payload.get('price_component') or 'unit')}"
    if resource == "price_list_items":
        return f"price:{payload.get('price_list_id')}:{payload.get('item_type')}:{payload.get('item_key')}:{_key(payload.get('price_component'))}"
    return ""


def _mapped_fields(spec: ImportSpec, columns: list[str], column_mapping: dict[str, str]) -> list[dict[str, Any]]:
    by_normalized = {_normalize_column(column): column for column in columns}
    result: list[dict[str, Any]] = []
    for field in spec.fields:
        source_column = ""
        mapped_name = column_mapping.get(field.key, "")
        if mapped_name:
            source_column = by_normalized.get(_normalize_column(mapped_name), mapped_name)
        if not source_column:
            source_column = next((by_normalized[alias] for alias in [_normalize_column(alias) for alias in field.aliases] if alias in by_normalized), "")
        result.append(
            {
                "field": field.key,
                "label": field.label,
                "source_column": source_column,
                "required": field.required,
            }
        )
    return result


def _mapped_values(source_values: dict[str, Any], mapped_fields: list[dict[str, Any]]) -> dict[str, Any]:
    by_normalized = {_normalize_column(column): value for column, value in source_values.items()}
    values: dict[str, Any] = {}
    for field in mapped_fields:
        source_column = field["source_column"]
        if source_column:
            values[field["field"]] = by_normalized.get(_normalize_column(source_column))
    return values


def _row_result(
    row_number: int,
    status: ImportRowStatus,
    identity: str,
    payload: dict[str, Any],
    message: str,
    problems: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "row_number": row_number,
        "status": status,
        "identity": identity,
        "message": message,
        "payload": payload,
        "problems": problems,
    }


def _problem(
    field: str,
    code: str,
    message: str,
    suggestion: str,
    *,
    severity: ImportProblemSeverity = "error",
) -> dict[str, Any]:
    return {
        "field": field,
        "code": code,
        "severity": severity,
        "message": message,
        "suggestion": suggestion,
    }


def _count_status(rows: list[dict[str, Any]], status: ImportRowStatus) -> int:
    return sum(1 for row in rows if row["status"] == status)


def _required_text(raw: dict[str, Any], field: str, label: str, problems: list[dict[str, Any]]) -> str:
    value = _text(raw.get(field))
    if not value:
        problems.append(_problem(field, "missing_required", f"{label} is required.", f"Map or fill in the {label.lower()} column."))
    return value


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value)).strip()
    return str(value).strip()


def _normalize_grain_policy(value: Any) -> str:
    text = _text(value).lower()
    if not text:
        return "required"
    if text in {"no", "false", "not grained", "non-grained", "nongrained", "no grain"}:
        return "none"
    if text in {"yes", "true", "grained", "grain required", "requires grain"}:
        return "required"
    return text


def _positive_int(value: Any, field: str, label: str, problems: list[dict[str, Any]], default: int | None = None) -> int:
    parsed = _int(value)
    if parsed is None:
        if default is not None:
            return default
        problems.append(_problem(field, "invalid_number", f"{label} must be a positive whole number.", f"Use a positive millimetre value for {label.lower()}."))
        return 0
    if parsed <= 0:
        problems.append(_problem(field, "invalid_number", f"{label} must be greater than zero.", f"Use a positive millimetre value for {label.lower()}."))
    return parsed


def _non_negative_int(value: Any, field: str, label: str, problems: list[dict[str, Any]], default: int = 0) -> int:
    parsed = _int(value)
    if parsed is None:
        if value in (None, ""):
            return default
        problems.append(_problem(field, "invalid_number", f"{label} must be a whole number.", f"Use zero or a positive value for {label.lower()}."))
        return default
    if parsed < 0:
        problems.append(_problem(field, "invalid_number", f"{label} cannot be negative.", f"Use zero or a positive value for {label.lower()}."))
    return parsed


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        decimal = Decimal(str(value).strip().replace(",", ""))
    except InvalidOperation:
        return None
    if decimal != decimal.to_integral_value():
        return None
    return int(decimal)


def _money_cents(value: Any, field: str, label: str, problems: list[dict[str, Any]], *, required: bool = True) -> int:
    if value in (None, "") and not required:
        return 0
    text = _text(value)
    if not text:
        problems.append(_problem(field, "missing_price", f"{label} is required.", f"Fill in the {label.lower()} column."))
        return 0
    cleaned = re.sub(r"[^0-9.,-]", "", text).replace(",", "")
    try:
        decimal = Decimal(cleaned)
    except InvalidOperation:
        problems.append(_problem(field, "invalid_price", f"{label} must be a valid money amount.", "Use numbers such as 125.50, without text in the price cell."))
        return 0
    if decimal < 0:
        problems.append(_problem(field, "invalid_price", f"{label} cannot be negative.", "Use a zero or positive price."))
    if decimal == decimal.to_integral_value() and "cents" in field and abs(decimal) >= 10000:
        return int(decimal)
    return int((decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _bps(value: Any, field: str, label: str, problems: list[dict[str, Any]]) -> int:
    if value in (None, ""):
        return 0
    text = _text(value)
    try:
        decimal = Decimal(text.replace("%", "").strip())
    except InvalidOperation:
        problems.append(_problem(field, "invalid_percent", f"{label} must be a percentage.", "Use a value such as 30 or 30%."))
        return 0
    if "%" in text:
        bps = int((decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    elif decimal <= 1:
        bps = int((decimal * 10000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    elif decimal > 100:
        bps = int(decimal)
    else:
        bps = int((decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if bps < 0 or bps > 10000:
        problems.append(_problem(field, "invalid_percent", f"{label} must be between 0% and 100%.", "Use a percentage between 0 and 100."))
    return max(0, min(10000, bps))


def _currency(value: Any, problems: list[dict[str, Any]]) -> str:
    currency = (_text(value) or "ZAR").upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        problems.append(_problem("currency_code", "invalid_currency", "Currency must be a three-letter code.", "Use a code such as ZAR or USD."))
    return currency


def _item_type(value: Any, problems: list[dict[str, Any]]) -> str:
    item_type = _text(value).lower()
    if item_type not in ALLOWED_ITEM_TYPES:
        problems.append(_problem("item_type", "invalid_item_type", "Item type must be board, slide, hinge, handle, or extra.", "Choose the library type this price or supplier cost belongs to."))
    return item_type


def _uom(value: Any, field: str, label: str, problems: list[dict[str, Any]]) -> str:
    uom = _text(value).lower()
    if not uom:
        problems.append(_problem(field, "missing_uom", f"{label} is required.", "Map or fill in the unit column."))
        return ""
    if uom not in ALLOWED_UOMS:
        problems.append(_problem(field, "invalid_uom", f"{label} uses an unsupported unit.", "Use a familiar unit such as sheet, m2, m, pcs, pairs, day, or trip."))
    return uom


def _compare_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _key(value: Any) -> str:
    return _text(value).casefold()


def _clean_column_mapping(mapping: dict[str, Any]) -> dict[str, str]:
    return {str(key).strip(): str(value).strip() for key, value in mapping.items() if str(key).strip() and str(value).strip()}


def _clean_header_name(value: Any) -> str:
    return re.sub(r"\s+", " ", _text(value)).strip()


def _normalize_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _sniff_delimiter(content: str) -> str:
    try:
        return csv.Sniffer().sniff(content[:2048], delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def _parse_number(value: str) -> Any:
    try:
        decimal = Decimal(value)
    except InvalidOperation:
        return value
    if decimal == decimal.to_integral_value():
        return int(decimal)
    return float(decimal)


def _column_index(reference: str) -> int:
    letters = "".join(ch for ch in reference if ch.isalpha()).upper()
    result = 0
    for letter in letters:
        result = result * 26 + (ord(letter) - ord("A") + 1)
    return result
