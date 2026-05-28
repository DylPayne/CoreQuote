import importlib.util
import sys
from pathlib import Path


IMPORTER_PATH = Path(__file__).resolve().parents[2] / "infra" / "db" / "import_sqlite_libraries.py"
spec = importlib.util.spec_from_file_location("import_sqlite_libraries", IMPORTER_PATH)
assert spec and spec.loader
importer = importlib.util.module_from_spec(spec)
sys.modules["import_sqlite_libraries"] = importer
spec.loader.exec_module(importer)
remap_price_item = importer.remap_price_item


def test_remap_price_item_rewrites_board_keys_to_new_uuid():
    row = {
        "item_type": "board",
        "item_ref_id": None,
        "item_key": "board::1::sheet",
        "uom": "sheet",
        "unit_price_cents": 70282,
    }
    id_map = {"board_types": {1: "board-uuid"}}

    assert remap_price_item(row, id_map) == {
        "item_type": "board",
        "item_ref_id": "board-uuid",
        "item_key": "board::board-uuid",
        "price_component": "sheet",
        "uom": "sheet",
        "unit_price_cents": 70282,
    }


def test_remap_price_item_rewrites_extra_keys_to_new_uuid():
    row = {
        "item_type": "extra",
        "item_ref_id": "",
        "item_key": "extra::1",
        "uom": "pcs",
        "unit_price_cents": 750000,
    }
    id_map = {"extras": {1: "extra-uuid"}}

    assert remap_price_item(row, id_map) == {
        "item_type": "extra",
        "item_ref_id": "extra-uuid",
        "item_key": "extra::extra-uuid",
        "price_component": "unit",
        "uom": "pcs",
        "unit_price_cents": 750000,
    }


def test_remap_price_item_preserves_natural_slide_key():
    row = {
        "item_type": "slide",
        "item_ref_id": None,
        "item_key": "slide::Grass::Dynapro::12346::500",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 100000,
    }

    assert remap_price_item(row, {"slides": {1: "slide-uuid"}}) == {
        "item_type": "slide",
        "item_ref_id": None,
        "item_key": "slide::Grass::Dynapro::12346::500",
        "price_component": "unit",
        "uom": "pairs",
        "unit_price_cents": 100000,
    }
