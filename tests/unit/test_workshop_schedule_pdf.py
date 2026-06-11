from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from corequote_core.workshop_schedule_pdf import (
    build_workshop_schedule_document,
    render_workshop_schedule_pdf,
    workshop_schedule_filename,
)


def test_workshop_schedule_document_groups_rows_and_marks_invalid_rows():
    document = build_workshop_schedule_document(
        company={"name": "CoreQuote Test Co"},
        quote={
            "name": "Smith Kitchen Quote v1",
            "quote_number": "Q-001",
            "revision": 2,
            "default_carcass_board_type_id": "board-carcass",
            "default_door_board_type_id": "board-door",
            "default_panel_board_type_id": "board-visible",
        },
        project={
            "name": "Smith Kitchen",
            "client": "Alex Smith",
            "address": "12 Oak Street",
        },
        units=[
            {
                "unit_number": 1,
                "carcass_board_type_id": None,
                "door_board_type_id": "board-door",
            }
        ],
        cutting_list={
            "runtime_rows": [
                {
                    "unit_number": 1,
                    "section": "carcass",
                    "desc": "Side",
                    "length": 748,
                    "width": 564,
                    "qty": 2,
                },
                {
                    "unit_number": 1,
                    "section": "panel",
                    "desc": "Door",
                    "length": 777,
                    "width": 297,
                    "qty": 2,
                },
                {
                    "unit_number": 0,
                    "section": "extra_panel",
                    "desc": "Kicker",
                    "length": 0,
                    "width": 100,
                    "qty": 1,
                    "board_type_id": "board-visible",
                },
            ],
            "validation_warnings": [
                {
                    "severity": "warning",
                    "source": "quote_panel",
                    "unit_number": 0,
                    "section": "extra_panel",
                    "row_desc": "Kicker",
                    "reason": "Length must be greater than 0 mm.",
                }
            ],
        },
        board_lookup={
            "board-carcass": {"brand": "PG", "material": "White", "thickness": 16},
            "board-door": {"brand": "Seno", "material": "Matte Grey", "thickness": 18},
            "board-visible": {"brand": "PG", "material": "Visible Oak", "thickness": 18},
        },
        export_date=date(2026, 6, 11),
    )

    assert document.company_name == "CoreQuote Test Co"
    assert document.project_name == "Smith Kitchen"
    assert document.client_name == "Alex Smith"
    assert document.quote_number == "Q-001"
    assert document.revision == 2
    assert document.export_date == date(2026, 6, 11)

    assert [group.title for group in document.groups] == ["Carcass rows", "Panel rows", "Custom panel rows"]
    assert document.groups[0].rows[0].board_material == "PG White 16mm"
    assert document.groups[1].rows[0].board_material == "Seno Matte Grey 18mm"
    assert document.groups[2].rows[0].unit_label == "Quote"
    assert document.groups[2].rows[0].status == "Check"
    assert document.groups[2].rows[0].warning_reasons == ["Length must be greater than 0 mm."]
    assert document.warnings[0].reason == "Length must be greater than 0 mm."

    for key in _keys(asdict(document)):
        assert "cost" not in key
        assert "profit" not in key
        assert "margin" not in key
        assert "price" not in key


def test_workshop_schedule_pdf_renders_bytes_and_business_filename():
    document = build_workshop_schedule_document(
        company={"name": "CoreQuote Test Co"},
        quote={"name": "Smith Kitchen Quote v1", "quote_number": "Q-001", "revision": 1},
        project={"name": "Smith Kitchen", "client": "Alex Smith", "address": "12 Oak Street"},
        units=[],
        cutting_list={
            "carcass": [{"unit_number": 1, "desc": "Side", "length": 748, "width": 564, "qty": 2}],
            "panels": [{"unit_number": 1, "desc": "Door", "length": 777, "width": 297, "qty": 2}],
            "extras": [{"unit_number": 0, "desc": "Kicker", "length": 1760, "width": 100, "qty": 1}],
            "validation_warnings": [],
        },
        board_lookup={},
        export_date=date(2026, 6, 11),
    )

    assert workshop_schedule_filename(document) == "workshop-Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"
    pdf_bytes = render_workshop_schedule_pdf(document)
    assert bytes(pdf_bytes).startswith(b"%PDF")


def _keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            found.append(str(key))
            found.extend(_keys(child))
        return found
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(_keys(child))
        return found
    return []
