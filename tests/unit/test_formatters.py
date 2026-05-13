from src.ui.formatters import (
    format_board_label,
    format_handle_label,
    format_hinge_label,
    format_slide_label,
)


def test_format_board_label():
    label = format_board_label(
        {
            "brand": "PG Bison",
            "material": "MDF",
            "thickness": 16,
            "length_mm": 2750,
            "width_mm": 1830,
        }
    )
    assert label == "PG Bison • MDF • 16mm • 2750x1830"


def test_format_slide_label():
    label = format_slide_label({"brand": "Blum", "model": "Movento", "length": 500})
    assert label == "Blum Movento (500mm)"


def test_format_hinge_label():
    label = format_hinge_label({"brand": "Blum", "model": "Clip Top", "opening_angle_deg": 110})
    assert label == "Blum Clip Top (110°)"


def test_format_handle_label_with_optional_parts():
    assert format_handle_label({"name": "Slim Bar", "supplier": "Hafele", "code": "HB-1"}) == "Slim Bar • Hafele • HB-1"
    assert format_handle_label({"name": "Slim Bar", "supplier": "", "code": ""}) == "Slim Bar"
    assert format_handle_label({"name": "", "supplier": "", "code": ""}) == "Handle"
