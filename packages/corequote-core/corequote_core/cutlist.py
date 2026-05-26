"""
cutlist.py
────────────────────────────────────────────────────────────────────────────────
Builds a full cutting list from all units in a quote.

Each board row is tagged with the unit number it belongs to.

This module is the integration layer between the database (raw dicts) and the
cutting engine (typed unit objects + strategies).  It is intentionally thin:
  1. Deserialise each unit dict into a typed CabinetUnit subclass.
  2. Ask the CuttingEngine for carcass boards and panel boards.
  3. Flatten everything into two DataFrames.

Adding support for a new unit type here requires only one new `elif` branch
in `_build_unit_from_dict`.
"""

from __future__ import annotations

import pandas as pd

from corequote_core.models import Slide
from corequote_core.units import DrawerUnit, DoorUnit, WallUnit, TallUnit
from corequote_core.cutting.engine import CuttingEngine


# ── Private helpers ────────────────────────────────────────────────────────────

def _slide_from_params(extra: dict) -> Slide:
    """Reconstruct a Slide dataclass from the extra_params dict stored in the DB."""
    return Slide(
        brand                = extra.get("slide_brand", ""),
        model                = extra.get("slide_model", ""),
        code                 = extra.get("slide_code", ""),
        length               = int(extra.get("slide_length", 0)),
        side_length          = int(extra.get("slide_side_length", 0)),
        side_clearance_total = int(extra.get("slide_side_clearance_total", 0)),
        side_height_uplift   = int(extra.get("slide_side_height_uplift", 0)),
    )


def _build_unit_from_dict(u: dict):
    """
    Deserialise a unit dict (from database.get_units_for_quote) into a
    typed CabinetUnit subclass.

    Args:
        u: A unit dict with keys: unit_type, height, width, depth,
           thickness, extra_params.

    Returns:
        A CabinetUnit subclass instance, or None if the unit_type is unknown.
    """
    h, w, d = u["height"], u["width"], u["depth"]
    t       = int(u.get("thickness", 16) or 16)
    extra   = u.get("extra_params", {})
    utype   = u["unit_type"]

    if utype in ("Base Drawer", "Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"):
        default_drawers = 3
        if utype in ("Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"):
            default_drawers = int(utype.split()[1])
        num_drawers = int(extra.get("num_drawers", default_drawers))
        slide       = _slide_from_params(extra)
        ratios_raw  = extra.get("drawer_face_ratios")
        drawer_face_ratios = ratios_raw if isinstance(ratios_raw, list) else None
        heights_raw = extra.get("drawer_face_heights")
        drawer_face_heights = heights_raw if isinstance(heights_raw, list) else None
        return DrawerUnit(h=h, w=w, d=d, slide=slide,
                          num_drawers=num_drawers,
                          drawer_face_ratios=drawer_face_ratios,
                          drawer_face_heights=drawer_face_heights,
                          thickness=t)

    elif utype in ("Base Door", "Base 1 Door", "Base 2 Door"):
        default_doors = int(utype.split()[1]) if utype in ("Base 1 Door", "Base 2 Door") else 2
        num_doors   = int(extra.get("num_doors", default_doors))
        num_shelves = int(extra.get("num_shelves", 1))
        return DoorUnit(h=h, w=w, d=d,
                        num_doors=num_doors, num_shelves=num_shelves,
                        thickness=t)

    elif utype in ("Wall Door", "Wall 1 Door", "Wall 2 Door"):
        default_doors = int(utype.split()[1]) if utype in ("Wall 1 Door", "Wall 2 Door") else 2
        num_doors   = int(extra.get("num_doors", default_doors))
        num_shelves = int(extra.get("num_shelves", 1))
        return WallUnit(h=h, w=w, d=d,
                        num_doors=num_doors, num_shelves=num_shelves,
                        thickness=t)

    elif utype in ("Tall Standard", "Tall Pantry"):
        num_doors   = int(extra.get("num_doors", 2))
        num_shelves = int(extra.get("num_shelves", 4))
        is_pantry   = utype == "Tall Pantry"
        return TallUnit(h=h, w=w, d=d,
                        num_doors=num_doors, num_shelves=num_shelves,
                        is_pantry=is_pantry, thickness=t)

    # Unknown type — caller will skip this unit.
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def build_cutlist(units: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build a full cutting list from a list of unit dicts.

    Args:
        units: List of unit dicts as returned by database.get_units_for_quote.
               Each dict must contain: unit_number, unit_type, height, width,
               depth, thickness, extra_params.

    Returns:
        (carcass_df, panels_df) — two DataFrames, each with columns:
            "Unit #", "Desc", "L", "W", "Qty"
    """
    carcass_rows: list[dict] = []
    panel_rows:   list[dict] = []

    for u in units:
        unit_num = u["unit_number"]
        unit_obj = _build_unit_from_dict(u)

        if unit_obj is None:
            # Gracefully skip unknown unit types rather than crashing.
            continue

        # Delegate all dimension maths to the CuttingEngine.
        result = CuttingEngine.calculate(unit_obj)

        for board in result.carcass_boards:
            carcass_rows.append({
                "Unit #": unit_num,
                "Desc":   board.name,
                "L":      board.length,
                "W":      board.width,
                "Qty":    board.qty,
            })

        for board in result.panel_boards:
            panel_rows.append({
                "Unit #": unit_num,
                "Desc":   board.name,
                "L":      board.length,
                "W":      board.width,
                "Qty":    board.qty,
            })

    carcass_df = pd.DataFrame(carcass_rows, columns=["Unit #", "Desc", "L", "W", "Qty"])
    panels_df  = pd.DataFrame(panel_rows,   columns=["Unit #", "Desc", "L", "W", "Qty"])
    return carcass_df, panels_df
