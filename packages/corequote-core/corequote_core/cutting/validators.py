"""
cutting/validators.py
────────────────────────────────────────────────────────────────────────────────
Validation helpers for cabinet unit dimensions and hardware compatibility.

All validators raise `ValidationError` on failure so callers can catch a
single, well-typed exception rather than checking boolean return values.

Usage example:
    from corequote_core.cutting.validators import validate_dimensions, validate_slide_fit

    try:
        validate_dimensions(unit, config)
        validate_slide_fit(unit)
    except ValidationError as exc:
        st.error(str(exc))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from corequote_core.units.base import CabinetUnit
    from corequote_core.units.definitions import UnitConfig


# ── Custom exception ───────────────────────────────────────────────────────────

class ValidationError(ValueError):
    """
    Raised when a cabinet unit fails a validation check.

    Inherits from ValueError so it can be caught generically if needed,
    but is distinct enough to be caught specifically.
    """


# ── Dimension validators ───────────────────────────────────────────────────────

def validate_dimensions(unit: "CabinetUnit", config: "UnitConfig") -> None:
    """
    Verify that h, w, d all fall within the bounds defined in UnitConfig.

    Args:
        unit:   The cabinet unit to validate.
        config: The UnitConfig that defines the allowed dimension ranges.

    Raises:
        ValidationError: If any dimension is outside its allowed range.
    """
    checks = [
        ("Height", unit.h, config.height_bounds),
        ("Width",  unit.w, config.width_bounds),
        ("Depth",  unit.d, config.depth_bounds),
    ]
    for label, value, bounds in checks:
        if not (bounds.min_mm <= value <= bounds.max_mm):
            raise ValidationError(
                f"{label} {value} mm is outside the allowed range "
                f"[{bounds.min_mm}–{bounds.max_mm} mm] "
                f"for a '{config.label}'."
            )


def validate_slide_fit(unit: "CabinetUnit") -> None:
    """
    Verify that the drawer slide fits within the cabinet's internal depth.

    Only applicable to DrawerUnit instances; silently passes for all others.

    Args:
        unit: The cabinet unit to validate.

    Raises:
        ValidationError: If the slide is longer than the available depth.
    """
    # Only DrawerUnit carries a slide attribute.
    slide = getattr(unit, "slide", None)
    if slide is None:
        return

    available_depth = unit.d - unit.t
    if slide.length > available_depth:
        raise ValidationError(
            f"Slide length ({slide.length} mm) exceeds the available "
            f"cabinet depth ({available_depth} mm).  "
            f"Choose a shorter slide or increase the cabinet depth."
        )


def validate_min_drawer_height(unit: "CabinetUnit") -> None:
    """
    Verify that the cabinet is tall enough to accommodate all drawer boxes.

    Each drawer box needs at least `drawer_side_h + panel_gap_mm` of height.
    The default drawer side height is 200 mm with a 3 mm gap.

    Args:
        unit: The cabinet unit to validate (must be a DrawerUnit).

    Raises:
        ValidationError: If the unit is too short for the requested drawers.
    """
    num_drawers = getattr(unit, "num_drawers", None)
    if num_drawers is None:
        return

    # Pull values from the unit's config if available, else use safe defaults.
    from corequote_core.units.definitions import UNIT_REGISTRY
    config = UNIT_REGISTRY.get(unit.unit_type_key)
    if config is not None:
        drawer_side_h = config.variant_config.drawer_side_h  # type: ignore[union-attr]
        panel_gap_mm  = config.variant_config.panel_gap_mm   # type: ignore[union-attr]
    else:
        drawer_side_h = 200
        panel_gap_mm  = 3

    # Minimum height = (drawer box height + gap) × number of drawers + 1 gap
    min_height = (drawer_side_h + panel_gap_mm) * num_drawers + panel_gap_mm
    if unit.h < min_height:
        raise ValidationError(
            f"Unit height ({unit.h} mm) is too short for {num_drawers} drawer(s).  "
            f"Minimum required height is {min_height} mm."
        )
