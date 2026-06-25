from __future__ import annotations

import csv
from io import BytesIO, StringIO
from zipfile import ZipFile
from xml.etree import ElementTree

from corequote_core.production_export import (
    production_handoff_export_filename,
    render_production_handoff_csv,
    render_production_handoff_xlsx,
)
from corequote_core.production_handoff import build_production_handoff


XLSX_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def test_production_handoff_csv_exports_workshop_rows_custom_panels_and_warnings():
    handoff = _handoff_with_custom_panel_and_warning()
    handoff["client_quote_total_cents"] = 999999
    handoff["rows"][0]["cost_total_cents"] = 120000
    handoff["material_summary"]["groups"][0]["profit_cents"] = 50000

    rows = _csv_rows(render_production_handoff_csv(handoff))

    assert rows[0]["Project"] == "Smith Kitchen Phase 5 Workshop Handoff"
    assert rows[0]["Quote Number"] == "Q-007"
    assert rows[0]["Revision"] == "2"
    assert rows[0]["Part ID"] == "Q-007-R2-QP-EXT-KICKER-2400X100-01"
    assert rows[0]["Source"] == "Quote panel"
    assert rows[0]["Unit"] == "Quote-level"
    assert rows[0]["Warning State"] == "Review"
    assert rows[0]["Warning Messages"] == "Confirm kicker split before cutting."
    assert rows[1]["Part ID"] == "Q-007-R2-U01-CAR-SIDE-748X564-01"
    assert rows[1]["Board"] == "PG White (16mm)"
    assert rows[2]["Part ID"] == "Q-007-R2-U02-CAR-SHELF-568X300-01"
    assert rows[3]["Part ID"] == "Q-007-R2-U02-PAN-DOOR-720X297-01"

    flattened = "\n".join(",".join(row.values()) for row in rows)
    assert "cost_total_cents" not in flattened
    assert "profit_cents" not in flattened
    assert "client_quote_total_cents" not in flattened


def test_production_handoff_exports_include_wall_front_overhang_rows():
    handoff = build_production_handoff(
        quote=_quote(),
        project={"id": "project-1", "name": "Smith Kitchen Phase 5 Workshop Handoff"},
        units=[_unit(1, "Wall Door", carcass_board_type_id="board-white", door_board_type_id="board-oak")],
        cutting_list={
            "panels": [
                {"unit_number": 1, "desc": "Door", "length": 717, "width": 297, "qty": 1},
                {"unit_number": 1, "desc": "Door (bottom overhang 20 mm)", "length": 737, "width": 297, "qty": 1},
            ],
            "validation_warnings": [],
        },
        material_summary={"groups": [], "warnings": [], "total_area_m2": 0, "total_piece_count": 0, "total_edge_m": 0},
        hardware_pick_list={"items": [], "warnings": [], "total_item_count": 0, "total_quantity": 0},
        board_lookup=_board_lookup(),
    )

    csv_row = next(row for row in _csv_rows(render_production_handoff_csv(handoff)) if row["Part"] == "Door (bottom overhang 20 mm)")
    workbook = _xlsx_sheets(render_production_handoff_xlsx(handoff))
    xlsx_row = next(row for row in workbook["Cutting Schedule"] if row[9] == "Door (bottom overhang 20 mm)")
    label_row = next(row for row in workbook["Labels"] if row[5] == "Door (bottom overhang 20 mm)")

    assert csv_row["Length (mm)"] == "737"
    assert csv_row["Width (mm)"] == "297"
    assert xlsx_row[17:20] == [737, 297, 1]
    assert label_row[6] == "737 x 297 mm"


