"""CSV and XLSX exports for workshop production handoff packets."""

from __future__ import annotations

import csv
import re
from io import BytesIO, StringIO
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ExportFormat = str
CellValue = str | int | float | bool | None
SheetRows = list[dict[str, CellValue]]

CSV_COLUMNS = [
    "Project",
    "Quote",
    "Quote Number",
    "Revision",
    "Source",
    "Unit",
    "Unit Type",
    "Section",
    "Part ID",
    "Part",
    "Material Role",
    "Board",
    "Brand",
    "Material",
    "Thickness (mm)",
    "Sheet Length (mm)",
    "Sheet Width (mm)",
    "Length (mm)",
    "Width (mm)",
    "Quantity",
    "Edge Sides",
    "Edge Banding",
    "Grain Direction",
    "Rotation",
    "Production Notes",
    "Warning State",
    "Warning Messages",
]

MATERIAL_SUMMARY_COLUMNS = [
    "Board",
    "Material Role",
    "Brand",
    "Material",
    "Thickness (mm)",
    "Sheet Length (mm)",
    "Sheet Width (mm)",
    "Pieces",
    "Area (m2)",
    "Edge (m)",
    "Estimated Sheets",
    "Part IDs",
]

BOARD_REQUIREMENT_COLUMNS = [
    "Board",
    "Material Role",
    "Sources",
    "Brand",
    "Material",
    "Thickness (mm)",
    "Sheet Length (mm)",
    "Sheet Width (mm)",
    "Rows",
    "Pieces",
    "Area (m2)",
    "Edge (m)",
    "Sheet Area (m2)",
    "Estimated Sheets",
    "Estimated Sheet Area (m2)",
    "Waste Area (m2)",
    "Waste Percent",
    "Sheet Estimate",
    "Waste Allowance",
    "Part IDs",
    "Warning State",
    "Warning Messages",
]

HARDWARE_PICK_LIST_COLUMNS = [
    "Part ID",
    "Type",
    "Item",
    "Supplier",
    "Code",
    "Quantity",
    "UOM",
    "Used In",
    "Unit Numbers",
    "Related Part IDs",
]

LABEL_COLUMNS = [
    "Part ID",
    "Label",
    "Source",
    "Unit",
    "Section",
    "Part",
    "Dimensions",
    "Material",
    "Quantity",
    "Warning State",
    "Edge Sides",
    "Grain",
    "Rotation",
]

WARNING_COLUMNS = [
    "Warning Source",
    "Severity",
    "Code",
    "Part ID",
    "Unit",
    "Section",
    "Item",
    "Message",
]


def render_production_handoff_csv(handoff: dict[str, Any]) -> bytes:
    """Render production cutting schedule rows as a CSV attachment."""

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_cutting_schedule_rows(handoff))
    return output.getvalue().encode("utf-8")


def render_production_handoff_xlsx(handoff: dict[str, Any]) -> bytes:
    """Render production handoff data as a multi-sheet XLSX workbook."""

    sheets = {
        "Cutting Schedule": (CSV_COLUMNS, _cutting_schedule_rows(handoff)),
        "Material Summary": (MATERIAL_SUMMARY_COLUMNS, _material_summary_rows(handoff)),
        "Board Requirements": (BOARD_REQUIREMENT_COLUMNS, _board_requirement_rows(handoff)),
        "Hardware Pick List": (HARDWARE_PICK_LIST_COLUMNS, _hardware_pick_list_rows(handoff)),
        "Labels": (LABEL_COLUMNS, _label_rows(handoff)),
        "Warnings": (WARNING_COLUMNS, _warning_rows(handoff)),
    }
    return _write_xlsx(sheets)


def production_handoff_export_filename(handoff: dict[str, Any], extension: str) -> str:
    """Return a business-friendly production export filename."""

    safe_extension = extension.lstrip(".").lower() or "csv"
    base = "-".join(
        part
        for part in (
            "production",
            _filename_part(str(handoff.get("project_name") or handoff.get("quote_name") or "handoff")),
            _filename_part(str(handoff.get("quote_number") or "quote")),
            f"rev-{_positive_int(handoff.get('revision'), fallback=1)}",
        )
        if part
    )
    return f"{base or 'production-handoff'}.{safe_extension}"


