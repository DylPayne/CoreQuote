"""
units.py  ← COMPATIBILITY SHIM — DO NOT ADD LOGIC HERE
────────────────────────────────────────────────────────────────────────────────
This file previously contained BaseUnit, DrawerUnit, and DoorUnit.

The unit system has been refactored into the `units/` package:

    logic/units/
    ├── __init__.py      ← public re-exports (same API as before)
    ├── base.py          ← CabinetUnit abstract base class
    ├── types.py         ← DrawerUnit, DoorUnit, WallUnit, TallUnit
    └── definitions.py   ← UNIT_REGISTRY, UnitConfig, DrawerConfig, etc.

All existing imports of the form:
    from logic.units import DrawerUnit, DoorUnit
continue to work unchanged because logic/units/__init__.py re-exports them.

This file is kept only so that any direct import of `logic.units` as a module
(rather than a package) does not break.  It simply re-exports from the package.
"""

# Re-export everything from the new package so old-style imports still work.
from logic.units.types import DrawerUnit, DoorUnit, WallUnit, TallUnit  # noqa: F401
from logic.units.base import CabinetUnit                                 # noqa: F401
