from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class CuttingConfigError(Exception):
    pass


class CuttingConfigNotFound(CuttingConfigError):
    pass


class CuttingConfigConflict(CuttingConfigError):
    pass


UNIT_CONFIG_SELECT = """
    id::text,
    company_id::text,
    unit_type_key,
    label,
    category,
    variant_type,
    version,
    status,
    is_default,
    variant_config,
    default_height,
    default_width,
    default_depth,
    height_min,
    height_max,
    width_min,
    width_max,
    depth_min,
    depth_max,
    created_at,
    updated_at
"""

RULESET_SELECT = """
    id::text,
    company_id::text,
    unit_config_id::text,
    unit_type_key,
    name,
    description,
    status,
    version,
    is_default,
    created_at,
    updated_at
"""

RULE_ROW_SELECT = """
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
    edge_short_2,
    meta,
    created_at,
    updated_at
"""


class CuttingConfigStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def list_unit_configs(self, company_id: str, include_archived: bool = False) -> list[dict]:
        status_filter = "" if include_archived else "AND status != 'archived'"
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {UNIT_CONFIG_SELECT}
                FROM unit_configs
                WHERE (company_id IS NULL OR company_id = %s)
                  {status_filter}
                ORDER BY category ASC, label ASC, company_id IS NOT NULL ASC, version DESC
                """,
                (company_id,),
            ).fetchall()

    def get_unit_config(self, company_id: str, unit_config_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {UNIT_CONFIG_SELECT}
                FROM unit_configs
                WHERE id = %s
                  AND (company_id IS NULL OR company_id = %s)
                """,
                (unit_config_id, company_id),
            ).fetchone()
        if not row:
            raise CuttingConfigNotFound("Unit config not found")
        return row

    def create_unit_config(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO unit_configs
                        (company_id, unit_type_key, label, category, variant_type, version, status, is_default,
                         variant_config, default_height, default_width, default_depth,
                         height_min, height_max, width_min, width_max, depth_min, depth_max)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        data["unit_type_key"],
                        data["label"],
                        data.get("category", "custom"),
                        data.get("variant_type", "custom"),
                        data.get("version", 1),
                        data.get("status", "active"),
                        data.get("is_default", False),
                        Jsonb(data.get("variant_config", {}) or {}),
                        data["default_height"],
                        data["default_width"],
                        data["default_depth"],
                        data["height_min"],
                        data["height_max"],
                        data["width_min"],
                        data["width_max"],
                        data["depth_min"],
                        data["depth_max"],
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise CuttingConfigConflict("Unit config already exists") from exc
        return self.get_unit_config(company_id, row["id"])

    def update_unit_config(self, company_id: str, unit_config_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    UPDATE unit_configs
                    SET unit_type_key = %s,
                        label = %s,
                        category = %s,
                        variant_type = %s,
                        version = %s,
                        status = %s,
                        is_default = %s,
                        variant_config = %s,
                        default_height = %s,
                        default_width = %s,
                        default_depth = %s,
                        height_min = %s,
                        height_max = %s,
                        width_min = %s,
                        width_max = %s,
                        depth_min = %s,
                        depth_max = %s
                    WHERE id = %s
                      AND company_id = %s
                    RETURNING id::text
                    """,
                    (
                        data["unit_type_key"],
                        data["label"],
                        data.get("category", "custom"),
                        data.get("variant_type", "custom"),
                        data.get("version", 1),
                        data.get("status", "active"),
                        data.get("is_default", False),
                        Jsonb(data.get("variant_config", {}) or {}),
                        data["default_height"],
                        data["default_width"],
                        data["default_depth"],
                        data["height_min"],
                        data["height_max"],
                        data["width_min"],
                        data["width_max"],
                        data["depth_min"],
                        data["depth_max"],
                        unit_config_id,
                        company_id,
                    ),
                ).fetchone()
                if not row:
                    raise CuttingConfigNotFound("Unit config not found")
        except psycopg.errors.UniqueViolation as exc:
            raise CuttingConfigConflict("Unit config already exists") from exc
        return self.get_unit_config(company_id, unit_config_id)

    def list_rulesets(
        self,
        company_id: str,
        unit_type_key: str | None = None,
        include_archived: bool = False,
    ) -> list[dict]:
        filters = ["(company_id IS NULL OR company_id = %s)"]
        params: list[Any] = [company_id]
        if unit_type_key:
            filters.append("unit_type_key = %s")
            params.append(unit_type_key)
        if not include_archived:
            filters.append("status != 'archived'")

        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {RULESET_SELECT}
                FROM cutting_rulesets
                WHERE {" AND ".join(filters)}
                ORDER BY unit_type_key ASC, company_id IS NOT NULL ASC, version DESC, name ASC
                """,
                params,
            ).fetchall()

    def get_ruleset(self, company_id: str, ruleset_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {RULESET_SELECT}
                FROM cutting_rulesets
                WHERE id = %s
                  AND (company_id IS NULL OR company_id = %s)
                """,
                (ruleset_id, company_id),
            ).fetchone()
            if not row:
                raise CuttingConfigNotFound("Cutting ruleset not found")
            return self._with_rows(conn, row)

    def create_ruleset(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            with self._connect() as conn:
                with conn.transaction():
                    self._ensure_unit_config_visible(conn, company_id, data.get("unit_config_id"))
                    row = conn.execute(
                        """
                        INSERT INTO cutting_rulesets
                            (company_id, unit_config_id, unit_type_key, name, description, status, version, is_default)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id::text
                        """,
                        (
                            company_id,
                            data.get("unit_config_id"),
                            data["unit_type_key"],
                            data["name"],
                            data.get("description", ""),
                            data.get("status", "draft"),
                            data.get("version", 1),
                            data.get("is_default", False),
                        ),
                    ).fetchone()
                    self._replace_rows(conn, row["id"], data.get("rows", []))
        except psycopg.errors.UniqueViolation as exc:
            raise CuttingConfigConflict("Cutting ruleset already exists") from exc
        return self.get_ruleset(company_id, row["id"])

    def update_ruleset(self, company_id: str, ruleset_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_payload(payload)
        try:
            with self._connect() as conn:
                with conn.transaction():
                    self._ensure_unit_config_visible(conn, company_id, data.get("unit_config_id"))
                    existing = conn.execute(
                        f"""
                        SELECT {RULESET_SELECT}
                        FROM cutting_rulesets
                        WHERE id = %s
                          AND company_id = %s
                        """,
                        (ruleset_id, company_id),
                    ).fetchone()
                    if not existing:
                        raise CuttingConfigNotFound("Cutting ruleset not found")
                    self._snapshot_ruleset(conn, self._with_rows(conn, existing), snapshot_reason="update")
                    row = conn.execute(
                        """
                        UPDATE cutting_rulesets
                        SET unit_config_id = %s,
                            unit_type_key = %s,
                            name = %s,
                            description = %s,
                            status = %s,
                            version = %s,
                            is_default = %s
                        WHERE id = %s
                          AND company_id = %s
                        RETURNING id::text
                        """,
                        (
                            data.get("unit_config_id"),
                            data["unit_type_key"],
                            data["name"],
                            data.get("description", ""),
                            data.get("status", "draft"),
                            data.get("version", 1),
                            data.get("is_default", False),
                            ruleset_id,
                            company_id,
                        ),
                    ).fetchone()
                    if not row:
                        raise CuttingConfigNotFound("Cutting ruleset not found")
                    self._replace_rows(conn, ruleset_id, data.get("rows", []))
        except psycopg.errors.UniqueViolation as exc:
            raise CuttingConfigConflict("Cutting ruleset already exists") from exc
        return self.get_ruleset(company_id, ruleset_id)

    def _snapshot_ruleset(self, conn, ruleset: dict[str, Any], snapshot_reason: str) -> None:
        conn.execute(
            """
            INSERT INTO cutting_ruleset_history (
                ruleset_id,
                company_id,
                unit_config_id,
                unit_type_key,
                name,
                description,
                status,
                version,
                is_default,
                rows,
                snapshot_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                ruleset["id"],
                ruleset.get("company_id"),
                ruleset.get("unit_config_id"),
                ruleset["unit_type_key"],
                ruleset["name"],
                ruleset.get("description", ""),
                ruleset.get("status", "draft"),
                ruleset.get("version", 1),
                ruleset.get("is_default", False),
                Jsonb(ruleset.get("rows", []) or []),
                snapshot_reason,
            ),
        )

    def _with_rows(self, conn, ruleset: dict) -> dict:
        rows = conn.execute(
            f"""
            SELECT {RULE_ROW_SELECT}
            FROM cutting_rule_rows
            WHERE ruleset_id = %s
            ORDER BY sort_order ASC, id ASC
            """,
            (ruleset["id"],),
        ).fetchall()
        return {**ruleset, "rows": rows}

    def _replace_rows(self, conn, ruleset_id: str, rows: list[dict[str, Any]]) -> None:
        conn.execute("DELETE FROM cutting_rule_rows WHERE ruleset_id = %s", (ruleset_id,))
        for row in rows:
            data = _clean_payload(row)
            conn.execute(
                """
                INSERT INTO cutting_rule_rows
                    (ruleset_id, sort_order, section, description, length_formula, width_formula,
                     qty_formula, condition_formula, grain_direction, can_rotate,
                     edge_long_1, edge_long_2, edge_short_1, edge_short_2, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ruleset_id,
                    data["sort_order"],
                    data["section"],
                    data["description"],
                    data.get("length_formula", ""),
                    data.get("width_formula", ""),
                    data.get("qty_formula", "1"),
                    data.get("condition_formula", ""),
                    data.get("grain_direction", "none"),
                    data.get("can_rotate", True),
                    data.get("edge_long_1", False),
                    data.get("edge_long_2", False),
                    data.get("edge_short_1", False),
                    data.get("edge_short_2", False),
                    Jsonb(data.get("meta", {}) or {}),
                ),
            )

    def _ensure_unit_config_visible(self, conn, company_id: str, unit_config_id: str | None) -> None:
        if not unit_config_id:
            return
        row = conn.execute(
            """
            SELECT id
            FROM unit_configs
            WHERE id = %s
              AND (company_id IS NULL OR company_id = %s)
            """,
            (unit_config_id, company_id),
        ).fetchone()
        if not row:
            raise CuttingConfigNotFound("Unit config not found")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for cutting config database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _clean(value) for key, value in payload.items()}
