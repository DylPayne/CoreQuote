from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class WorkspaceError(Exception):
    pass


class WorkspaceNotFound(WorkspaceError):
    pass


class WorkspaceConflict(WorkspaceError):
    pass


class WorkspaceValidationError(WorkspaceError):
    pass


PROJECT_SELECT = """
    p.id::text,
    p.company_id::text,
    p.name,
    p.client,
    p.address,
    p.description,
    COALESCE(count(q.id), 0)::int AS quote_count,
    p.created_at,
    p.updated_at
"""

QUOTE_SELECT = """
    q.id::text,
    q.company_id::text,
    q.project_id::text,
    q.name,
    q.notes,
    q.default_carcass_board_type_id::text,
    q.default_door_board_type_id::text,
    q.default_panel_board_type_id::text,
    q.default_slide_id::text,
    q.default_hinge_id::text,
    q.default_base_handle_id::text,
    q.default_wall_handle_id::text,
    q.default_tall_handle_id::text,
    q.default_drawer_handle_id::text,
    q.unit_defaults,
    COALESCE(count(qu.id), 0)::int AS unit_count,
    q.created_at,
    q.updated_at
"""

UNIT_SELECT = """
    u.id::text,
    u.company_id::text,
    u.quote_id::text,
    u.unit_number,
    u.unit_type_key,
    u.height,
    u.width,
    u.depth,
    u.thickness,
    u.carcass_board_type_id::text,
    u.door_board_type_id::text,
    u.extra_params,
    u.created_at,
    u.updated_at
"""


