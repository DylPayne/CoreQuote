from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from corequote_core.panels import PANEL_PRESET_KEYS
from corequote_api.projects_quotes_errors import WorkspaceValidationError


QUOTE_STATUSES = ("draft", "ready", "sent", "accepted", "rejected", "revised", "expired")


def _clean_project_payload(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "name": _clean_required(payload.get("name"), field="name"),
        "client": _clean_optional(payload.get("client", "")),
        "address": _clean_optional(payload.get("address", "")),
        "description": _clean_optional(payload.get("description", "")),
    }


def _clean_quote_payload(payload: dict[str, Any]) -> dict[str, Any]:
    unit_defaults = payload.get("unit_defaults") or {}
    if not isinstance(unit_defaults, dict):
        raise WorkspaceValidationError("unit_defaults must be an object")

    cleaned_unit_defaults: dict[str, dict[str, int]] = {}
    for key, value in unit_defaults.items():
        unit_key = _clean_optional(key)
        if not unit_key:
            continue
        if not isinstance(value, dict):
            raise WorkspaceValidationError(f"unit_defaults[{unit_key}] must be an object")
        cleaned_unit_defaults[unit_key] = {
            "height": _positive_int(value.get("height"), field=f"unit_defaults[{unit_key}].height"),
            "depth": _positive_int(value.get("depth"), field=f"unit_defaults[{unit_key}].depth"),
        }

    return {
        "name": _clean_required(payload.get("name"), field="name"),
        "notes": _clean_optional(payload.get("notes", "")),
        "default_carcass_board_type_id": _optional_uuid(payload.get("default_carcass_board_type_id")),
        "default_door_board_type_id": _optional_uuid(payload.get("default_door_board_type_id")),
        "default_panel_board_type_id": _optional_uuid(payload.get("default_panel_board_type_id")),
        "default_slide_id": _optional_uuid(payload.get("default_slide_id")),
        "default_hinge_id": _optional_uuid(payload.get("default_hinge_id")),
        "default_base_handle_id": _optional_uuid(payload.get("default_base_handle_id")),
        "default_wall_handle_id": _optional_uuid(payload.get("default_wall_handle_id")),
        "default_tall_handle_id": _optional_uuid(payload.get("default_tall_handle_id")),
        "default_drawer_handle_id": _optional_uuid(payload.get("default_drawer_handle_id")),
        "unit_defaults": cleaned_unit_defaults,
    }


def _clean_quote_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status not in QUOTE_STATUSES:
        raise WorkspaceValidationError("Quote status is not supported")
    return status


def _clean_unit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    extra_params = payload.get("extra_params") or {}
    if not isinstance(extra_params, dict):
        raise WorkspaceValidationError("extra_params must be an object")

    return {
        "unit_type_key": _clean_required(payload.get("unit_type_key"), field="unit_type_key"),
        "height": _positive_int(payload.get("height"), field="height"),
        "width": _positive_int(payload.get("width"), field="width"),
        "depth": _positive_int(payload.get("depth"), field="depth"),
        "thickness": _positive_int(payload.get("thickness", 16), field="thickness"),
        "carcass_board_type_id": _optional_uuid(payload.get("carcass_board_type_id")),
        "door_board_type_id": _optional_uuid(payload.get("door_board_type_id")),
        "extra_params": extra_params,
    }


