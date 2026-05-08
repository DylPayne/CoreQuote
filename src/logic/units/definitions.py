"""
units/definitions.py
────────────────────────────────────────────────────────────────────────────────
Single source of truth for every cabinet unit type in the system.

HOW TO ADD A NEW UNIT TYPE
──────────────────────────
1. Create a new config dataclass (or reuse an existing one) below.
2. Add an entry to UNIT_REGISTRY with a unique string key.
3. Create a matching concrete class in types.py (inheriting CabinetUnit).
4. Add a matching CuttingStrategy in cutting/strategies.py.

That's it — no other files need to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ── Shared constraint types ────────────────────────────────────────────────────

@dataclass(frozen=True)
class DimensionBounds:
    """Min/max guardrails for a single dimension (mm)."""
    min_mm: int
    max_mm: int


# ── Per-variant config dataclasses ────────────────────────────────────────────

@dataclass(frozen=True)
class DrawerConfig:
    """
    Configuration for a drawer-based base unit.

    Attributes:
        num_drawers:    How many drawers this variant has (1–4).
        drawer_side_h:  Default drawer-box side height in mm.
        panel_gap_mm:   Gap between adjacent drawer fronts in mm.
    """
    num_drawers: Literal[1, 2, 3, 4]
    drawer_side_h: int = 200          # mm — standard Grass/Blum box height
    panel_gap_mm: int = 3             # mm — gap between drawer fronts


@dataclass(frozen=True)
class DoorConfig:
    """
    Configuration for a door-based base or wall unit.

    Attributes:
        num_doors:      How many doors this variant has (1–2).
        default_shelves: Suggested shelf count (user can override).
        shelf_setback:  How far the shelf sits back from the door plane (mm).
        panel_gap_mm:   Gap between adjacent doors in mm.
    """
    num_doors: Literal[1, 2]
    default_shelves: int = 1
    shelf_setback: int = 20           # mm
    panel_gap_mm: int = 3             # mm


@dataclass(frozen=True)
class WallConfig:
    """
    Configuration for a wall-hung unit.

    Attributes:
        num_doors:      How many doors (1–2).
        default_shelves: Suggested shelf count.
        shelf_setback:  Shelf setback from door plane (mm).
        panel_gap_mm:   Gap between adjacent doors (mm).
    """
    num_doors: Literal[1, 2]
    default_shelves: int = 1
    shelf_setback: int = 20
    panel_gap_mm: int = 3


@dataclass(frozen=True)
class TallConfig:
    """
    Configuration for a tall / pantry unit.

    Attributes:
        num_doors:       How many doors (typically 2 for a pantry).
        default_shelves: Suggested shelf count.
        shelf_setback:   Shelf setback from door plane (mm).
        panel_gap_mm:    Gap between adjacent doors (mm).
        is_pantry:       True → pantry variant (taller default height).
    """
    num_doors: Literal[1, 2] = 2
    default_shelves: int = 4
    shelf_setback: int = 20
    panel_gap_mm: int = 3
    is_pantry: bool = False


# ── Master unit config ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class UnitConfig:
    """
    Top-level descriptor for a cabinet unit variant.

    Attributes:
        key:            Unique string identifier used in the DB and UI.
        label:          Human-readable display name.
        category:       Broad family: "base", "wall", or "tall".
        variant_config: The specific config dataclass for this variant.
        default_h:      Default height in mm.
        default_w:      Default width in mm.
        default_d:      Default depth in mm.
        height_bounds:  Allowed height range.
        width_bounds:   Allowed width range.
        depth_bounds:   Allowed depth range.
    """
    key: str
    label: str
    category: Literal["base", "wall", "tall"]
    variant_config: DrawerConfig | DoorConfig | WallConfig | TallConfig

    # Sensible defaults for the Add-Unit dialog
    default_h: int = 720
    default_w: int = 600
    default_d: int = 560

    # Validation guardrails
    height_bounds: DimensionBounds = field(
        default_factory=lambda: DimensionBounds(300, 2400)
    )
    width_bounds: DimensionBounds = field(
        default_factory=lambda: DimensionBounds(150, 1200)
    )
    depth_bounds: DimensionBounds = field(
        default_factory=lambda: DimensionBounds(150, 700)
    )


# ── Unit Registry ──────────────────────────────────────────────────────────────
#
# UNIT_REGISTRY is the single place where every supported unit variant lives.
# The key is the string stored in the database `unit_type` column.
#
# To add a new variant:
#   1. Define its config below.
#   2. Add it here with a unique key.
#   3. Add the matching class in types.py and strategy in cutting/strategies.py.

UNIT_REGISTRY: dict[str, UnitConfig] = {

    # ── Base Units ─────────────────────────────────────────────────────────────

    "Base 3 Draw": UnitConfig(
        key="Base 3 Draw",
        label="Base 3 Draw",
        category="base",
        variant_config=DrawerConfig(num_drawers=3),
        default_h=780, default_w=600, default_d=580,
    ),
    "Base 1 Draw": UnitConfig(
        key="Base 1 Draw",
        label="Base 1 Draw",
        category="base",
        variant_config=DrawerConfig(num_drawers=1),
        default_h=780, default_w=600, default_d=580,
    ),
    "Base 2 Draw": UnitConfig(
        key="Base 2 Draw",
        label="Base 2 Draw",
        category="base",
        variant_config=DrawerConfig(num_drawers=2),
        default_h=780, default_w=600, default_d=580,
    ),
    "Base 4 Draw": UnitConfig(
        key="Base 4 Draw",
        label="Base 4 Draw",
        category="base",
        variant_config=DrawerConfig(num_drawers=4),
        default_h=780, default_w=600, default_d=580,
    ),
    "Base 2 Door": UnitConfig(
        key="Base 2 Door",
        label="Base 2 Door",
        category="base",
        variant_config=DoorConfig(num_doors=2),
        default_h=780, default_w=600, default_d=580,
    ),
    "Base 1 Door": UnitConfig(
        key="Base 1 Door",
        label="Base 1 Door",
        category="base",
        variant_config=DoorConfig(num_doors=1),
        default_h=780, default_w=400, default_d=580,
    ),

    # ── Wall Units ─────────────────────────────────────────────────────────────

    "Wall 2 Door": UnitConfig(
        key="Wall 2 Door",
        label="Wall 2 Door",
        category="wall",
        variant_config=WallConfig(num_doors=2),
        default_h=720, default_w=600, default_d=330,
        depth_bounds=DimensionBounds(150, 450),
    ),
    "Wall 1 Door": UnitConfig(
        key="Wall 1 Door",
        label="Wall 1 Door",
        category="wall",
        variant_config=WallConfig(num_doors=1),
        default_h=720, default_w=400, default_d=330,
        depth_bounds=DimensionBounds(150, 450),
    ),

    # ── Tall Units ─────────────────────────────────────────────────────────────

    "Tall Standard": UnitConfig(
        key="Tall Standard",
        label="Tall Standard",
        category="tall",
        variant_config=TallConfig(num_doors=2, default_shelves=4, is_pantry=False),
        default_h=2100, default_w=600, default_d=580,
        height_bounds=DimensionBounds(1800, 2400),
    ),
    "Tall Pantry": UnitConfig(
        key="Tall Pantry",
        label="Tall Pantry",
        category="tall",
        variant_config=TallConfig(num_doors=2, default_shelves=6, is_pantry=True),
        default_h=2400, default_w=600, default_d=580,
        height_bounds=DimensionBounds(2100, 2700),
    ),
}
