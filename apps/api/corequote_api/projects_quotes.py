from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.projects_quotes_errors import (
    WorkspaceConflict,
    WorkspaceError,
    WorkspaceNotFound,
    WorkspaceValidationError,
)
from corequote_api.projects_quotes_payloads import (
    _clean_custom_panels_payload,
    _clean_project_payload,
    _clean_quote_extras_items,
    _clean_quote_payload,
    _clean_unit_payload,
    _is_enabled,
)
from corequote_api.projects_quotes_pricing import (
    _build_cutting_list_preview,
    _compute_quote_custom_panel_rows,
    _custom_panel_row_response,
    _price_quote,
)


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
    q.custom_panels,
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

    def get_quote_cutting_list(
        self,
        company_id: str,
        quote_id: str,
        *,
        runtime_service: CutlistRuntimeService,
    ) -> dict:
        quote = self.get_quote(company_id, quote_id)
        units = self.list_units(company_id, quote_id)
        use_rulesets = _is_enabled("CUTLIST_USE_DB_RULESETS")

        with self._connect() as conn:
            lookups = self._load_company_item_lookups(conn, company_id)

        return _build_cutting_list_preview(
            company_id=company_id,
            quote=quote,
            units=units,
            runtime_service=runtime_service,
            use_rulesets=use_rulesets,
            board_lookup=lookups["boards"],
            slide_lookup=lookups["slides"],
        )

    def get_quote_custom_panels(self, company_id: str, quote_id: str) -> dict:
        quote = self.get_quote(company_id, quote_id)
        units = self.list_units(company_id, quote_id)
        with self._connect() as conn:
            lookups = self._load_company_item_lookups(conn, company_id)
        state = _clean_custom_panels_payload(quote.get("custom_panels"))
        rows = _compute_quote_custom_panel_rows(
            quote=quote,
            units=units,
            state=state,
            board_lookup=lookups["boards"],
        )
        return {
            "quote_id": quote_id,
            "custom_panels": state,
            "computed_rows": [_custom_panel_row_response(row) for row in rows],
        }

    def replace_quote_custom_panels(self, company_id: str, quote_id: str, payload: dict[str, Any]) -> dict:
        cleaned = _clean_custom_panels_payload(payload)
        with self._connect() as conn:
            with conn.transaction():
                self._ensure_quote_visible(conn, company_id, quote_id)
                self._validate_quote_custom_panels(conn, company_id, cleaned)
                row = conn.execute(
                    """
                    UPDATE quotes
                    SET custom_panels = %s
                    WHERE company_id = %s
                      AND id = %s
                    RETURNING id::text
                    """,
                    (Jsonb(cleaned), company_id, quote_id),
                ).fetchone()
        if not row:
            raise WorkspaceNotFound("Quote not found")
        return self.get_quote_custom_panels(company_id, quote_id)

    def list_quote_extras(self, company_id: str, quote_id: str) -> list[dict]:
        try:
            with self._connect() as conn:
                self._ensure_quote_visible(conn, company_id, quote_id)
                return conn.execute(
                    """
                    SELECT extra_id::text, quantity
                    FROM quote_extras
                    WHERE company_id = %s
                      AND quote_id = %s
                    ORDER BY created_at ASC, id ASC
                    """,
                    (company_id, quote_id),
                ).fetchall()
        except psycopg.errors.UndefinedTable:
            return []

    def replace_quote_extras(self, company_id: str, quote_id: str, items: list[dict[str, Any]]) -> list[dict]:
        cleaned_items = _clean_quote_extras_items(items)
        try:
            with self._connect() as conn:
                with conn.transaction():
                    self._ensure_quote_visible(conn, company_id, quote_id)
                    self._validate_quote_extras(conn, company_id, cleaned_items)
                    conn.execute(
                        """
                        DELETE FROM quote_extras
                        WHERE company_id = %s
                          AND quote_id = %s
                        """,
                        (company_id, quote_id),
                    )
                    if cleaned_items:
                        conn.executemany(
                            """
                            INSERT INTO quote_extras (company_id, quote_id, extra_id, quantity)
                            VALUES (%s, %s, %s, %s)
                            """,
                            [
                                (
                                    company_id,
                                    quote_id,
                                    row["extra_id"],
                                    row["quantity"],
                                )
                                for row in cleaned_items
                            ],
                        )
        except psycopg.errors.UndefinedTable as exc:
            raise WorkspaceValidationError("Quote extras storage is not available. Apply the latest DB migrations.") from exc
        return self.list_quote_extras(company_id, quote_id)

    def get_project_pricing(
        self,
        company_id: str,
        project_id: str,
        *,
        runtime_service: CutlistRuntimeService,
    ) -> dict:
        project = self.get_project(company_id, project_id)
        quotes = self.list_quotes(company_id, project_id)
        quote_ids = [quote["id"] for quote in quotes]
        use_rulesets = _is_enabled("CUTLIST_USE_DB_RULESETS")

        units_by_quote: dict[str, list[dict]] = {quote_id: [] for quote_id in quote_ids}
        extras_by_quote: dict[str, list[dict]] = {quote_id: [] for quote_id in quote_ids}

        with self._connect() as conn:
            pricing_settings = self._get_pricing_settings(conn, company_id)
            active_price_list_id = self._get_active_price_list_id(conn, company_id)
            price_lookup = self._get_price_lookup(conn, company_id, active_price_list_id)
            lookups = self._load_company_item_lookups(conn, company_id)

            if quote_ids:
                for row in conn.execute(
                    f"""
                    SELECT {UNIT_SELECT}
                    FROM quote_units u
                    WHERE u.company_id = %s
                      AND u.quote_id = ANY(%s::uuid[])
                    ORDER BY u.quote_id ASC, u.unit_number ASC, u.created_at ASC
                    """,
                    (company_id, quote_ids),
                ).fetchall():
                    units_by_quote.setdefault(row["quote_id"], []).append(row)

                try:
                    extra_rows = conn.execute(
                        """
                        SELECT quote_id::text, extra_id::text, quantity
                        FROM quote_extras
                        WHERE company_id = %s
                          AND quote_id = ANY(%s::uuid[])
                        ORDER BY quote_id ASC, created_at ASC, id ASC
                        """,
                        (company_id, quote_ids),
                    ).fetchall()
                except psycopg.errors.UndefinedTable:
                    extra_rows = []
                for row in extra_rows:
                    extras_by_quote.setdefault(row["quote_id"], []).append(row)

        quote_summaries = [
            _price_quote(
                quote=quote,
                units=units_by_quote.get(quote["id"], []),
                quote_extras=extras_by_quote.get(quote["id"], []),
                runtime_service=runtime_service,
                company_id=company_id,
                use_rulesets=use_rulesets,
                price_lookup=price_lookup,
                board_lookup=lookups["boards"],
                slide_lookup=lookups["slides"],
                hinge_lookup=lookups["hinges"],
                handle_lookup=lookups["handles"],
                extra_lookup=lookups["extras"],
                active_price_list_id=active_price_list_id,
                markup_bps=int(pricing_settings["default_markup_bps"]),
                vat_rate_bps=int(pricing_settings["vat_rate_bps"]),
            )
            for quote in quotes
        ]

        subtotal_cents = sum(int(row["subtotal_cents"]) for row in quote_summaries)
        sell_before_vat_cents = sum(int(row["sell_before_vat_cents"]) for row in quote_summaries)
        vat_cents = sum(int(row["vat_cents"]) for row in quote_summaries)
        grand_total_cents = sum(int(row["grand_total_cents"]) for row in quote_summaries)
        is_complete = bool(active_price_list_id) and all(bool(row["is_complete"]) for row in quote_summaries)

        return {
            "project_id": project["id"],
            "project_name": project["name"],
            "active_price_list_id": active_price_list_id,
            "vat_rate_bps": int(pricing_settings["vat_rate_bps"]),
            "markup_bps": int(pricing_settings["default_markup_bps"]),
            "is_complete": is_complete,
            "subtotal_cents": subtotal_cents,
            "sell_before_vat_cents": sell_before_vat_cents,
            "vat_cents": vat_cents,
            "grand_total_cents": grand_total_cents,
            "quotes": quote_summaries,
        }

    def _get_pricing_settings(self, conn, company_id: str) -> dict:
        row = conn.execute(
            """
            SELECT vat_rate_bps, default_markup_bps
            FROM pricing_settings
            WHERE company_id = %s
            """,
            (company_id,),
        ).fetchone()
        if row:
            return row
        return {"vat_rate_bps": 1500, "default_markup_bps": 2500}

    def _get_active_price_list_id(self, conn, company_id: str) -> str | None:
        row = conn.execute(
            """
            SELECT id::text
            FROM price_lists
            WHERE company_id = %s
              AND status = 'active'
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()
        return row["id"] if row else None

    def _get_price_lookup(self, conn, company_id: str, price_list_id: str | None) -> dict[tuple[str, str, str], dict]:
        if not price_list_id:
            return {}
        rows = conn.execute(
            """
            SELECT item_type, item_key, price_component, uom, unit_price_cents
            FROM price_list_items
            WHERE company_id = %s
              AND price_list_id = %s
              AND effective_to IS NULL
            ORDER BY item_type ASC, item_key ASC, price_component ASC
            """,
            (company_id, price_list_id),
        ).fetchall()
        return {
            (str(row["item_type"]), str(row["item_key"]), str(row["price_component"])): row
            for row in rows
        }

    def _load_company_item_lookups(self, conn, company_id: str) -> dict[str, dict[str, dict]]:
        boards = {
            row["id"]: row
            for row in conn.execute(
                """
                SELECT id::text, brand, material, thickness, length_mm, width_mm, costing_mode
                FROM board_types
                WHERE company_id = %s
                ORDER BY brand ASC, material ASC, thickness ASC
                """,
                (company_id,),
            ).fetchall()
        }
        slides = {
            row["id"]: row
            for row in conn.execute(
                """
                SELECT id::text, brand, model, code, length, side_length, side_clearance_total, side_height_uplift
                FROM slides
                WHERE company_id = %s
                ORDER BY brand ASC, model ASC, code ASC
                """,
                (company_id,),
            ).fetchall()
        }
        hinges = {
            row["id"]: row
            for row in conn.execute(
                """
                SELECT id::text, brand, model, code, opening_angle_deg
                FROM hinges
                WHERE company_id = %s
                ORDER BY brand ASC, model ASC, code ASC
                """,
                (company_id,),
            ).fetchall()
        }
        handles = {
            row["id"]: row
            for row in conn.execute(
                """
                SELECT id::text, name, supplier, code
                FROM handles
                WHERE company_id = %s
                ORDER BY name ASC, supplier ASC, code ASC
                """,
                (company_id,),
            ).fetchall()
        }
        extras = {
            row["id"]: row
            for row in conn.execute(
                """
                SELECT id::text, name, supplier, code
                FROM extras
                WHERE company_id = %s
                ORDER BY name ASC, supplier ASC, code ASC
                """,
                (company_id,),
            ).fetchall()
        }
        return {
            "boards": boards,
            "slides": slides,
            "hinges": hinges,
            "handles": handles,
            "extras": extras,
        }

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

    def _validate_quote_extras(self, conn, company_id: str, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        extra_ids = [row["extra_id"] for row in items]
        visible_rows = conn.execute(
            """
            SELECT id::text
            FROM extras
            WHERE company_id = %s
              AND id = ANY(%s::uuid[])
            """,
            (company_id, extra_ids),
        ).fetchall()
        visible = {row["id"] for row in visible_rows}
        for extra_id in extra_ids:
            if extra_id not in visible:
                raise WorkspaceValidationError(f"Extra is not visible for this company: {extra_id}")

    def _validate_quote_custom_panels(self, conn, company_id: str, state: dict[str, Any]) -> None:
        board_ids: set[str] = set()

        presets = state.get("presets", {}) or {}
        for config in presets.values():
            if isinstance(config, dict):
                board_id = str(config.get("board_type_id") or "").strip()
                if board_id:
                    board_ids.add(board_id)

        for row in state.get("manual", []) or []:
            if not isinstance(row, dict):
                continue
            board_id = str(row.get("board_type_id") or "").strip()
            if board_id:
                board_ids.add(board_id)

        auto = state.get("auto", {}) or {}
        if isinstance(auto, dict):
            for key in ("kicker_board_type_id", "pelmet_board_type_id"):
                board_id = str(auto.get(key) or "").strip()
                if board_id:
                    board_ids.add(board_id)

        for board_id in sorted(board_ids):
            self._ensure_library_item_visible(
                conn,
                company_id,
                "board_types",
                board_id,
                "Custom panel board",
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
