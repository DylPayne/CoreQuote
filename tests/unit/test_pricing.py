import importlib
import pytest


def _setup_isolated_db(tmp_path, monkeypatch):
    import logic.database as db

    db_file = tmp_path / "test_corequote.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_file), raising=False)
    db.init_db()
    return db


def test_pricing_run_snapshot_immutable_after_price_change(tmp_path, monkeypatch):
    db = _setup_isolated_db(tmp_path, monkeypatch)
    pricing = importlib.import_module("logic.pricing")

    project_id = db.create_project("P1")
    quote_id = db.create_quote(project_id=project_id, name="Q1")

    slide_id = db.create_slide("Blum", "Movento", "MV500", 500, 450, 13)
    slide = [s for s in db.get_all_slides() if s["id"] == slide_id][0]
    db.add_unit(
        quote_id=quote_id,
        unit_type="Base Drawer",
        height=780,
        width=600,
        depth=560,
        thickness=16,
        extra_params={
            "num_drawers": 3,
            "slide_brand": slide["brand"],
            "slide_model": slide["model"],
            "slide_code": slide["code"],
            "slide_length": slide["length"],
            "slide_side_length": slide["side_length"],
            "slide_side_clearance_total": slide["side_clearance_total"],
            "handle_qty": 0,
        },
    )

    active = db.get_active_price_list()
    assert active is not None
    plist_id = int(active["id"])
    slide_item_key = "slide::Blum::Movento::MV500::500"
    db.upsert_price_list_item(plist_id, "slide", slide_item_key, "pairs", 10000)

    run1 = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)
    assert run1.subtotal_cents == 30000

    db.upsert_price_list_item(plist_id, "slide", slide_item_key, "pairs", 20000)
    run2 = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)
    assert run2.subtotal_cents == 60000

    runs = db.get_quote_pricing_runs(quote_id)
    assert len(runs) >= 2
    latest = runs[0]
    previous = runs[1]
    assert int(latest["subtotal_cents"]) == 60000
    assert int(previous["subtotal_cents"]) == 30000


def test_pricing_markup_and_margin_modes(tmp_path, monkeypatch):
    db = _setup_isolated_db(tmp_path, monkeypatch)
    pricing = importlib.import_module("logic.pricing")

    project_id = db.create_project("P2")
    quote_id = db.create_quote(project_id=project_id, name="Q2")
    active = db.get_active_price_list()
    plist_id = int(active["id"])

    cat_id = db.create_extra_category("Accessories")
    extra_id = db.create_extra("Shelf Pins", cat_id, "", "")
    db.add_quote_extra(quote_id, extra_id, qty=2)
    db.upsert_price_list_item(plist_id, "extra", f"extra::{extra_id}", "pcs", 10000)

    db.update_vat_rate_bps(1500)
    run_markup = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=25.0)
    assert run_markup.subtotal_cents == 20000
    assert run_markup.sell_before_vat_cents == 25000
    assert run_markup.vat_cents == 3750
    assert run_markup.grand_total_cents == 28750

    run_margin = pricing.price_quote(quote_id=quote_id, pricing_mode="margin", pricing_value_percent=20.0)
    assert run_margin.subtotal_cents == 20000
    assert run_margin.sell_before_vat_cents == 25000


def test_vat_rate_is_snapshotted_per_run(tmp_path, monkeypatch):
    db = _setup_isolated_db(tmp_path, monkeypatch)
    pricing = importlib.import_module("logic.pricing")

    project_id = db.create_project("P3")
    quote_id = db.create_quote(project_id=project_id, name="Q3")
    active = db.get_active_price_list()
    plist_id = int(active["id"])

    cat_id = db.create_extra_category("Services")
    extra_id = db.create_extra("Delivery", cat_id, "", "")
    db.add_quote_extra(quote_id, extra_id, qty=1)
    db.upsert_price_list_item(plist_id, "extra", f"extra::{extra_id}", "pcs", 10000)

    db.update_vat_rate_bps(1500)
    run1 = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)
    db.update_vat_rate_bps(1600)
    run2 = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)

    rows = db.get_quote_pricing_runs(quote_id)
    assert int(rows[0]["id"]) == run2.run_id
    assert int(rows[0]["vat_rate_bps_snapshot"]) == 1600
    assert int(rows[1]["id"]) == run1.run_id
    assert int(rows[1]["vat_rate_bps_snapshot"]) == 1500