def test_production_handoff_xlsx_exports_related_handoff_sheets_without_pricing_fields():
    handoff = _handoff_with_custom_panel_and_warning()
    handoff["board_requirements"]["groups"][0]["margin_bps"] = 2500
    handoff["hardware_pick_list"]["items"][0]["unit_cost_cents"] = 9000

    workbook = _xlsx_sheets(render_production_handoff_xlsx(handoff))

    assert set(workbook) == {
        "Cutting Schedule",
        "Material Summary",
        "Board Requirements",
        "Hardware Pick List",
        "Labels",
        "Warnings",
    }
    assert workbook["Cutting Schedule"][0][:5] == ["Project", "Quote", "Quote Number", "Revision", "Source"]
    assert workbook["Cutting Schedule"][1][8] == "Q-007-R2-QP-EXT-KICKER-2400X100-01"
    assert workbook["Cutting Schedule"][1][25] == "Review"
    assert workbook["Material Summary"][1][0] == "PG White (16mm)"
    assert workbook["Board Requirements"][1][0] == "PG Black (16mm)"
    assert workbook["Hardware Pick List"][1][2] == "Blum Clip top"
    assert workbook["Labels"][1][0] == "Q-007-R2-QP-EXT-KICKER-2400X100-01"
    assert workbook["Warnings"][1][-1] == "Confirm kicker split before cutting."

    flattened = "\n".join(",".join(str(value) for value in row) for rows in workbook.values() for row in rows)
    assert "margin_bps" not in flattened
    assert "unit_cost_cents" not in flattened
    assert "cost_total_cents" not in flattened


def test_production_handoff_export_filename_uses_business_context():
    filename = production_handoff_export_filename(_handoff_with_custom_panel_and_warning(), "xlsx")

    assert filename == "production-Smith-Kitchen-Phase-5-Workshop-Handoff-Q-007-rev-2.xlsx"


def _handoff_with_custom_panel_and_warning() -> dict:
    return build_production_handoff(
        quote=_quote(),
        project={"id": "project-1", "name": "Smith Kitchen Phase 5 Workshop Handoff"},
        units=[
            _unit(1, "Base Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
            _unit(2, "Wall Door", carcass_board_type_id="board-white", door_board_type_id="board-oak"),
        ],
        cutting_list={
            "runtime_rows": [
                {"unit_number": 2, "section": "panel", "desc": "Door", "length": 720, "width": 297, "qty": 2},
                {"unit_number": 1, "section": "carcass", "desc": "Side", "length": 748, "width": 564, "qty": 2},
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Kicker",
                    "length": 2400,
                    "width": 100,
                    "qty": 1,
                    "board_type_id": "board-black",
                },
                {"unit_number": 2, "section": "carcass", "desc": "Shelf", "length": 568, "width": 300, "qty": 1},
            ],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "quote_panel",
                    "unit_number": 0,
                    "section": "extra_panel",
                    "row_desc": "Kicker",
                    "reason": "Confirm kicker split before cutting.",
                }
            ],
        },
        material_summary=_material_summary(),
        hardware_pick_list=_hardware_pick_list(),
        board_lookup=_board_lookup(),
    )


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content.decode("utf-8"))))


def _xlsx_sheets(content: bytes) -> dict[str, list[list[object]]]:
    with ZipFile(BytesIO(content)) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall("pkgrel:Relationship", XLSX_NS)
        }
        sheets: dict[str, list[list[object]]] = {}
        for sheet in workbook.findall(".//main:sheets/main:sheet", XLSX_NS):
            rel_id = sheet.attrib[f"{{{XLSX_NS['rel']}}}id"]
            target = relationship_targets[rel_id].lstrip("/")
            path = target if target.startswith("xl/") else f"xl/{target}"
            root = ElementTree.fromstring(archive.read(path))
            sheets[sheet.attrib["name"]] = [
                [_cell_value(cell) for cell in row.findall("main:c", XLSX_NS)]
                for row in root.findall(".//main:sheetData/main:row", XLSX_NS)
            ]
        return sheets


def _cell_value(cell) -> object:
    if cell.attrib.get("t") == "inlineStr":
        node = cell.find(".//main:t", XLSX_NS)
        return node.text if node is not None else ""
    value = cell.find("main:v", XLSX_NS)
    if value is None or value.text is None:
        return ""
    if "." in value.text:
        return float(value.text)
    return int(value.text)