class WorkspaceStore:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")

    def list_projects(self, company_id: str, search: str | None = None) -> list[dict]:
        params: list[Any] = [company_id]
        filters = ["p.company_id = %s"]
        if search:
            filters.append("(p.name ILIKE %s OR p.client ILIKE %s OR p.address ILIKE %s)")
            like = f"%{search.strip()}%"
            params.extend([like, like, like])

        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT {PROJECT_SELECT}
                FROM projects p
                LEFT JOIN quotes q
                    ON q.project_id = p.id
                   AND q.company_id = p.company_id
                WHERE {' AND '.join(filters)}
                GROUP BY p.id
                ORDER BY p.updated_at DESC, p.created_at DESC
                """,
                params,
            ).fetchall()

    def create_project(self, company_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_project_payload(payload)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO projects (company_id, name, client, address, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        data["name"],
                        data["client"],
                        data["address"],
                        data["description"],
                    ),
                ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise WorkspaceConflict("Project already exists") from exc
        return self.get_project(company_id, row["id"])

    def get_project(self, company_id: str, project_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {PROJECT_SELECT}
                FROM projects p
                LEFT JOIN quotes q
                    ON q.project_id = p.id
                   AND q.company_id = p.company_id
                WHERE p.company_id = %s
                  AND p.id = %s
                GROUP BY p.id
                """,
                (company_id, project_id),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Project not found")
        return row

    def update_project(self, company_id: str, project_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_project_payload(payload)
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE projects
                SET name = %s,
                    client = %s,
                    address = %s,
                    description = %s
                WHERE company_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (
                    data["name"],
                    data["client"],
                    data["address"],
                    data["description"],
                    company_id,
                    project_id,
                ),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Project not found")
        return self.get_project(company_id, project_id)

    def delete_project(self, company_id: str, project_id: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                DELETE FROM projects
                WHERE company_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (company_id, project_id),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Project not found")

    def list_quotes(self, company_id: str, project_id: str) -> list[dict]:
        with self._connect() as conn:
            self._ensure_project_visible(conn, company_id, project_id)
            return conn.execute(
                f"""
                SELECT {QUOTE_SELECT}
                FROM quotes q
                LEFT JOIN quote_units qu
                    ON qu.quote_id = q.id
                   AND qu.company_id = q.company_id
                WHERE q.company_id = %s
                  AND q.project_id = %s
                GROUP BY q.id
                ORDER BY q.updated_at DESC, q.created_at DESC
                """,
                (company_id, project_id),
            ).fetchall()

    def create_quote(self, company_id: str, project_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_quote_payload(payload)
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_project_visible(conn, company_id, project_id)
                self._validate_quote_defaults(conn, company_id, data)
                row = conn.execute(
                    """
                    INSERT INTO quotes (
                        company_id,
                        project_id,
                        name,
                        notes,
                        default_carcass_board_type_id,
                        default_door_board_type_id,
                        default_panel_board_type_id,
                        default_slide_id,
                        default_hinge_id,
                        default_base_handle_id,
                        default_wall_handle_id,
                        default_tall_handle_id,
                        default_drawer_handle_id,
                        unit_defaults
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        project_id,
                        data["name"],
                        data["notes"],
                        data["default_carcass_board_type_id"],
                        data["default_door_board_type_id"],
                        data["default_panel_board_type_id"],
                        data["default_slide_id"],
                        data["default_hinge_id"],
                        data["default_base_handle_id"],
                        data["default_wall_handle_id"],
                        data["default_tall_handle_id"],
                        data["default_drawer_handle_id"],
                        Jsonb(data["unit_defaults"]),
                    ),
                ).fetchone()
        return self.get_quote(company_id, row["id"])

    def get_quote(self, company_id: str, quote_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {QUOTE_SELECT}
                FROM quotes q
                LEFT JOIN quote_units qu
                    ON qu.quote_id = q.id
                   AND qu.company_id = q.company_id
                WHERE q.company_id = %s
                  AND q.id = %s
                GROUP BY q.id
                """,
                (company_id, quote_id),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Quote not found")
        return row

    def update_quote(self, company_id: str, quote_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_quote_payload(payload)
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_quote_visible(conn, company_id, quote_id)
                self._validate_quote_defaults(conn, company_id, data)
                row = conn.execute(
                    """
                    UPDATE quotes
                    SET name = %s,
                        notes = %s,
                        default_carcass_board_type_id = %s,
                        default_door_board_type_id = %s,
                        default_panel_board_type_id = %s,
                        default_slide_id = %s,
                        default_hinge_id = %s,
                        default_base_handle_id = %s,
                        default_wall_handle_id = %s,
                        default_tall_handle_id = %s,
                        default_drawer_handle_id = %s,
                        unit_defaults = %s
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (
                        data["name"],
                        data["notes"],
                        data["default_carcass_board_type_id"],
                        data["default_door_board_type_id"],
                        data["default_panel_board_type_id"],
                        data["default_slide_id"],
                        data["default_hinge_id"],
                        data["default_base_handle_id"],
                        data["default_wall_handle_id"],
                        data["default_tall_handle_id"],
                        data["default_drawer_handle_id"],
                        Jsonb(data["unit_defaults"]),
                        company_id,
                        quote_id,
                    ),
                ).fetchone()
        if not row:
            raise WorkspaceNotFound("Quote not found")
        return self.get_quote(company_id, quote_id)

    def delete_quote(self, company_id: str, quote_id: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                DELETE FROM quotes
                WHERE company_id = %s
                  AND id = %s
                RETURNING id::text
                """,
                (company_id, quote_id),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Quote not found")

    def list_units(self, company_id: str, quote_id: str) -> list[dict]:
        with self._connect() as conn:
            self._ensure_quote_visible(conn, company_id, quote_id)
            return conn.execute(
                f"""
                SELECT {UNIT_SELECT}
                FROM quote_units u
                WHERE u.company_id = %s
                  AND u.quote_id = %s
                ORDER BY u.unit_number ASC, u.created_at ASC
                """,
                (company_id, quote_id),
            ).fetchall()

    def create_unit(self, company_id: str, quote_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_unit_payload(payload)
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_quote_visible(conn, company_id, quote_id)
                self._validate_unit_defaults(conn, company_id, data)
                next_number_row = conn.execute(
                    """
                    SELECT COALESCE(MAX(unit_number), 0) + 1 AS next_unit_number
                    FROM quote_units
                    WHERE company_id = %s
                      AND quote_id = %s
                    """,
                    (company_id, quote_id),
                ).fetchone()
                row = conn.execute(
                    """
                    INSERT INTO quote_units (
                        company_id,
                        quote_id,
                        unit_number,
                        unit_type_key,
                        height,
                        width,
                        depth,
                        thickness,
                        carcass_board_type_id,
                        door_board_type_id,
                        extra_params
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        company_id,
                        quote_id,
                        int(next_number_row["next_unit_number"]),
                        data["unit_type_key"],
                        data["height"],
                        data["width"],
                        data["depth"],
                        data["thickness"],
                        data["carcass_board_type_id"],
                        data["door_board_type_id"],
                        Jsonb(data["extra_params"]),
                    ),
                ).fetchone()
        return self.get_unit(company_id, quote_id, row["id"])

    def get_unit(self, company_id: str, quote_id: str, unit_id: str) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT {UNIT_SELECT}
                FROM quote_units u
                WHERE u.company_id = %s
                  AND u.quote_id = %s
                  AND u.id = %s
                """,
                (company_id, quote_id, unit_id),
            ).fetchone()
        if not row:
            raise WorkspaceNotFound("Unit not found")
        return row

    def update_unit(self, company_id: str, quote_id: str, unit_id: str, payload: dict[str, Any]) -> dict:
        data = _clean_unit_payload(payload)
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_quote_visible(conn, company_id, quote_id)
                self._validate_unit_defaults(conn, company_id, data)
                row = conn.execute(
                    """
                    UPDATE quote_units
                    SET unit_type_key = %s,
                        height = %s,
                        width = %s,
                        depth = %s,
                        thickness = %s,
                        carcass_board_type_id = %s,
                        door_board_type_id = %s,
                        extra_params = %s
                    WHERE company_id = %s
                      AND quote_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (
                        data["unit_type_key"],
                        data["height"],
                        data["width"],
                        data["depth"],
                        data["thickness"],
                        data["carcass_board_type_id"],
                        data["door_board_type_id"],
                        Jsonb(data["extra_params"]),
                        company_id,
                        quote_id,
                        unit_id,
                    ),
                ).fetchone()
        if not row:
            raise WorkspaceNotFound("Unit not found")
        return self.get_unit(company_id, quote_id, unit_id)

    def delete_unit(self, company_id: str, quote_id: str, unit_id: str) -> None:
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_quote_visible(conn, company_id, quote_id)
                row = conn.execute(
                    """
                    DELETE FROM quote_units
                    WHERE company_id = %s
                      AND quote_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (company_id, quote_id, unit_id),
                ).fetchone()
                if not row:
                    raise WorkspaceNotFound("Unit not found")

                conn.execute(
                    """
                    WITH ranked AS (
                        SELECT
                            id,
                            ROW_NUMBER() OVER (ORDER BY unit_number ASC, created_at ASC, id ASC) AS seq
                        FROM quote_units
                        WHERE company_id = %s
                          AND quote_id = %s
                    )
                    UPDATE quote_units u
                    SET unit_number = ranked.seq
                    FROM ranked
                    WHERE u.id = ranked.id
                      AND u.unit_number <> ranked.seq
                    """,
                    (company_id, quote_id),
                )

    def _validate_quote_defaults(self, conn, company_id: str, data: dict[str, Any]) -> None:
        self._ensure_library_item_visible(
            conn,
            company_id,
            "board_types",
            data["default_carcass_board_type_id"],
            "Default carcass board",
        )
        self._ensure_library_item_visible(
            conn,
            company_id,
            "board_types",
            data["default_door_board_type_id"],
            "Default door board",
        )
        self._ensure_library_item_visible(
            conn,
            company_id,
            "board_types",
            data["default_panel_board_type_id"],
            "Default panel board",
        )
        self._ensure_library_item_visible(conn, company_id, "slides", data["default_slide_id"], "Default slide")
        self._ensure_library_item_visible(conn, company_id, "hinges", data["default_hinge_id"], "Default hinge")
        self._ensure_library_item_visible(conn, company_id, "handles", data["default_base_handle_id"], "Default base handle")
        self._ensure_library_item_visible(conn, company_id, "handles", data["default_wall_handle_id"], "Default wall handle")
        self._ensure_library_item_visible(conn, company_id, "handles", data["default_tall_handle_id"], "Default tall handle")
        self._ensure_library_item_visible(conn, company_id, "handles", data["default_drawer_handle_id"], "Default drawer handle")

    def _validate_unit_defaults(self, conn, company_id: str, data: dict[str, Any]) -> None:
        self._ensure_library_item_visible(
            conn,
            company_id,
            "board_types",
            data["carcass_board_type_id"],
            "Unit carcass board",
        )
        self._ensure_library_item_visible(
            conn,
            company_id,
            "board_types",
            data["door_board_type_id"],
            "Unit door board",
        )

    def _ensure_project_visible(self, conn, company_id: str, project_id: str) -> None:
        row = conn.execute(
            """
            SELECT id::text
            FROM projects
            WHERE company_id = %s
              AND id = %s
            """,
            (company_id, project_id),
        ).fetchone()
        if not row:
            raise WorkspaceNotFound("Project not found")

    def _ensure_quote_visible(self, conn, company_id: str, quote_id: str) -> None:
        row = conn.execute(
            """
            SELECT id::text
            FROM quotes
            WHERE company_id = %s
              AND id = %s
            """,
            (company_id, quote_id),
        ).fetchone()
        if not row:
            raise WorkspaceNotFound("Quote not found")

    def _ensure_library_item_visible(
        self,
        conn,
        company_id: str,
        table_name: str,
        item_id: str | None,
        label: str,
    ) -> None:
        if not item_id:
            return

        row = conn.execute(
            f"""
            SELECT id::text
            FROM {table_name}
            WHERE company_id = %s
              AND id = %s
            """,
            (company_id, item_id),
        ).fetchone()
        if not row:
            raise WorkspaceValidationError(f"{label} is not visible for this company")

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for workspace database access")
        return psycopg.connect(self.database_url, row_factory=dict_row)


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