def _cutting_schedule_rows(handoff: dict[str, Any]) -> SheetRows:
    rows: SheetRows = []
    for row in _list(handoff.get("rows")):
        rows.append(
            {
                "Project": _text(row.get("project_name") or handoff.get("project_name")),
                "Quote": _text(row.get("quote_name") or handoff.get("quote_name")),
                "Quote Number": _text(row.get("quote_number") or handoff.get("quote_number")),
                "Revision": _positive_int(row.get("revision") or handoff.get("revision"), fallback=1),
                "Source": _source_label(row.get("source_type")),
                "Unit": _text(row.get("unit_label")),
                "Unit Type": _text(row.get("unit_type_key")),
                "Section": _text(row.get("section_label")),
                "Part ID": _text(row.get("part_id")),
                "Part": _text(row.get("desc")),
                "Material Role": _text(row.get("role_label")),
                "Board": _text(row.get("board_name")),
                "Brand": _text(row.get("brand")),
                "Material": _text(row.get("material")),
                "Thickness (mm)": _optional_number(row.get("thickness")),
                "Sheet Length (mm)": _optional_number(row.get("sheet_length_mm")),
                "Sheet Width (mm)": _optional_number(row.get("sheet_width_mm")),
                "Length (mm)": _positive_int(row.get("length")),
                "Width (mm)": _positive_int(row.get("width")),
                "Quantity": _positive_int(row.get("quantity")),
                "Edge Sides": _text(row.get("edge_sides_label")),
                "Edge Banding": _text(row.get("edge_banding")),
                "Grain Direction": _text(row.get("grain_label")),
                "Rotation": _text(row.get("rotation_label")),
                "Production Notes": _text(row.get("production_notes")),
                "Warning State": _warning_state(row.get("warning_count")),
                "Warning Messages": _joined(row.get("warning_messages")),
            }
        )
    return rows


def _material_summary_rows(handoff: dict[str, Any]) -> SheetRows:
    summary = handoff.get("material_summary") if isinstance(handoff.get("material_summary"), dict) else {}
    rows: SheetRows = []
    for group in _list(summary.get("groups")):
        rows.append(
            {
                "Board": _text(group.get("board_name")),
                "Material Role": _text(group.get("role_label")),
                "Brand": _text(group.get("brand")),
                "Material": _text(group.get("material")),
                "Thickness (mm)": _optional_number(group.get("thickness")),
                "Sheet Length (mm)": _optional_number(group.get("length_mm")),
                "Sheet Width (mm)": _optional_number(group.get("width_mm")),
                "Pieces": _positive_int(group.get("piece_count")),
                "Area (m2)": _optional_number(group.get("area_m2")),
                "Edge (m)": _optional_number(group.get("edge_m")),
                "Estimated Sheets": _optional_number(group.get("estimated_sheets")),
                "Part IDs": _joined(group.get("part_ids")),
            }
        )
    return rows


