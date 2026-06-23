from __future__ import annotations

import ast
import math
import os
import re
from collections.abc import Mapping
from typing import Any

import psycopg
from psycopg.rows import dict_row

from corequote_api.cutlist_validation import preview_with_validation
from corequote_core.cutlist import build_cutlist


UNIT_CONFIG_RUNTIME_SELECT = """
    id::text,
    unit_type_key,
    variant_config
"""

RULESET_RUNTIME_SELECT = """
    id::text,
    unit_config_id::text,
    unit_type_key
"""

RULE_ROW_RUNTIME_SELECT = """
    id::text,
    sort_order,
    section,
    description,
    length_formula,
    width_formula,
    qty_formula,
    condition_formula,
    grain_direction,
    can_rotate,
    edge_long_1,
    edge_long_2,
    edge_short_1,
    edge_short_2
"""

FORMULA_ALLOWED_CHARACTERS = re.compile(r"^[0-9A-Za-z_+\-*/().<>=!&|,%\s]*$")
SIMPLIFIED_UNIT_TYPE_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Base Draw": ("Base Draw", "Base Drawer", "Base 1 Draw", "Base 2 Draw", "Base 3 Draw", "Base 4 Draw"),
    "Base Door": ("Base Door", "Base 1 Door", "Base 2 Door"),
    "Wall Door": ("Wall Door", "Wall 1 Door", "Wall 2 Door"),
    "Tall Door": ("Tall Door", "Tall Standard", "Tall Pantry"),
}
UNIT_TYPE_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in SIMPLIFIED_UNIT_TYPE_CANDIDATES.items()
    for alias in aliases
}
CANONICAL_TO_LEGACY_FALLBACK: dict[str, str] = {
    "Base Draw": "Base Drawer",
    "Base Door": "Base Door",
    "Wall Door": "Wall Door",
    "Tall Door": "Tall Standard",
}
METAL_DRAWER_SUPPRESSED_PARTS = {"Drawer Side", "Drawer Front/Back", "Drawer Base"}
DRAWER_SYSTEM_NUMERIC_CONFIG_FIELDS = (
    "side_height_mm",
    "installation_width_mm",
    "min_internal_width_mm",
    "max_internal_width_mm",
    "min_depth_mm",
    "min_front_height_mm",
    "max_front_height_mm",
)


class CuttingRuntimeError(ValueError):
    pass


