from src.logic.panels import (
    PANEL_PRESET_KEYS,
    PANEL_PRESET_LABELS,
    compute_panel_rows,
    split_run_into_rows,
)


def test_split_run_into_rows_with_board_length_breaks_into_full_and_remainder():
    rows = split_run_into_rows(
        "Kicker",
        run_length=2500,
        width=100,
        board_length_mm=1200,
        board_type_id=7,
    )

    assert rows == [
        {"Desc": "Kicker", "L": 1200, "W": 100, "Qty": 2, "board_type_id": 7},
        {"Desc": "Kicker", "L": 100, "W": 100, "Qty": 1, "board_type_id": 7},
    ]


def test_compute_panel_rows_includes_presets_manual_and_auto_segments():
    units = [
        {"unit_type": "Base Door", "width": 600},
        {"unit_type": "Base Drawer", "width": 900},
        {"unit_type": "Wall Door", "width": 1200},
    ]

    state = {
        "presets": {
            "base_side_panel": {"qty": 1, "board_type_id": 10},
            "wall_side_panel": {"qty": 2, "board_type_id": 11},
            "wall_side_filler": {"qty": 1, "board_type_id": 11},
        },
        "manual": [
            {"name": "Feature End", "length": 2300, "width": 300, "qty": 1, "board_type_id": 12},
        ],
        "auto": {
            "kicker_board_type_id": 13,
            "pelmet_board_type_id": 14,
        },
    }

    def default_dims_for_panel_preset(key: str) -> tuple[int, int]:
        mapping = {
            "base_side_panel": (780, 580),
            "base_side_filler": (780, 100),
            "wall_side_panel": (720, 330),
            "wall_side_filler": (720, 100),
            "tall_side_panel": (2100, 580),
            "tall_side_filler": (2100, 100),
        }
        return mapping[key]

    def default_dims_for_unit_type(unit_type: str) -> tuple[int, int]:
        if unit_type == "Wall Door":
            return 720, 330
        return 780, 580

    board_lengths = {13: 2400, 14: 2400}

    rows = compute_panel_rows(
        units=units,
        state=state,
        default_panel_board_type_id=None,
        panel_preset_keys=PANEL_PRESET_KEYS,
        panel_preset_labels=PANEL_PRESET_LABELS,
        default_dims_for_panel_preset=default_dims_for_panel_preset,
        default_dims_for_unit_type=default_dims_for_unit_type,
        board_length_for=lambda bid: board_lengths.get(bid, 0),
    )

    descs = {r["Desc"] for r in rows}
    assert "Base Side Panel" in descs
    assert "Wall Side Panel" in descs
    assert "Wall Side Filler" in descs
    assert "Feature End" in descs
    assert "Kicker" in descs
    assert "Wall Pelmet" in descs


def test_compute_panel_rows_uses_override_values_when_enabled():
    rows = compute_panel_rows(
        units=[],
        state={
            "presets": {},
            "manual": [],
            "auto": {
                "kicker_override_on": True,
                "kicker_override_qty": 2,
                "kicker_override_length": 1800,
                "kicker_override_width": 120,
                "pelmet_override_on": True,
                "pelmet_override_qty": 1,
                "pelmet_override_length": 900,
                "pelmet_override_width": 280,
            },
        },
        default_panel_board_type_id=9,
        panel_preset_keys=PANEL_PRESET_KEYS,
        panel_preset_labels=PANEL_PRESET_LABELS,
        default_dims_for_panel_preset=lambda _k: (1, 1),
        default_dims_for_unit_type=lambda _u: (720, 330),
        board_length_for=lambda _bid: 0,
    )

    descs = {r["Desc"] for r in rows}
    assert "Kicker" in descs
    assert "Wall Pelmet" in descs
    kicker = next(r for r in rows if r["Desc"] == "Kicker")
    pelmet = next(r for r in rows if r["Desc"] == "Wall Pelmet")
    assert kicker["L"] == 1800 and kicker["W"] == 120 and kicker["Qty"] == 2
    assert pelmet["L"] == 900 and pelmet["W"] == 280 and pelmet["Qty"] == 1
