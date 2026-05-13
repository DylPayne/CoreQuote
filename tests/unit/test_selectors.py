from src.ui.selectors import (
    board_index_for_id,
    handle_id_from_quote,
    handle_payload_from_id,
    hinge_id_from_quote,
    hinge_payload_from_id,
    slide_id_from_quote,
    slide_payload_from_id,
)


def test_board_index_for_id():
    ids = [None, 10, 20]
    assert board_index_for_id(ids, 20) == 2
    assert board_index_for_id(ids, 999) == 0


def test_slide_payload_from_id_and_missing():
    lookup = {
        1: {
            "brand": "Blum",
            "model": "Movento",
            "code": "M500",
            "length": 500,
            "side_length": 500,
            "side_clearance_total": 13,
            "side_height_uplift": 0,
        }
    }
    assert slide_payload_from_id(lookup, 1)["brand"] == "Blum"
    assert slide_payload_from_id(lookup, None) == {}
    assert slide_payload_from_id(lookup, 999) == {}


def test_hinge_payload_from_id_and_missing():
    lookup = {1: {"brand": "Blum", "model": "Clip Top", "code": "CT", "opening_angle_deg": 110}}
    assert hinge_payload_from_id(lookup, 1)["model"] == "Clip Top"
    assert hinge_payload_from_id(lookup, None) == {}


def test_handle_payload_from_id_and_missing():
    lookup = {1: {"name": "Slim Bar", "supplier": "Hafele", "code": "HB-1"}}
    assert handle_payload_from_id(lookup, 1)["name"] == "Slim Bar"
    assert handle_payload_from_id(lookup, None) == {}


def test_slide_and_hinge_id_from_quote_with_fallback():
    slides = [{"id": 1, "brand": "A", "model": "B", "code": "C"}]
    slide_ids = [1]
    quote = {"default_slide_brand": "A", "default_slide_model": "B", "default_slide_code": "C"}
    assert slide_id_from_quote(slides, slide_ids, quote) == 1
    assert slide_id_from_quote(slides, slide_ids, None) == 1

    hinges = [{"id": 2, "brand": "H", "model": "M", "code": "X"}]
    hinge_ids = [2]
    q2 = {"default_hinge_brand": "H", "default_hinge_model": "M", "default_hinge_code": "X"}
    assert hinge_id_from_quote(hinges, hinge_ids, q2) == 2


def test_handle_id_from_quote_prefix_match_and_fallback():
    handles = [{"id": 5, "name": "Slim Bar", "supplier": "Hafele", "code": "HB-1"}]
    handle_ids = [5]
    quote = {
        "default_base_handle_name": "Slim Bar",
        "default_base_handle_supplier": "Hafele",
        "default_base_handle_code": "HB-1",
    }
    assert handle_id_from_quote(handles, handle_ids, quote, "base") == 5
    assert handle_id_from_quote(handles, handle_ids, None, "base") == 5
