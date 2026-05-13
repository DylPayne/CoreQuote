"""
models.py
────────────────────────────────────────────────────────────────────────────────
Core data models shared across the entire logic layer.

These are intentionally plain dataclasses — no methods, no business logic.
They act as typed value objects that flow between the unit definitions,
the cutting engine, and the cutlist builder.
"""

from dataclasses import dataclass


@dataclass
class Board:
    """
    A single cut board / panel in the cutting schedule.

    Attributes:
        name   (str): Human-readable description, e.g. "Side", "Drawer Base".
        length (int): Longer dimension in mm (typically the vertical axis).
        width  (int): Shorter dimension in mm (typically the horizontal axis).
        qty    (int): How many identical pieces are required.
    """
    name:   str
    length: int
    width:  int
    qty:    int


@dataclass
class Slide:
    """
    Drawer slide hardware specification.

    Attributes:
        brand                (str): Manufacturer name, e.g. "Grass".
        model                (str): Product line, e.g. "Dynapro".
        code                 (str): SKU / product code.
        length               (int): Nominal slide length in mm (e.g. 500).
        side_length          (int): Actual drawer-box running depth in mm.
                                    Usually slightly less than `length`.
        side_clearance_total (int): Required clearance per side (left OR right)
                                    in mm between drawer box and cabinet interior.
                                    drawer_box_width = cabinet_width - (2 × side_clearance_total)
    """
    brand:                str
    model:                str
    code:                 str
    length:               int
    side_length:          int
    side_clearance_total: int
    side_height_uplift:   int = 0