def _clean_required(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise WorkspaceValidationError(f"{field} is required")
    return text


def _clean_optional(value: Any) -> str:
    return str(value or "").strip()


def _optional_uuid(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_int(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise WorkspaceValidationError(f"{field} must be a positive integer") from exc
    if parsed <= 0:
        raise WorkspaceValidationError(f"{field} must be a positive integer")
    return parsed


def _is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _clean_quote_extras_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    for index, row in enumerate(items):
        extra_id = str(row.get("extra_id", "")).strip()
        if not extra_id:
            raise WorkspaceValidationError(f"items[{index}].extra_id is required")
        try:
            quantity = int(row.get("quantity", 1))
        except (TypeError, ValueError) as exc:
            raise WorkspaceValidationError(f"items[{index}].quantity must be a positive integer") from exc
        if quantity <= 0:
            raise WorkspaceValidationError(f"items[{index}].quantity must be a positive integer")
        totals[extra_id] += quantity
    return [{"extra_id": extra_id, "quantity": quantity} for extra_id, quantity in sorted(totals.items())]


def _default_dims_for_unit_type_from_quote(quote: dict[str, Any], unit_type: str) -> tuple[int, int]:
    defaults = quote.get("unit_defaults", {}) or {}
    item = defaults.get(unit_type, {}) if isinstance(defaults, dict) else {}

    if unit_type == "Wall Door":
        fallback_h, fallback_d = 720, 330
    elif unit_type == "Tall Door":
        fallback_h, fallback_d = 2100, 580
    else:
        fallback_h, fallback_d = 780, 580

    return int(item.get("height", fallback_h)), int(item.get("depth", fallback_d))


def _default_dims_for_panel_preset_from_quote(quote: dict[str, Any], key: str) -> tuple[int, int]:
    base_h, base_d = _default_dims_for_unit_type_from_quote(quote, "Base Door")
    wall_h, wall_d = _default_dims_for_unit_type_from_quote(quote, "Wall Door")
    tall_h, tall_d = _default_dims_for_unit_type_from_quote(quote, "Tall Door")

    if key == "base_side_panel":
        return int(base_h), int(base_d)
    if key == "base_side_filler":
        return int(base_h), 100
    if key == "wall_side_panel":
        return int(wall_h), int(wall_d)
    if key == "wall_side_filler":
        return int(wall_h), 100
    if key == "tall_side_panel":
        return int(tall_h), int(tall_d)
    if key == "tall_side_filler":
        return int(tall_h), 100
    return 0, 0


def _non_negative_int(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise WorkspaceValidationError(f"{field} must be a non-negative integer") from exc
    if parsed < 0:
        raise WorkspaceValidationError(f"{field} must be a non-negative integer")
    return parsed


def _clean_custom_panels_payload(payload: Any) -> dict[str, Any]:
    value = payload or {}
    if not isinstance(value, dict):
        raise WorkspaceValidationError("custom_panels must be an object")

    raw_presets = value.get("presets") or {}
    if not isinstance(raw_presets, dict):
        raise WorkspaceValidationError("custom_panels.presets must be an object")
    cleaned_presets: dict[str, dict[str, Any]] = {}
    for key in PANEL_PRESET_KEYS:
        raw = raw_presets.get(key) or {}
        if not isinstance(raw, dict):
            raise WorkspaceValidationError(f"custom_panels.presets.{key} must be an object")
        cleaned_presets[key] = {
            "qty": _non_negative_int(raw.get("qty", 0), field=f"custom_panels.presets.{key}.qty"),
            "board_type_id": _optional_uuid(raw.get("board_type_id")),
        }

    raw_manual = value.get("manual") or []
    if not isinstance(raw_manual, list):
        raise WorkspaceValidationError("custom_panels.manual must be an array")
    cleaned_manual: list[dict[str, Any]] = []
    for index, row in enumerate(raw_manual):
        if not isinstance(row, dict):
            raise WorkspaceValidationError(f"custom_panels.manual[{index}] must be an object")
        cleaned_row = {
            "name": str(row.get("name", "Custom Panel") or "Custom Panel").strip() or "Custom Panel",
            "length": _non_negative_int(row.get("length", 0), field=f"custom_panels.manual[{index}].length"),
            "width": _non_negative_int(row.get("width", 0), field=f"custom_panels.manual[{index}].width"),
            "qty": _non_negative_int(row.get("qty", 0), field=f"custom_panels.manual[{index}].qty"),
            "board_type_id": _optional_uuid(row.get("board_type_id")),
        }
        if cleaned_row["length"] > 0 and cleaned_row["width"] > 0 and cleaned_row["qty"] > 0:
            cleaned_manual.append(cleaned_row)

    raw_auto = value.get("auto") or {}
    if not isinstance(raw_auto, dict):
        raise WorkspaceValidationError("custom_panels.auto must be an object")
    cleaned_auto = {
        "kicker_board_type_id": _optional_uuid(raw_auto.get("kicker_board_type_id")),
        "pelmet_board_type_id": _optional_uuid(raw_auto.get("pelmet_board_type_id")),
        "kicker_return_count": _non_negative_int(raw_auto.get("kicker_return_count", 0), field="custom_panels.auto.kicker_return_count"),
        "kicker_return_depth_mm": _non_negative_int(
            raw_auto.get("kicker_return_depth_mm", 0),
            field="custom_panels.auto.kicker_return_depth_mm",
        ),
        "kicker_override_on": bool(raw_auto.get("kicker_override_on", False)),
        "kicker_override_qty": _non_negative_int(raw_auto.get("kicker_override_qty", 0), field="custom_panels.auto.kicker_override_qty"),
        "kicker_override_length": _non_negative_int(
            raw_auto.get("kicker_override_length", 0),
            field="custom_panels.auto.kicker_override_length",
        ),
        "kicker_override_width": _non_negative_int(
            raw_auto.get("kicker_override_width", 100),
            field="custom_panels.auto.kicker_override_width",
        ),
        "pelmet_override_on": bool(raw_auto.get("pelmet_override_on", False)),
        "pelmet_override_qty": _non_negative_int(raw_auto.get("pelmet_override_qty", 0), field="custom_panels.auto.pelmet_override_qty"),
        "pelmet_override_length": _non_negative_int(
            raw_auto.get("pelmet_override_length", 0),
            field="custom_panels.auto.pelmet_override_length",
        ),
        "pelmet_override_width": _non_negative_int(
            raw_auto.get("pelmet_override_width", 330),
            field="custom_panels.auto.pelmet_override_width",
        ),
    }

    return {
        "presets": cleaned_presets,
        "manual": cleaned_manual,
        "auto": cleaned_auto,
    }
