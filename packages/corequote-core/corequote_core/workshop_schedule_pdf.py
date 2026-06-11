"""Workshop-facing cutting schedule PDF output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from fpdf import FPDF


SECTION_TITLES = {
    "carcass": "Carcass rows",
    "panel": "Panel rows",
    "extra_panel": "Custom panel rows",
    "hardware": "Hardware rows",
    "other": "Other rows",
}
SECTION_ORDER = ("carcass", "panel", "extra_panel", "hardware", "other")
TABLE_COLUMNS = (
    ("Unit", 18, "L"),
    ("Description", 68, "L"),
    ("L mm", 23, "R"),
    ("W mm", 23, "R"),
    ("Qty", 18, "R"),
    ("Board/material", 84, "L"),
    ("Status", 23, "L"),
)
TABLE_WIDTH = sum(width for _, width, _ in TABLE_COLUMNS)
TABLE_ROW_HEIGHT = 5.6
TABLE_HEADER_HEIGHT = 6
UNIT_SEPARATOR_HEIGHT = 1.1


@dataclass(frozen=True)
class WorkshopScheduleWarning:
    source: str
    unit_number: int
    section: str
    row_desc: str
    reason: str


@dataclass(frozen=True)
class WorkshopScheduleRow:
    section: str
    unit_number: int
    unit_label: str
    desc: str
    length: int
    width: int
    qty: int
    board_material: str
    status: str
    warning_reasons: list[str]


@dataclass(frozen=True)
class WorkshopScheduleGroup:
    section: str
    title: str
    rows: list[WorkshopScheduleRow]


@dataclass(frozen=True)
class WorkshopScheduleDocument:
    company_name: str
    project_name: str
    client_name: str
    site_address: str
    quote_name: str
    quote_number: str
    revision: int
    export_date: date
    groups: list[WorkshopScheduleGroup]
    warnings: list[WorkshopScheduleWarning]


class WorkshopSchedulePDF(FPDF):
    def __init__(self, document: WorkshopScheduleDocument):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.document = document

    def header(self) -> None:
        document = self.document
        self.set_y(8)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(20, 24, 31)
        self.cell(130, 6, _pdf_text(document.company_name))
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, _pdf_text("Workshop Cutting Schedule"), align="R", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(90, 96, 110)
        self.cell(130, 5, _pdf_text(f"{document.project_name} / {document.client_name}"))
        self.cell(
            0,
            5,
            _pdf_text(f"{document.quote_number} rev {document.revision} / exported {document.export_date.isoformat()}"),
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_draw_color(205, 211, 220)
        self.line(10, 24, 287, 24)
        self.set_y(28)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, _pdf_text(f"Page {self.page_no()}"), align="C")


def build_workshop_schedule_document(
    *,
    company: dict[str, Any],
    quote: dict[str, Any],
    project: dict[str, Any],
    units: list[dict[str, Any]],
    cutting_list: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
    export_date: date | None = None,
) -> WorkshopScheduleDocument:
    """Build the workshop cutting schedule model from live cutlist rows."""

    warnings = [_schedule_warning(row) for row in _list(cutting_list.get("validation_warnings"))]
    warnings_by_row = _warnings_by_row(warnings)
    units_by_number = {
        _int_value(unit.get("unit_number")): unit
        for unit in units
        if _int_value(unit.get("unit_number")) > 0
    }
    grouped: dict[str, list[WorkshopScheduleRow]] = {section: [] for section in SECTION_ORDER}

    for raw_row in _iter_schedule_rows(cutting_list):
        section = _section(raw_row.get("section"))
        unit_number = _int_value(raw_row.get("unit_number"))
        desc = _text(raw_row.get("desc"), fallback="Cutlist row")
        row_warnings = warnings_by_row.get((section, unit_number, desc), [])
        board_id = _resolve_board_id(raw_row, section=section, quote=quote, units_by_number=units_by_number)
        grouped[section].append(
            WorkshopScheduleRow(
                section=section,
                unit_number=unit_number,
                unit_label="Quote" if unit_number == 0 else str(unit_number),
                desc=desc,
                length=_int_value(raw_row.get("length")),
                width=_int_value(raw_row.get("width")),
                qty=_int_value(raw_row.get("qty")),
                board_material=_board_label(board_id, board_lookup=board_lookup),
                status="Check" if row_warnings else "OK",
                warning_reasons=[warning.reason for warning in row_warnings],
            )
        )

    return WorkshopScheduleDocument(
        company_name=_text(company.get("name"), fallback="Company"),
        project_name=_text(project.get("name"), fallback="Project"),
        client_name=_text(project.get("client"), fallback="Client"),
        site_address=_text(project.get("address"), fallback=""),
        quote_name=_text(quote.get("name"), fallback="Quote"),
        quote_number=_text(quote.get("quote_number"), fallback="Quote"),
        revision=max(1, _int_value(quote.get("revision"))),
        export_date=export_date or date.today(),
        groups=[
            WorkshopScheduleGroup(section=section, title=SECTION_TITLES[section], rows=rows)
            for section in SECTION_ORDER
            if (rows := grouped[section])
        ],
        warnings=warnings,
    )


def workshop_schedule_filename(document: WorkshopScheduleDocument) -> str:
    base = "-".join(
        part
        for part in (
            "workshop",
            _filename_part(document.quote_name),
            _filename_part(document.quote_number),
            f"rev-{document.revision}",
        )
        if part
    )
    return f"{base or 'workshop-schedule'}.pdf"


def render_workshop_schedule_pdf(document: WorkshopScheduleDocument) -> bytes:
    pdf = WorkshopSchedulePDF(document)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    _draw_context(pdf, document)
    _draw_warnings(pdf, document)
    for group in document.groups:
        _draw_group(pdf, group)
    return bytes(pdf.output())


def _draw_context(pdf: FPDF, document: WorkshopScheduleDocument) -> None:
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 96, 110)
    pdf.cell(22, 6, _pdf_text("Project"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(80, 6, _pdf_text(_clip(document.project_name, 38)))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 96, 110)
    pdf.cell(18, 6, _pdf_text("Client"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(70, 6, _pdf_text(_clip(document.client_name, 34)))
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 96, 110)
    pdf.cell(18, 6, _pdf_text("Site"))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(0, 6, _pdf_text(_clip(document.site_address or "-", 35)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _draw_warnings(pdf: FPDF, document: WorkshopScheduleDocument) -> None:
    if not document.warnings:
        return
    _ensure_space(pdf, 18)
    pdf.set_fill_color(255, 248, 230)
    pdf.set_draw_color(225, 185, 80)
    pdf.set_text_color(95, 65, 20)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, _pdf_text("Validation warnings included"), border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    for warning in document.warnings:
        _ensure_space(pdf, 6)
        source = "Quote panel" if warning.source == "quote_panel" else f"Unit {warning.unit_number}"
        text = f"{source} / {warning.row_desc}: {warning.reason}"
        pdf.cell(0, 5, _pdf_text(_clip(text, 150)), border="LR", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 1, "", border="T", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _draw_group(pdf: FPDF, group: WorkshopScheduleGroup) -> None:
    _ensure_space(pdf, 20)
    _draw_table_header(pdf, group.title)
    previous_unit_number: int | None = None
    for row in group.rows:
        needs_unit_separator = (
            group.section in {"carcass", "panel"}
            and previous_unit_number is not None
            and row.unit_number != previous_unit_number
        )
        required_height = TABLE_ROW_HEIGHT + (UNIT_SEPARATOR_HEIGHT if needs_unit_separator else 0)
        if _ensure_space(pdf, required_height):
            _draw_table_header(pdf, f"{group.title} continued")
            needs_unit_separator = False
        if needs_unit_separator:
            _draw_unit_separator(pdf)
        _draw_row(pdf, row)
        previous_unit_number = row.unit_number
    pdf.ln(4)


def _draw_table_header(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(0, 6, _pdf_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(205, 211, 220)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(45, 55, 72)
    for label, width, align in TABLE_COLUMNS:
        pdf.cell(width, TABLE_HEADER_HEIGHT, _pdf_text(label), border=1, align=align, fill=True)
    pdf.ln(TABLE_HEADER_HEIGHT)


def _draw_unit_separator(pdf: FPDF) -> None:
    pdf.set_fill_color(210, 216, 226)
    pdf.rect(10, pdf.get_y(), TABLE_WIDTH, UNIT_SEPARATOR_HEIGHT, style="F")
    pdf.ln(UNIT_SEPARATOR_HEIGHT)


def _draw_row(pdf: FPDF, row: WorkshopScheduleRow) -> None:
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(20, 24, 31)
    values = (
        row.unit_label,
        _clip(row.desc, 34),
        str(row.length),
        str(row.width),
        str(row.qty),
        _clip(row.board_material, 44),
        row.status,
    )
    for (label, width, align), value in zip(TABLE_COLUMNS, values, strict=True):
        fill = label == "Status" and row.status == "Check"
        if fill:
            pdf.set_fill_color(255, 248, 230)
            pdf.set_text_color(95, 65, 20)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(20, 24, 31)
        pdf.cell(width, TABLE_ROW_HEIGHT, _pdf_text(value), border=1, align=align, fill=fill)
    pdf.ln(TABLE_ROW_HEIGHT)


def _ensure_space(pdf: FPDF, height: int) -> bool:
    if pdf.get_y() + height <= pdf.h - pdf.b_margin:
        return False
    pdf.add_page()
    return True


def _iter_schedule_rows(cutting_list: dict[str, Any]) -> list[dict[str, Any]]:
    runtime_rows = _list(cutting_list.get("runtime_rows"))
    if runtime_rows:
        return [dict(row) for row in runtime_rows]

    rows: list[dict[str, Any]] = []
    for key, section in (
        ("carcass", "carcass"),
        ("panels", "panel"),
        ("hardware", "hardware"),
        ("extras", "extra_panel"),
    ):
        rows.extend({**dict(row), "section": section} for row in _list(cutting_list.get(key)))
    return rows


def _schedule_warning(row: dict[str, Any]) -> WorkshopScheduleWarning:
    return WorkshopScheduleWarning(
        source=str(row.get("source") or "unit"),
        unit_number=_int_value(row.get("unit_number")),
        section=_section(row.get("section")),
        row_desc=_text(row.get("row_desc"), fallback="Cutlist row"),
        reason=_text(row.get("reason"), fallback="Review this row before cutting."),
    )


def _warnings_by_row(
    warnings: list[WorkshopScheduleWarning],
) -> dict[tuple[str, int, str], list[WorkshopScheduleWarning]]:
    grouped: dict[tuple[str, int, str], list[WorkshopScheduleWarning]] = {}
    for warning in warnings:
        key = (warning.section, warning.unit_number, warning.row_desc)
        grouped.setdefault(key, []).append(warning)
    return grouped


def _resolve_board_id(
    row: dict[str, Any],
    *,
    section: str,
    quote: dict[str, Any],
    units_by_number: dict[int, dict[str, Any]],
) -> str:
    unit = units_by_number.get(_int_value(row.get("unit_number"))) or {}
    if section == "carcass":
        return _clean_id(row.get("board_type_id") or unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id"))
    if section == "panel":
        return _clean_id(row.get("board_type_id") or unit.get("door_board_type_id") or quote.get("default_door_board_type_id"))
    if section == "extra_panel":
        return _clean_id(
            row.get("board_type_id")
            or quote.get("default_panel_board_type_id")
            or unit.get("door_board_type_id")
            or quote.get("default_door_board_type_id")
        )
    return _clean_id(row.get("board_type_id"))


def _board_label(board_id: str, *, board_lookup: dict[str, dict[str, Any]]) -> str:
    if not board_id:
        return "-"
    board = board_lookup.get(board_id)
    if not board:
        return "Unknown board"
    parts = [
        str(board.get("brand") or "").strip(),
        str(board.get("material") or "").strip(),
    ]
    label = " ".join(part for part in parts if part).strip()
    thickness = _int_value(board.get("thickness"))
    if thickness > 0:
        label = f"{label} {thickness}mm".strip()
    return label or board_id


def _section(value: Any) -> str:
    cleaned = str(value or "").strip()
    if cleaned in SECTION_TITLES:
        return cleaned
    if cleaned == "panels":
        return "panel"
    if cleaned == "extras":
        return "extra_panel"
    return "other"


def _text(value: Any, *, fallback: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _clean_id(value: Any) -> str:
    return str(value or "").strip()


def _filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-")
    return cleaned[:60]


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: max(0, limit - 3)]}..."


def _pdf_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")
