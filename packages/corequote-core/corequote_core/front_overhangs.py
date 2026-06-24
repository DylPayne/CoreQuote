from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


WALL_FRONT_OVERHANG_DEFAULT = {
    "enabled": False,
    "amount_mm": 20,
    "edge": "bottom",
    "apply_to": "all",
    "front_indexes": [],
}
WALL_FRONT_OVERHANG_KEY = "wall_front_overhang"
WALL_FRONT_OVERHANG_QUOTE_DEFAULT_KEY = "_wall_front_overhang_default"

WALL_FRONT_OVERHANG_EDGES = {"bottom", "top", "left", "right"}
WALL_FRONT_OVERHANG_APPLY_TO = {"all", "selected"}
WALL_FRONT_OVERHANG_MODES = {"inherit", "none", "custom"}


@dataclass(frozen=True)
class EffectiveWallFrontOverhang:
    enabled: bool
    amount_mm: int
    edge: str
    apply_to: str
    front_indexes: tuple[int, ...]
    raw_front_indexes: tuple[int, ...]


def is_wall_door_unit_type(unit_type_key: str | None) -> bool:
    value = str(unit_type_key or "")
    return value in {"Wall Door", "Wall 1 Door", "Wall 2 Door"} or (
        "wall" in value.lower() and "door" in value.lower()
    )