class CuttingFormulaEvaluator:
    _MAX_EXPRESSION_LENGTH = 500
    _FUNCTIONS = {
        "abs": abs,
        "ceil": math.ceil,
        "floor": math.floor,
        "max": max,
        "min": min,
        "round": round,
    }
    _SAFE_AST_NODE_TYPES = (
        ast.Add,
        ast.And,
        ast.BinOp,
        ast.BoolOp,
        ast.Call,
        ast.Compare,
        ast.Constant,
        ast.Div,
        ast.Eq,
        ast.Expression,
        ast.Gt,
        ast.GtE,
        ast.IfExp,
        ast.Load,
        ast.Lt,
        ast.LtE,
        ast.Mod,
        ast.Mult,
        ast.Name,
        ast.Not,
        ast.NotEq,
        ast.Or,
        ast.Sub,
        ast.UnaryOp,
        ast.USub,
        ast.UAdd,
    )
    _COMPARISON_OPERATORS = {
        ast.Eq: lambda left, right: left == right,
        ast.NotEq: lambda left, right: left != right,
        ast.Gt: lambda left, right: left > right,
        ast.GtE: lambda left, right: left >= right,
        ast.Lt: lambda left, right: left < right,
        ast.LtE: lambda left, right: left <= right,
    }
    _BINARY_OPERATORS = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
        ast.Mod: lambda left, right: left % right,
    }

    def evaluate_numeric(self, expression: str, context: Mapping[str, float | int | bool], *, field_name: str) -> float:
        trimmed = expression.strip()
        if not trimmed:
            raise CuttingRuntimeError(f"{field_name} is required.")

        parsed = self._parse(trimmed, context_keys=context.keys(), field_name=field_name)
        value = self._evaluate_node(parsed.body, context)
        numeric = self._as_number(value, field_name=field_name)
        if not math.isfinite(numeric):
            raise CuttingRuntimeError(f"{field_name} must evaluate to a finite number.")
        return numeric

    def evaluate_condition(self, expression: str, context: Mapping[str, float | int | bool]) -> bool:
        trimmed = expression.strip()
        if not trimmed:
            return True

        parsed = self._parse(trimmed, context_keys=context.keys(), field_name="condition_formula")
        value = self._evaluate_node(parsed.body, context)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        raise CuttingRuntimeError("condition_formula must evaluate to a boolean-compatible value.")

    def _parse(self, expression: str, *, context_keys: Any, field_name: str) -> ast.Expression:
        if len(expression) > self._MAX_EXPRESSION_LENGTH:
            raise CuttingRuntimeError(f"{field_name} exceeds the maximum length of {self._MAX_EXPRESSION_LENGTH} characters.")
        if not FORMULA_ALLOWED_CHARACTERS.fullmatch(expression):
            raise CuttingRuntimeError(f"{field_name} contains unsupported characters.")
        if not _has_balanced_parentheses(expression):
            raise CuttingRuntimeError(f"{field_name} has unbalanced parentheses.")

        try:
            parsed = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise CuttingRuntimeError(f"{field_name} has invalid syntax.") from exc

        for node in ast.walk(parsed):
            if not isinstance(node, self._SAFE_AST_NODE_TYPES):
                raise CuttingRuntimeError(f"{field_name} contains unsupported syntax.")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in self._FUNCTIONS:
                    raise CuttingRuntimeError(f"{field_name} uses an unsupported function.")
            if isinstance(node, ast.Name):
                if node.id in self._FUNCTIONS:
                    continue
                lowered = node.id.lower()
                if lowered in ("true", "false"):
                    continue
                if node.id not in context_keys:
                    raise CuttingRuntimeError(f"Unknown identifier in {field_name}: {node.id}")

        return parsed

    def _evaluate_node(self, node: ast.AST, context: Mapping[str, float | int | bool]) -> float | int | bool:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                return node.value
            raise CuttingRuntimeError("Formula constants must be numbers or booleans.")

        if isinstance(node, ast.Name):
            lowered = node.id.lower()
            if lowered == "true":
                return True
            if lowered == "false":
                return False
            if node.id not in context:
                raise CuttingRuntimeError(f"Unknown identifier: {node.id}")
            return context[node.id]

        if isinstance(node, ast.UnaryOp):
            value = self._evaluate_node(node.operand, context)
            if isinstance(node.op, ast.Not):
                return not bool(value)
            numeric = self._as_number(value, field_name="expression")
            if isinstance(node.op, ast.UAdd):
                return numeric
            if isinstance(node.op, ast.USub):
                return -numeric
            raise CuttingRuntimeError("Unsupported unary operator in formula.")

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for item in node.values:
                    if not bool(self._evaluate_node(item, context)):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for item in node.values:
                    if bool(self._evaluate_node(item, context)):
                        return True
                return False
            raise CuttingRuntimeError("Unsupported logical operator in formula.")

        if isinstance(node, ast.BinOp):
            operator = self._BINARY_OPERATORS.get(type(node.op))
            if not operator:
                raise CuttingRuntimeError("Unsupported arithmetic operator in formula.")
            left = self._as_number(self._evaluate_node(node.left, context), field_name="expression")
            right = self._as_number(self._evaluate_node(node.right, context), field_name="expression")
            try:
                return operator(left, right)
            except ZeroDivisionError as exc:
                raise CuttingRuntimeError("Division by zero in formula.") from exc

        if isinstance(node, ast.Compare):
            left_value = self._evaluate_node(node.left, context)
            for operator_node, comparator in zip(node.ops, node.comparators):
                operator = self._COMPARISON_OPERATORS.get(type(operator_node))
                if not operator:
                    raise CuttingRuntimeError("Unsupported comparison operator in formula.")
                right_value = self._evaluate_node(comparator, context)
                if not operator(left_value, right_value):
                    return False
                left_value = right_value
            return True

        if isinstance(node, ast.IfExp):
            condition = bool(self._evaluate_node(node.test, context))
            return self._evaluate_node(node.body if condition else node.orelse, context)

        if isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else ""
            function = self._FUNCTIONS.get(func_name)
            if function is None:
                raise CuttingRuntimeError("Unsupported function in formula.")
            args = [self._as_number(self._evaluate_node(arg, context), field_name="expression") for arg in node.args]
            return function(*args)

        raise CuttingRuntimeError("Formula contains an unsupported expression.")

    @staticmethod
    def _as_number(value: Any, *, field_name: str) -> float:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        raise CuttingRuntimeError(f"{field_name} must evaluate to a number.")


class CuttingRuntimeStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def resolve_unit_config(self, company_id: str, unit_type_key: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {UNIT_CONFIG_RUNTIME_SELECT}
                FROM unit_configs
                WHERE status = 'active'
                  AND unit_type_key = %s
                  AND (
                    company_id = %s
                    OR (company_id IS NULL AND is_default = true)
                  )
                ORDER BY
                  CASE WHEN company_id = %s THEN 0 ELSE 1 END,
                  version DESC,
                  updated_at DESC
                LIMIT 1
                """,
                (unit_type_key, company_id, company_id),
            ).fetchone()

    def resolve_ruleset(self, company_id: str, unit_type_key: str) -> dict | None:
        with self._connect() as conn:
            ruleset = conn.execute(
                f"""
                SELECT {RULESET_RUNTIME_SELECT}
                FROM cutting_rulesets
                WHERE status = 'active'
                  AND unit_type_key = %s
                  AND (
                    company_id = %s
                    OR (company_id IS NULL AND is_default = true)
                  )
                ORDER BY
                  CASE WHEN company_id = %s THEN 0 ELSE 1 END,
                  is_default DESC,
                  version DESC,
                  updated_at DESC
                LIMIT 1
                """,
                (unit_type_key, company_id, company_id),
            ).fetchone()

            if not ruleset:
                return None

            rows = conn.execute(
                f"""
                SELECT {RULE_ROW_RUNTIME_SELECT}
                FROM cutting_rule_rows
                WHERE ruleset_id = %s
                ORDER BY sort_order ASC, id ASC
                """,
                (ruleset["id"],),
            ).fetchall()
            return {**ruleset, "rows": rows}

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for runtime cutting database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)


class CutlistRuntimeService:
    def __init__(
        self,
        *,
        evaluator: CuttingFormulaEvaluator | None = None,
        store: CuttingRuntimeStore | Any = None,
    ):
        self.evaluator = evaluator or CuttingFormulaEvaluator()
        self.store = store or CuttingRuntimeStore()

    def build_preview(self, *, company_id: str, units: list[dict], use_db_rulesets: bool) -> dict:
        carcass_rows: list[dict] = []
        panel_rows: list[dict] = []
        hardware_rows: list[dict] = []
        extra_rows: list[dict] = []
        runtime_rows: list[dict] = []
        unit_sources: list[dict] = []
        resolution_cache: dict[str, tuple[dict | None, dict | None]] = {}

        for unit in units:
            unit_number = int(unit["unit_number"])
            unit_type_key = canonical_unit_type_key(str(unit["unit_type"]))

            if _is_metal_drawer_system_unit(unit, unit_type_key):
                self._append_metal_drawer_system_rows(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    carcass_rows=carcass_rows,
                    panel_rows=panel_rows,
                    hardware_rows=hardware_rows,
                    extra_rows=extra_rows,
                    runtime_rows=runtime_rows,
                    unit_sources=unit_sources,
                )
                continue

            if not use_db_rulesets:
                self._append_legacy_unit_rows(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    carcass_rows=carcass_rows,
                    panel_rows=panel_rows,
                    runtime_rows=runtime_rows,
                    unit_sources=unit_sources,
                )
                continue

            resolved = resolution_cache.get(unit_type_key)
            if not resolved:
                unit_config = self._resolve_unit_config(company_id, unit_type_key)
                ruleset = self._resolve_ruleset(company_id, unit_type_key)
                resolved = (unit_config, ruleset)
                resolution_cache[unit_type_key] = resolved
            unit_config, ruleset = resolved

            if not ruleset:
                self._append_legacy_unit_rows(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    carcass_rows=carcass_rows,
                    panel_rows=panel_rows,
                    runtime_rows=runtime_rows,
                    unit_sources=unit_sources,
                    note="No active ruleset found; used legacy strategy output.",
                    unit_config_id=unit_config["id"] if unit_config else None,
                )
                continue

            if _has_split_drawer_faces(unit, unit_type_key):
                self._append_legacy_unit_rows(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    carcass_rows=carcass_rows,
                    panel_rows=panel_rows,
                    runtime_rows=runtime_rows,
                    unit_sources=unit_sources,
                    note="Split drawer fronts use legacy strategy output.",
                    unit_config_id=ruleset.get("unit_config_id") or (unit_config["id"] if unit_config else None),
                    ruleset_id=ruleset.get("id"),
                )
                continue

            try:
                context = self._build_formula_context(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    unit_config=unit_config,
                )
                generated_rows = self._evaluate_ruleset_rows(
                    unit_number=unit_number,
                    rows=ruleset.get("rows", []),
                    context=context,
                )
            except CuttingRuntimeError as exc:
                self._append_legacy_unit_rows(
                    unit=unit,
                    unit_type_key=unit_type_key,
                    carcass_rows=carcass_rows,
                    panel_rows=panel_rows,
                    runtime_rows=runtime_rows,
                    unit_sources=unit_sources,
                    note=f"Ruleset runtime evaluation failed: {exc}",
                    unit_config_id=ruleset.get("unit_config_id") or (unit_config["id"] if unit_config else None),
                    ruleset_id=ruleset.get("id"),
                )
                continue

            for row in generated_rows:
                runtime_rows.append(row)
                compact = {
                    "unit_number": row["unit_number"],
                    "desc": row["desc"],
                    "length": row["length"],
                    "width": row["width"],
                    "qty": row["qty"],
                }
                if row["section"] == "carcass":
                    carcass_rows.append(compact)
                elif row["section"] == "panel":
                    panel_rows.append(compact)
                elif row["section"] == "hardware":
                    hardware_rows.append(compact)
                elif row["section"] == "extra_panel":
                    extra_rows.append(compact)

            unit_sources.append(
                {
                    "unit_number": unit_number,
                    "unit_type_key": unit_type_key,
                    "source": "ruleset",
                    "ruleset_id": ruleset.get("id"),
                    "unit_config_id": ruleset.get("unit_config_id") or (unit_config["id"] if unit_config else None),
                    "note": None,
                }
            )

        runtime_mode = _runtime_mode(unit_sources)

        preview = {
            "carcass": carcass_rows,
            "panels": panel_rows,
            "hardware": hardware_rows,
            "extras": extra_rows,
            "runtime_rows": runtime_rows,
            "runtime_mode": runtime_mode,
            "unit_sources": unit_sources,
        }
        return preview_with_validation(preview)

    def _append_metal_drawer_system_rows(
        self,
        *,
        unit: dict,
        unit_type_key: str,
        carcass_rows: list[dict],
        panel_rows: list[dict],
        hardware_rows: list[dict],
        extra_rows: list[dict],
        runtime_rows: list[dict],
        unit_sources: list[dict],
    ) -> None:
        legacy_unit = {**unit, "unit_type": to_legacy_unit_type(str(unit.get("unit_type", unit_type_key)))}
        legacy_carcass, legacy_panels = build_cutlist([legacy_unit])
        unit_number = int(unit["unit_number"])

        for record in legacy_carcass.to_dict(orient="records"):
            desc = str(record["Desc"])
            if desc in METAL_DRAWER_SUPPRESSED_PARTS:
                continue
            self._append_runtime_row(
                {
                    "unit_number": int(record["Unit #"]),
                    "section": "carcass",
                    "desc": desc,
                    "length": int(record["L"]),
                    "width": int(record["W"]),
                    "qty": int(record["Qty"]),
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "none",
                    "can_rotate": True,
                },
                carcass_rows=carcass_rows,
                panel_rows=panel_rows,
                hardware_rows=hardware_rows,
                extra_rows=extra_rows,
                runtime_rows=runtime_rows,
            )

        for record in legacy_panels.to_dict(orient="records"):
            self._append_runtime_row(
                {
                    "unit_number": int(record["Unit #"]),
                    "section": "panel",
                    "desc": str(record["Desc"]),
                    "length": int(record["L"]),
                    "width": int(record["W"]),
                    "qty": int(record["Qty"]),
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "none",
                    "can_rotate": True,
                },
                carcass_rows=carcass_rows,
                panel_rows=panel_rows,
                hardware_rows=hardware_rows,
                extra_rows=extra_rows,
                runtime_rows=runtime_rows,
            )

        config = _drawer_system_config(unit)
        try:
            context = self._build_formula_context(unit=unit, unit_type_key=unit_type_key, unit_config=None)
            context.update(_drawer_system_numeric_context(config))
            generated_rows = self._evaluate_drawer_system_rows(
                unit_number=unit_number,
                rows=list(config.get("panel_formulas") or []),
                context=context,
            )
        except CuttingRuntimeError as exc:
            generated_rows = [
                {
                    "unit_number": unit_number,
                    "section": "carcass",
                    "desc": "Metal drawer system configuration error",
                    "length": 0,
                    "width": 0,
                    "qty": 0,
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "none",
                    "can_rotate": True,
                    "configuration_error": str(exc),
                }
            ]

        for row in generated_rows:
            self._append_runtime_row(
                row,
                carcass_rows=carcass_rows,
                panel_rows=panel_rows,
                hardware_rows=hardware_rows,
                extra_rows=extra_rows,
                runtime_rows=runtime_rows,
            )

        unit_sources.append(
            {
                "unit_number": unit_number,
                "unit_type_key": unit_type_key,
                "source": "drawer_system",
                "ruleset_id": None,
                "unit_config_id": None,
                "note": "Configured metal drawer system output.",
            }
        )

    def _resolve_unit_config(self, company_id: str, unit_type_key: str) -> dict | None:
        for candidate in unit_type_candidates(unit_type_key):
            row = self.store.resolve_unit_config(company_id, candidate)
            if row:
                return row
        return None

    def _resolve_ruleset(self, company_id: str, unit_type_key: str) -> dict | None:
        for candidate in unit_type_candidates(unit_type_key):
            row = self.store.resolve_ruleset(company_id, candidate)
            if row:
                return row
        return None

    def _append_legacy_unit_rows(
        self,
        *,
        unit: dict,
        unit_type_key: str,
        carcass_rows: list[dict],
        panel_rows: list[dict],
        runtime_rows: list[dict],
        unit_sources: list[dict],
        note: str | None = None,
        ruleset_id: str | None = None,
        unit_config_id: str | None = None,
    ) -> None:
        legacy_unit = {**unit, "unit_type": to_legacy_unit_type(str(unit.get("unit_type", unit_type_key)))}
        legacy_carcass, legacy_panels = build_cutlist([legacy_unit])
        unit_number = int(unit["unit_number"])

        for record in legacy_carcass.to_dict(orient="records"):
            compact_row = {
                "unit_number": int(record["Unit #"]),
                "desc": str(record["Desc"]),
                "length": int(record["L"]),
                "width": int(record["W"]),
                "qty": int(record["Qty"]),
            }
            carcass_rows.append(compact_row)
            runtime_rows.append(
                {
                    **compact_row,
                    "section": "carcass",
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "none",
                    "can_rotate": True,
                }
            )

        for record in legacy_panels.to_dict(orient="records"):
            compact_row = {
                "unit_number": int(record["Unit #"]),
                "desc": str(record["Desc"]),
                "length": int(record["L"]),
                "width": int(record["W"]),
                "qty": int(record["Qty"]),
            }
            panel_rows.append(compact_row)
            runtime_rows.append(
                {
                    **compact_row,
                    "section": "panel",
                    "edge_long_1": False,
                    "edge_long_2": False,
                    "edge_short_1": False,
                    "edge_short_2": False,
                    "grain_direction": "none",
                    "can_rotate": True,
                }
            )

        unit_sources.append(
            {
                "unit_number": unit_number,
                "unit_type_key": unit_type_key,
                "source": "legacy",
                "ruleset_id": ruleset_id,
                "unit_config_id": unit_config_id,
                "note": note,
            }
        )

    def _append_runtime_row(
        self,
        row: dict,
        *,
        carcass_rows: list[dict],
        panel_rows: list[dict],
        hardware_rows: list[dict],
        extra_rows: list[dict],
        runtime_rows: list[dict],
    ) -> None:
        runtime_rows.append(row)
        compact = {
            "unit_number": row["unit_number"],
            "desc": row["desc"],
            "length": row["length"],
            "width": row["width"],
            "qty": row["qty"],
        }
        if row["section"] == "carcass":
            carcass_rows.append(compact)
        elif row["section"] == "panel":
            panel_rows.append(compact)
        elif row["section"] == "hardware":
            hardware_rows.append(compact)
        elif row["section"] == "extra_panel":
            extra_rows.append(compact)

    def _build_formula_context(
        self,
        *,
        unit: dict,
        unit_type_key: str,
        unit_config: dict | None,
    ) -> dict[str, float | int | bool]:
        height = int(unit["height"])
        width = int(unit["width"])
        depth = int(unit["depth"])
        thickness = int(unit.get("thickness", 16) or 16)
        extra_params = unit.get("extra_params", {}) or {}
        variant_config = (unit_config or {}).get("variant_config", {}) or {}

        context: dict[str, float | int | bool] = {
            "h": height,
            "w": width,
            "d": depth,
            "t": thickness,
        }
        context.update(_numeric_context_entries(variant_config))
        context.update(_numeric_context_entries(extra_params))

        default_num_doors = _default_num_doors(unit_type_key)
        default_num_drawers = _default_num_drawers(unit_type_key)
        default_num_shelves = _default_num_shelves(unit_type_key)

        context["panel_gap_mm"] = int(_number_or_default(context.get("panel_gap_mm"), 3))
        context["shelf_setback"] = int(_number_or_default(context.get("shelf_setback"), 20))
        context["num_doors"] = int(_number_or_default(context.get("num_doors"), default_num_doors))
        context["num_drawers"] = int(_number_or_default(context.get("num_drawers"), default_num_drawers))
        context["num_shelves"] = int(
            _number_or_default(
                context.get("num_shelves"),
                _number_or_default(context.get("default_shelves"), default_num_shelves),
            )
        )

        drawer_depth = int(
            _number_or_default(
                context.get("drawer_depth"),
                _number_or_default(extra_params.get("slide_side_length"), max(0, depth - thickness)),
            )
        )
        drawer_clearance = int(_number_or_default(extra_params.get("slide_side_clearance_total"), 0))
        configured_width_deduction = int(_number_or_default(extra_params.get("slide_box_width_deduction_mm"), 0))
        drawer_width_deduction = configured_width_deduction if configured_width_deduction > 0 else 2 * drawer_clearance
        drawer_width = max(0, int(width - (2 * thickness) - drawer_width_deduction))
        num_drawers = int(context["num_drawers"])
        panel_gap_mm = int(context["panel_gap_mm"])
        drawer_front_height = int((height / num_drawers) - panel_gap_mm) if num_drawers > 0 else 0
        drawer_front_back_height = max(0, drawer_front_height - 100)
        side_height_uplift = int(_number_or_default(extra_params.get("slide_side_height_uplift"), 0))
        drawer_side_height = max(0, drawer_front_back_height + side_height_uplift)

        context["drawer_depth"] = drawer_depth
        context["drawer_width"] = drawer_width
        context["drawer_front_height"] = drawer_front_height
        context["drawer_front_back_height"] = drawer_front_back_height
        context["drawer_side_height"] = drawer_side_height
        context["slide_mount_type"] = str(extra_params.get("slide_mount_type") or "")
        context["slide_product_family"] = str(extra_params.get("slide_product_family") or "")
        context["slide_required_depth_mm"] = int(_number_or_default(extra_params.get("slide_required_depth_mm"), 0))
        context["slide_box_width_deduction_mm"] = drawer_width_deduction
        context["inner_w"] = max(0, width - (2 * thickness))
        context["inner_h"] = max(0, height - (2 * thickness))
        return context

    def _evaluate_ruleset_rows(
        self,
        *,
        unit_number: int,
        rows: list[dict[str, Any]],
        context: Mapping[str, float | int | bool],
    ) -> list[dict]:
        generated_rows: list[dict] = []
        for row in rows:
            condition_expression = str(row.get("condition_formula", "") or "")
            if not self.evaluator.evaluate_condition(condition_expression, context):
                continue

            length = self.evaluator.evaluate_numeric(
                str(row.get("length_formula", "")),
                context,
                field_name="length_formula",
            )
            width = self.evaluator.evaluate_numeric(
                str(row.get("width_formula", "")),
                context,
                field_name="width_formula",
            )
            qty_raw = self.evaluator.evaluate_numeric(
                str(row.get("qty_formula", "")),
                context,
                field_name="qty_formula",
            )
            qty = int(qty_raw)
            length_mm = int(length)
            width_mm = int(width)
            generated_rows.append(
                {
                    "unit_number": unit_number,
                    "section": str(row.get("section", "carcass")),
                    "desc": str(row.get("description", "")).strip() or "Unnamed",
                    "length": length_mm,
                    "width": width_mm,
                    "qty": qty,
                    "edge_long_1": bool(row.get("edge_long_1", False)),
                    "edge_long_2": bool(row.get("edge_long_2", False)),
                    "edge_short_1": bool(row.get("edge_short_1", False)),
                    "edge_short_2": bool(row.get("edge_short_2", False)),
                    "grain_direction": str(row.get("grain_direction") or "none"),
                    "can_rotate": bool(row.get("can_rotate", True)),
                }
            )
        return generated_rows

    def _evaluate_drawer_system_rows(
        self,
        *,
        unit_number: int,
        rows: list[dict[str, Any]],
        context: Mapping[str, float | int | bool],
    ) -> list[dict]:
        generated_rows: list[dict] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            condition_expression = str(row.get("condition_formula", "") or "")
            if not self.evaluator.evaluate_condition(condition_expression, context):
                continue

            length = self.evaluator.evaluate_numeric(
                str(row.get("length_formula", "")),
                context,
                field_name="length_formula",
            )
            width = self.evaluator.evaluate_numeric(
                str(row.get("width_formula", "")),
                context,
                field_name="width_formula",
            )
            qty_raw = self.evaluator.evaluate_numeric(
                str(row.get("qty_formula", "num_drawers") or "num_drawers"),
                context,
                field_name="qty_formula",
            )
            section = str(row.get("section") or "carcass")
            if section not in {"carcass", "panel", "extra_panel"}:
                section = "carcass"
            generated_rows.append(
                {
                    "unit_number": unit_number,
                    "section": section,
                    "desc": str(row.get("name") or row.get("description") or "Metal drawer part").strip(),
                    "length": int(length),
                    "width": int(width),
                    "qty": int(qty_raw),
                    "edge_long_1": bool(row.get("edge_long_1", False)),
                    "edge_long_2": bool(row.get("edge_long_2", False)),
                    "edge_short_1": bool(row.get("edge_short_1", False)),
                    "edge_short_2": bool(row.get("edge_short_2", False)),
                    "grain_direction": str(row.get("grain_direction") or "none"),
                    "can_rotate": bool(row.get("can_rotate", True)),
                }
            )
        return generated_rows


def canonical_unit_type_key(unit_type: str) -> str:
    return UNIT_TYPE_ALIAS_TO_CANONICAL.get(unit_type, unit_type)


def unit_type_candidates(unit_type: str) -> tuple[str, ...]:
    canonical = canonical_unit_type_key(unit_type)
    candidates = SIMPLIFIED_UNIT_TYPE_CANDIDATES.get(canonical, (canonical,))
    # Preserve backward compatibility when legacy keys are passed directly.
    if unit_type not in candidates:
        return (canonical, unit_type, *tuple(key for key in candidates if key != canonical and key != unit_type))
    return candidates


def to_legacy_unit_type(unit_type: str) -> str:
    canonical = canonical_unit_type_key(unit_type)
    return CANONICAL_TO_LEGACY_FALLBACK.get(canonical, unit_type)


def _runtime_mode(unit_sources: list[dict]) -> str:
    if not unit_sources:
        return "legacy"
    sources = {str(row.get("source")) for row in unit_sources}
    if sources == {"ruleset"}:
        return "ruleset"
    if sources == {"legacy"}:
        return "legacy"
    if sources == {"drawer_system"}:
        return "drawer_system"
    return "mixed"


def _is_metal_drawer_system_unit(unit: Mapping[str, Any], unit_type_key: str) -> bool:
    if canonical_unit_type_key(unit_type_key) != "Base Draw":
        return False
    extra_params = unit.get("extra_params", {}) or {}
    if not isinstance(extra_params, Mapping):
        return False
    return str(extra_params.get("drawer_system_kind") or "conventional").strip().lower() == "metal"


def _drawer_system_config(unit: Mapping[str, Any]) -> dict[str, Any]:
    extra_params = unit.get("extra_params", {}) or {}
    if not isinstance(extra_params, Mapping):
        return {}
    config = extra_params.get("drawer_system_config") or {}
    return dict(config) if isinstance(config, Mapping) else {}


def _drawer_system_numeric_context(config: Mapping[str, Any]) -> dict[str, int | float | bool]:
    context = _numeric_context_entries(config.get("variables") or {})
    for field in DRAWER_SYSTEM_NUMERIC_CONFIG_FIELDS:
        value = config.get(field)
        if value is None:
            continue
        numeric = _number_or_default(value, 0)
        context[field] = numeric
        if field.endswith("_mm"):
            context[field[:-3]] = numeric
    return context


def _default_num_doors(unit_type_key: str) -> int:
    canonical = canonical_unit_type_key(unit_type_key)
    if canonical in {"Base Door", "Wall Door", "Tall Door"}:
        return 2
    return 0


def _default_num_drawers(unit_type_key: str) -> int:
    canonical = canonical_unit_type_key(unit_type_key)
    if canonical == "Base Draw":
        return 3
    return 0


def _default_num_shelves(unit_type_key: str) -> int:
    canonical = canonical_unit_type_key(unit_type_key)
    if canonical == "Tall Door":
        return 4
    if canonical in {"Base Door", "Wall Door"}:
        return 1
    return 0


def _has_split_drawer_faces(unit: Mapping[str, Any], unit_type_key: str) -> bool:
    if canonical_unit_type_key(unit_type_key) != "Base Draw":
        return False
    extra_params = unit.get("extra_params", {}) or {}
    if not isinstance(extra_params, Mapping):
        return False
    return isinstance(extra_params.get("drawer_face_heights"), list) or isinstance(extra_params.get("drawer_face_ratios"), list)


def _number_or_default(value: Any, fallback: int | float) -> int | float:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return fallback
    return parsed


def _numeric_context_entries(data: Mapping[str, Any]) -> dict[str, int | float | bool]:
    entries: dict[str, int | float | bool] = {}
    for key, value in data.items():
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(key)):
            continue
        if isinstance(value, bool):
            entries[str(key)] = value
            continue
        if isinstance(value, (int, float)):
            entries[str(key)] = value
            continue
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered == "true":
                entries[str(key)] = True
                continue
            if lowered == "false":
                entries[str(key)] = False
                continue
            try:
                parsed = float(value)
            except ValueError:
                continue
            entries[str(key)] = parsed
    return entries


def _has_balanced_parentheses(expression: str) -> bool:
    depth = 0
    for char in expression:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
