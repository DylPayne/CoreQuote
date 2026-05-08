"""
units/__init__.py
Re-exports the public API so existing imports like:
    from logic.units import DrawerUnit, DoorUnit
continue to work without modification.
"""

from logic.units.types import DrawerUnit, DoorUnit, WallUnit, TallUnit
from logic.units.base import CabinetUnit
from logic.units.definitions import (
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