def test_board_items_are_required_and_priced_in_quote(tmp_path, monkeypatch):
    db = _setup_isolated_db(tmp_path, monkeypatch)
    pricing = importlib.import_module("logic.pricing")

    board_id = db.create_board_type(
        "PG",
        "White Melamine",
        16,
        2750,
        1830,
        costing_mode="sheet",
        edging_cost_cents_per_m=100,
        cut_edge_labour_cents_per_board=500,
        sqm_price_cents=0,
    )
    project_id = db.create_project("P4")
    quote_id = db.create_quote(
        project_id=project_id,
        name="Q4",
        default_carcass_board_type_id=board_id,
        default_door_board_type_id=board_id,
        default_panel_board_type_id=board_id,
    )

    db.add_unit(
        quote_id=quote_id,
        unit_type="Base Door",
        height=780,
        width=900,
        depth=560,
        thickness=16,
        carcass_board_type_id=board_id,
        door_board_type_id=board_id,
        extra_params={"num_doors": 2, "handle_qty": 0},
    )

    required = pricing.get_required_price_items(quote_id)
    board_items = [r for r in required if r.item_type == "board"]
    assert board_items, "Expected at least one board pricing item"
    keys = {r.item_key for r in board_items}
    assert any(k.endswith("::sheet") for k in keys)
    assert any(k.endswith("::edging_m") for k in keys)
    assert any(k.endswith("::labour_board") for k in keys)
    assert all(r.qty_required >= 0 for r in board_items)

    with pytest.raises(ValueError, match="Missing prices for required items"):
        pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)

    active = db.get_active_price_list()
    assert active is not None
    plist_id = int(active["id"])
    board_price_cents = 10000
    for row in board_items:
        if row.item_key.endswith("::sheet"):
            db.upsert_price_list_item(plist_id, "board", row.item_key, "sheet", board_price_cents)
        elif row.item_key.endswith("::edging_m"):
            db.upsert_price_list_item(plist_id, "board", row.item_key, "m", 100)
        elif row.item_key.endswith("::labour_board"):
            db.upsert_price_list_item(plist_id, "board", row.item_key, "board", 500)

    # Base Door units require hinge pricing too; use zero to isolate board subtotal assertion.
    db.upsert_price_list_item(plist_id, "hinge", "hinge::::::::", "pcs", 0)

    run = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)
    board_line = None
    lines = db.get_quote_pricing_lines(run.run_id)
    for line in lines:
        if str(line.get("source_type")) == "board":
            board_line = line
            break
    assert board_line is not None
    meta = board_line.get("meta", {})
    expected_material = int(meta.get("material_total_cents", 0))
    expected_edging = int(meta.get("edging_total_cents", 0))
    expected_labour = int(meta.get("labour_total_cents", 0))
    assert int(board_line["line_total_cents_snapshot"]) == expected_material + expected_edging + expected_labour
    assert run.subtotal_cents == int(board_line["line_total_cents_snapshot"])


def test_board_sqm_mode_prices_by_area_without_price_list_item(tmp_path, monkeypatch):
    db = _setup_isolated_db(tmp_path, monkeypatch)
    pricing = importlib.import_module("logic.pricing")

    board_id = db.create_board_type(
        "Niemann",
        "Ultra Gloss",
        18,
        2800,
        2070,
        costing_mode="sqm",
        edging_cost_cents_per_m=0,
        cut_edge_labour_cents_per_board=0,
        sqm_price_cents=0,
    )
    project_id = db.create_project("P5")
    quote_id = db.create_quote(
        project_id=project_id,
        name="Q5",
        default_carcass_board_type_id=board_id,
        default_door_board_type_id=board_id,
        default_panel_board_type_id=board_id,
    )

    db.add_unit(
        quote_id=quote_id,
        unit_type="Base Door",
        height=780,
        width=900,
        depth=560,
        thickness=18,
        carcass_board_type_id=board_id,
        door_board_type_id=board_id,
        extra_params={"num_doors": 2, "handle_qty": 0},
    )

    # SQM mode should use pricing table key board::{id}::sqm.
    db.upsert_price_list_item(int(db.get_active_price_list()["id"]), "hinge", "hinge::::::::", "pcs", 0)
    db.upsert_price_list_item(int(db.get_active_price_list()["id"]), "board", f"board::{board_id}::sqm", "m2", 10000)
    run = pricing.price_quote(quote_id=quote_id, pricing_mode="markup", pricing_value_percent=0.0)
    lines = db.get_quote_pricing_lines(run.run_id)
    board_lines = [l for l in lines if str(l.get("source_type")) == "board"]
    assert board_lines
    assert all(str(l.get("uom")) == "m2" for l in board_lines)
    assert int(sum(int(l["line_total_cents_snapshot"]) for l in board_lines)) > 0
