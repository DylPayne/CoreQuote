"""
units/__init__.py
Re-exports the public API so existing imports like:
    from corequote_core.units import DrawerUnit, DoorUnit
continue to work without modification.
"""

from corequote_core.units.types import DrawerUnit, DoorUnit, WallUnit, TallUnit
from corequote_core.units.base import CabinetUnit
from corequote_core.units.definitions import (
    UNIT_REGISTRY,
    UnitConfig,
    DrawerConfig,
    DoorConfig,
    WallConfig,
    TallConfig,
)

__all__ = [
    # Concrete unit classes
    "DrawerUnit",
    "DoorUnit",
    "WallUnit",
    "TallUnit",
    # Abstract base
    "CabinetUnit",
    # Config types & registry
    "UNIT_REGISTRY",
    "UnitConfig",
    "DrawerConfig",
    "DoorConfig",
    "WallConfig",
    "TallConfig",
]