def _board_requirement_rows(handoff: dict[str, Any]) -> SheetRows:
    requirements = handoff.get("board_requirements") if isinstance(handoff.get("board_requirements"), dict) else {}
    rows: SheetRows = []
    for group in _list(requirements.get("groups")):
        rows.append(
            {
                "Board": _text(group.get("board_name")),
                "Material Role": _text(group.get("role_label")),
                "Sources": _joined(group.get("source_labels")),
                "Brand": _text(group.get("brand")),
                "Material": _text(group.get("material")),
                "Thickness (mm)": _optional_number(group.get("thickness")),
                "Sheet Length (mm)": _optional_number(group.get("sheet_length_mm")),
                "Sheet Width (mm)": _optional_number(group.get("sheet_width_mm")),
                "Rows": _positive_int(group.get("row_count")),
                "Pieces": _positive_int(group.get("piece_count")),
                "Area (m2)": _optional_number(group.get("area_m2")),
                "Edge (m)": _optional_number(group.get("edge_m")),
                "Sheet Area (m2)": _optional_number(group.get("sheet_area_m2")),
                "Estimated Sheets": _optional_number(group.get("estimated_sheets")),
                "Estimated Sheet Area (m2)": _optional_number(group.get("estimated_sheet_area_m2")),
                "Waste Area (m2)": _optional_number(group.get("waste_area_m2")),
                "Waste Percent": _optional_number(group.get("waste_percent")),
                "Sheet Estimate": _text(group.get("sheet_estimate_label")),
                "Waste Allowance": _text(group.get("waste_allowance_label")),
                "Part IDs": _joined(group.get("part_ids")),
                "Warning State": _warning_state(group.get("warning_count")),
                "Warning Messages": _joined(group.get("warning_messages")),
            }
        )
    return rows


def _hardware_pick_list_rows(handoff: dict[str, Any]) -> SheetRows:
    pick_list = handoff.get("hardware_pick_list") if isinstance(handoff.get("hardware_pick_list"), dict) else {}
    rows: SheetRows = []
    for item in _list(pick_list.get("items")):
        rows.append(
            {
                "Part ID": _text(item.get("part_id")),
                "Type": _text(item.get("type_label")),
                "Item": _text(item.get("item_name")),
                "Supplier": _text(item.get("supplier")),
                "Code": _text(item.get("code")),
                "Quantity": _optional_number(item.get("quantity")),
                "UOM": _text(item.get("uom")),
                "Used In": _text(item.get("usage_label")) or _joined(item.get("used_in")),
                "Unit Numbers": _joined(item.get("unit_numbers")),
                "Related Part IDs": _joined(item.get("related_part_ids")),
            }
        )
    return rows


def _label_rows(handoff: dict[str, Any]) -> SheetRows:
    rows: SheetRows = []
    for label in _list(handoff.get("labels")):
        rows.append(
            {
                "Part ID": _text(label.get("part_id")),
                "Label": _text(label.get("label")),
                "Source": _source_label(label.get("source_type")),
                "Unit": _text(label.get("unit_label")),
                "Section": _text(label.get("section")),
                "Part": _text(label.get("desc")),
                "Dimensions": _text(label.get("dimensions_label")),
                "Material": _text(label.get("material_label")),
                "Quantity": _positive_int(label.get("quantity")),
                "Warning State": _warning_state(label.get("warning_count")),
                "Edge Sides": _text(label.get("edge_sides_label")),
                "Grain": _text(label.get("grain_label")),
                "Rotation": _text(label.get("rotation_label")),
            }
        )
    return rows


def _warning_rows(handoff: dict[str, Any]) -> SheetRows:
    rows: SheetRows = []
    for row in _list(handoff.get("rows")):
        for message in _list(row.get("warning_messages")):
            rows.append(
                {
                    "Warning Source": "Cutting schedule",
                    "Severity": "warning",
                    "Code": "",
                    "Part ID": _text(row.get("part_id")),
                    "Unit": _text(row.get("unit_label")),
                    "Section": _text(row.get("section_label")),
                    "Item": _text(row.get("desc")),
                    "Message": _text(message),
                }
            )

    board_requirements = handoff.get("board_requirements") if isinstance(handoff.get("board_requirements"), dict) else {}
    for warning in _list(board_requirements.get("warnings")):
        rows.append(
            {
                "Warning Source": "Board requirements",
                "Severity": _text(warning.get("severity") or "warning"),
                "Code": _text(warning.get("code")),
                "Part ID": _text(warning.get("part_id")),
                "Unit": _unit_label(warning.get("unit_number")),
                "Section": _text(warning.get("role_label")),
                "Item": _text(warning.get("row_desc")),
                "Message": _text(warning.get("message")),
            }
        )

    material_summary = handoff.get("material_summary") if isinstance(handoff.get("material_summary"), dict) else {}
    for warning in _list(material_summary.get("warnings")):
        rows.append(_generic_warning_row("Material summary", warning))

    hardware_pick_list = handoff.get("hardware_pick_list") if isinstance(handoff.get("hardware_pick_list"), dict) else {}
    for warning in _list(hardware_pick_list.get("warnings")):
        rows.append(_generic_warning_row("Hardware pick list", warning))

    return rows