def _quote() -> dict:
    return {
        "id": "quote-1",
        "project_id": "project-1",
        "name": "Workshop Handoff",
        "status": "ready",
        "quote_number": "Q-007",
        "revision": 2,
        "default_carcass_board_type_id": "board-white",
        "default_door_board_type_id": "board-oak",
        "default_panel_board_type_id": "board-black",
        "production_metadata": {
            "door_panel": {
                "edge_banding": "1mm ABS on door edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "",
            },
            "visible_panel": {
                "edge_banding": "1mm ABS on exposed quote-panel edges",
                "grain_direction": "length",
                "rotation": "no_rotation",
                "notes": "",
            },
        },
    }


def _unit(
    unit_number: int,
    unit_type_key: str,
    *,
    carcass_board_type_id: str | None,
    door_board_type_id: str | None,
) -> dict:
    return {
        "unit_number": unit_number,
        "unit_type_key": unit_type_key,
        "carcass_board_type_id": carcass_board_type_id,
        "door_board_type_id": door_board_type_id,
    }


def _board_lookup() -> dict:
    return {
        "board-white": {
            "id": "board-white",
            "brand": "PG",
            "material": "White",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
        },
        "board-oak": {
            "id": "board-oak",
            "brand": "Seno",
            "material": "Oak",
            "thickness": 18,
            "length_mm": 2800,
            "width_mm": 1220,
        },
        "board-black": {
            "id": "board-black",
            "brand": "PG",
            "material": "Black",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
        },
    }


def _material_summary() -> dict:
    return {
        "groups": [
            {
                "board_type_id": "board-white",
                "material_role": "carcass",
                "role_label": "Carcass",
                "board_name": "PG White (16mm)",
                "brand": "PG",
                "material": "White",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "piece_count": 3,
                "area_m2": 1.01,
                "edge_m": 2.4,
                "estimated_sheets": 1,
                "cost_total_cents": 120000,
                "sell_total_cents": 150000,
            },
            {
                "board_type_id": "board-oak",
                "material_role": "door_panel",
                "role_label": "Door/Drawer Panel",
                "board_name": "Seno Oak (18mm)",
                "brand": "Seno",
                "material": "Oak",
                "thickness": 18,
                "length_mm": 2800,
                "width_mm": 1220,
                "piece_count": 2,
                "area_m2": 0.43,
                "edge_m": 1.2,
                "estimated_sheets": 1,
                "cost_total_cents": 90000,
                "sell_total_cents": 112500,
            },
            {
                "board_type_id": "board-black",
                "material_role": "visible_panel",
                "role_label": "Visible Panel",
                "board_name": "PG Black (16mm)",
                "brand": "PG",
                "material": "Black",
                "thickness": 16,
                "length_mm": 2750,
                "width_mm": 1830,
                "piece_count": 1,
                "area_m2": 0.24,
                "edge_m": 0.0,
                "estimated_sheets": 1,
                "cost_total_cents": 60000,
                "sell_total_cents": 75000,
            },
        ],
        "warnings": [],
        "total_area_m2": 1.68,
        "total_piece_count": 6,
        "total_edge_m": 3.6,
        "total_estimated_sheets": 3,
    }


def _hardware_pick_list() -> dict:
    return {
        "items": [
            {
                "item_type": "hinge",
                "type_label": "Hinges",
                "item_key": "hinge::hinge-1",
                "item_ref_id": "hinge-1",
                "item_name": "Blum Clip top",
                "supplier": "Blum",
                "code": "H110",
                "quantity": 8,
                "uom": "pcs",
                "unit_numbers": [1, 2],
                "used_in": ["Unit 1 doors", "Unit 2 doors"],
                "usage_label": "Unit 1 doors, Unit 2 doors",
            }
        ],
        "warnings": [],
        "total_item_count": 1,
        "total_quantity": 8,
    }