def normalize_wall_front_overhang_default(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return dict(WALL_FRONT_OVERHANG_DEFAULT)

    edge = str(value.get("edge") or WALL_FRONT_OVERHANG_DEFAULT["edge"]).strip().lower()
    if edge not in WALL_FRONT_OVERHANG_EDGES:
        edge = str(WALL_FRONT_OVERHANG_DEFAULT["edge"])

    apply_to = str(value.get("apply_to") or WALL_FRONT_OVERHANG_DEFAULT["apply_to"]).strip().lower()
    if apply_to not in WALL_FRONT_OVERHANG_APPLY_TO:
        apply_to = str(WALL_FRONT_OVERHANG_DEFAULT["apply_to"])

    indexes = _positive_ints(value.get("front_indexes"))
    return {
        "enabled": bool(value.get("enabled", WALL_FRONT_OVERHANG_DEFAULT["enabled"])),
        "amount_mm": _positive_int(value.get("amount_mm"), int(WALL_FRONT_OVERHANG_DEFAULT["amount_mm"])),
        "edge": edge,
        "apply_to": apply_to,
        "front_indexes": indexes if apply_to == "selected" else [],
    }


def normalize_wall_front_overhang_override(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {"mode": "inherit"}

    mode = str(value.get("mode") or "inherit").strip().lower()
    if mode not in WALL_FRONT_OVERHANG_MODES:
        mode = "inherit"
    if mode != "custom":
        return {"mode": mode}

    default = normalize_wall_front_overhang_default({**WALL_FRONT_OVERHANG_DEFAULT, "enabled": True})
    custom = normalize_wall_front_overhang_default({**default, **dict(value), "enabled": True})
    return {
        "mode": "custom",
        "amount_mm": custom["amount_mm"],
        "edge": custom["edge"],
        "apply_to": custom["apply_to"],
        "front_indexes": custom["front_indexes"],
    }


def effective_wall_front_overhang(
    *,
    unit_type_key: str | None,
    extra_params: Mapping[str, Any] | None,
    num_fronts: int,
    quote_default: Mapping[str, Any] | None = None,
) -> EffectiveWallFrontOverhang:
    disabled = EffectiveWallFrontOverhang(
        enabled=False,
        amount_mm=0,
        edge="bottom",
        apply_to="all",
        front_indexes=(),
        raw_front_indexes=(),
    )
    if not is_wall_door_unit_type(unit_type_key):
        return disabled

    params = extra_params if isinstance(extra_params, Mapping) else {}
    inherited_default = normalize_wall_front_overhang_default(
        quote_default if quote_default is not None else params.get(WALL_FRONT_OVERHANG_QUOTE_DEFAULT_KEY)
    )
    override = normalize_wall_front_overhang_override(params.get(WALL_FRONT_OVERHANG_KEY))

    mode = str(override.get("mode") or "inherit")
    if mode == "none":
        return disabled

    setting = inherited_default if mode == "inherit" else {
        "enabled": True,
        "amount_mm": override.get("amount_mm"),
        "edge": override.get("edge"),
        "apply_to": override.get("apply_to"),
        "front_indexes": override.get("front_indexes"),
    }
    normalized = normalize_wall_front_overhang_default(setting)
    if not normalized["enabled"] or int(normalized["amount_mm"]) <= 0:
        return disabled

    raw_indexes = tuple(_positive_ints(normalized.get("front_indexes")))
    valid_indexes = tuple(index for index in raw_indexes if 1 <= index <= max(0, int(num_fronts)))
    return EffectiveWallFrontOverhang(
        enabled=True,
        amount_mm=int(normalized["amount_mm"]),
        edge=str(normalized["edge"]),
        apply_to=str(normalized["apply_to"]),
        front_indexes=valid_indexes if normalized["apply_to"] == "selected" else (),
        raw_front_indexes=raw_indexes if normalized["apply_to"] == "selected" else (),
    )


def wall_front_overhang_boards(
    *,
    name: str,
    length: int,
    width: int,
    qty: int,
    unit_type_key: str | None,
    extra_params: Mapping[str, Any] | None,
    num_fronts: int,
) -> list[Any]:
    from corequote_core.models import Board

    rows = split_wall_front_overhang_row(
        {
            "desc": name,
            "length": int(length),
            "width": int(width),
            "qty": int(qty),
        },
        unit_type_key=unit_type_key,
        extra_params=extra_params,
        num_fronts=num_fronts,
    )
    return [
        Board(
            name=str(row["desc"]),
            length=int(row["length"]),
            width=int(row["width"]),
            qty=int(row["qty"]),
        )
        for row in rows
        if int(row["qty"]) > 0
    ]


def split_wall_front_overhang_row(
    row: Mapping[str, Any],
    *,
    unit_type_key: str | None,
    extra_params: Mapping[str, Any] | None,
    num_fronts: int,
) -> list[dict[str, Any]]:
    base = dict(row)
    total_qty = _positive_int(base.get("qty"), max(0, int(num_fronts)))
    effective = effective_wall_front_overhang(
        unit_type_key=unit_type_key,
        extra_params=extra_params,
        num_fronts=max(0, int(num_fronts)),
    )
    if not effective.enabled:
        return [base]

    if effective.apply_to == "selected":
        adjusted_qty = min(total_qty, len(effective.front_indexes))
        if adjusted_qty <= 0:
            return [base]
    else:
        adjusted_qty = total_qty

    rows: list[dict[str, Any]] = []
    normal_qty = max(0, total_qty - adjusted_qty)
    if normal_qty > 0:
        rows.append({**base, "qty": normal_qty})
    if adjusted_qty > 0:
        rows.append(
            {
                **_overhang_adjusted_row(base, effective),
                "qty": adjusted_qty,
            }
        )
    return rows or [base]


def wall_front_overhang_validation_messages(
    unit: Mapping[str, Any],
    *,
    quote: Mapping[str, Any] | None = None,
) -> list[str]:
    unit_type_key = str(unit.get("unit_type_key") or unit.get("unit_type") or "")
    if not is_wall_door_unit_type(unit_type_key):
        return []

    extra_params = unit.get("extra_params") or {}
    if not isinstance(extra_params, Mapping):
        extra_params = {}

    num_fronts = _positive_int(extra_params.get("num_doors"), _default_num_doors(unit_type_key))
    effective = effective_wall_front_overhang(
        unit_type_key=unit_type_key,
        extra_params=extra_params,
        quote_default=(quote or {}).get("wall_front_overhang_default") if isinstance(quote, Mapping) else None,
        num_fronts=num_fronts,
    )
    if not effective.enabled:
        return []

    messages: list[str] = []
    if effective.apply_to == "selected":
        invalid = [index for index in effective.raw_front_indexes if index < 1 or index > num_fronts]
        if invalid:
            joined = ", ".join(str(index) for index in invalid)
            messages.append(f"Wall front overhang selected front indexes must be between 1 and {num_fronts}; invalid: {joined}.")
        if not effective.front_indexes:
            messages.append("Wall front overhang is set to selected fronts but no valid front indexes are selected.")

    if effective.edge == "top":
        messages.append("Top-edge wall front overhang needs cornice clearance checked before production.")
    if effective.edge in {"left", "right"}:
        messages.append("Side-edge wall front overhang needs adjacent-unit clearance checked before production.")
    if effective.edge == "bottom" and _quote_has_pelmet_settings(quote or {}):
        messages.append("Bottom-edge wall front overhang may clash with the quote pelmet/light-pelmet setup.")

    return messages


def wall_front_overhang_summary(value: Mapping[str, Any] | None) -> str:
    setting = normalize_wall_front_overhang_default(value)
    if not setting["enabled"]:
        return "No wall overhang"
    target = "all fronts" if setting["apply_to"] == "all" else "selected fronts"
    return f"{setting['amount_mm']} mm {setting['edge']} overhang on {target}"


def _overhang_adjusted_row(row: Mapping[str, Any], overhang: EffectiveWallFrontOverhang) -> dict[str, Any]:
    length = int(row.get("length", 0) or 0)
    width = int(row.get("width", 0) or 0)
    if overhang.edge in {"top", "bottom"}:
        length += overhang.amount_mm
    else:
        width += overhang.amount_mm
    return {
        **dict(row),
        "desc": f"{str(row.get('desc') or 'Door')} ({overhang.edge} overhang {overhang.amount_mm} mm)",
        "length": max(0, length),
        "width": max(0, width),
    }


def _quote_has_pelmet_settings(quote: Mapping[str, Any]) -> bool:
    custom_panels = quote.get("custom_panels")
    if not isinstance(custom_panels, Mapping):
        return False
    auto = custom_panels.get("auto")
    if not isinstance(auto, Mapping):
        return False
    if str(auto.get("pelmet_board_type_id") or "").strip():
        return True
    if bool(auto.get("pelmet_override_on")):
        return True
    return _positive_int(auto.get("pelmet_override_qty"), 0) > 0 or _positive_int(auto.get("pelmet_override_width"), 0) > 0


def _default_num_doors(unit_type_key: str) -> int:
    value = str(unit_type_key or "")
    if value in {"Wall 1 Door", "Wall 2 Door"}:
        return int(value.split()[1])
    return 2


def _positive_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _positive_ints(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    values: list[int] = []
    for item in value:
        parsed = _positive_int(item, 0)
        if parsed > 0 and parsed not in values:
            values.append(parsed)
    return values