def _generic_warning_row(source: str, warning: dict[str, Any]) -> dict[str, CellValue]:
    return {
        "Warning Source": source,
        "Severity": _text(warning.get("severity") or "warning"),
        "Code": _text(warning.get("code")),
        "Part ID": _text(warning.get("part_id")),
        "Unit": _unit_label(warning.get("unit_number")),
        "Section": _text(warning.get("section") or warning.get("item_type") or warning.get("material_role")),
        "Item": _text(warning.get("row_desc") or warning.get("item_name") or warning.get("item_ref_id")),
        "Message": _text(warning.get("message") or warning.get("reason")),
    }


def _write_xlsx(sheets: dict[str, tuple[list[str], SheetRows]]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        sheet_items = list(sheets.items())
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheet_items)))
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml([name for name, _ in sheet_items]))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml(len(sheet_items)))
        for index, (_, (columns, rows)) in enumerate(sheet_items, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(columns, rows))
    return buffer.getvalue()


def _content_types_xml(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{sheet_overrides}"
        "</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{_xml_attr(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet_name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets>"
        "</workbook>"
    )


def _workbook_relationships_xml(sheet_count: int) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}"
        "</Relationships>"
    )


def _worksheet_xml(columns: list[str], rows: SheetRows) -> str:
    all_rows = [dict(zip(columns, columns, strict=True)), *rows]
    sheet_rows = "".join(
        _xlsx_row(row_number, [row.get(column) for column in columns])
        for row_number, row in enumerate(all_rows, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_rows}</sheetData>"
        "</worksheet>"
    )


def _xlsx_row(row_number: int, values: list[CellValue]) -> str:
    cells = "".join(_xlsx_cell(row_number, index, value) for index, value in enumerate(values, start=1))
    return f'<row r="{row_number}">{cells}</row>'


def _xlsx_cell(row_number: int, column_index: int, value: CellValue) -> str:
    reference = f"{_column_letters(column_index)}{row_number}"
    if isinstance(value, bool):
        return f'<c r="{reference}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{reference}"><v>{value}</v></c>'
    return f'<c r="{reference}" t="inlineStr"><is><t>{_xml_text(_text(value))}</t></is></c>'


def _column_letters(column_index: int) -> str:
    letters = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        letters = f"{chr(ord('A') + remainder)}{letters}"
    return letters


def _source_label(value: Any) -> str:
    if str(value or "") == "quote_panel":
        return "Quote panel"
    if str(value or "") == "unit":
        return "Unit"
    return _text(value)


def _warning_state(value: Any) -> str:
    return "Review" if _positive_int(value) > 0 else "Ready"


def _unit_label(value: Any) -> str:
    unit_number = _positive_int(value)
    if unit_number <= 0:
        return "Quote-level" if value not in (None, "") else ""
    return f"Unit {unit_number}"


def _joined(value: Any) -> str:
    if not isinstance(value, list):
        return _text(value)
    return "; ".join(_text(item) for item in value if _text(item))


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _positive_int(value: Any, *, fallback: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(0, parsed)


def _optional_number(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def _filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-")
    return cleaned[:60]


def _xml_text(value: str) -> str:
    return escape(_strip_xml_control_chars(value))


def _xml_attr(value: str) -> str:
    return escape(_strip_xml_control_chars(value), {'"': "&quot;"})


def _strip_xml_control_chars(value: str) -> str:
    return "".join(char for char in value if char in "\t\n\r" or ord(char) >= 32)
