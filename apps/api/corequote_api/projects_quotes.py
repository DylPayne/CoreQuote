from __future__ import annotations

import math
import os
from collections import defaultdict
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from corequote_core.panels import PANEL_PRESET_KEYS, PANEL_PRESET_LABELS, compute_panel_rows
from corequote_api.cutting_runtime import CutlistRuntimeService, canonical_unit_type_key


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


def _compute_quote_custom_panel_rows(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    state: dict[str, Any],
    board_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_units = [
        {
            "unit_type": str(unit.get("unit_type_key") or unit.get("unit_type") or ""),
            "width": int(unit.get("width", 0) or 0),
        }
        for unit in units
    ]

    return compute_panel_rows(
        units=normalized_units,
        state=state,
        default_panel_board_type_id=quote.get("default_panel_board_type_id"),
        panel_preset_keys=PANEL_PRESET_KEYS,
        panel_preset_labels=PANEL_PRESET_LABELS,
        default_dims_for_panel_preset=lambda key: _default_dims_for_panel_preset_from_quote(quote, key),
        default_dims_for_unit_type=lambda unit_type: _default_dims_for_unit_type_from_quote(quote, unit_type),
        board_length_for=lambda board_type_id: int(
            (
                board_lookup.get(str(board_type_id or "").strip())
                or {}
            ).get("length_mm", 0)
            or 0
        ),
    )


def _custom_panel_row_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "desc": str(row.get("Desc", "")),
        "length": int(row.get("L", 0) or 0),
        "width": int(row.get("W", 0) or 0),
        "qty": int(row.get("Qty", 0) or 0),
        "board_type_id": _optional_uuid(row.get("board_type_id")),
    }


def _build_cutting_list_preview(
    *,
    company_id: str,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    runtime_service: CutlistRuntimeService,
    use_rulesets: bool,
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    default_slide = slide_lookup.get(str(quote.get("default_slide_id") or ""))
    payload_units = [_to_runtime_unit(unit, default_slide=default_slide) for unit in units]
    preview = runtime_service.build_preview(
        company_id=company_id,
        units=payload_units,
        use_db_rulesets=use_rulesets,
    )

    if not preview:
        preview = {
            "carcass": [],
            "panels": [],
            "hardware": [],
            "extras": [],
            "runtime_rows": [],
            "runtime_mode": "legacy",
            "unit_sources": [],
        }

    state = _clean_custom_panels_payload(quote.get("custom_panels"))
    custom_rows = _compute_quote_custom_panel_rows(
        quote=quote,
        units=units,
        state=state,
        board_lookup=board_lookup,
    )
    for row in custom_rows:
        compact = {
            "unit_number": 0,
            "desc": str(row["Desc"]),
            "length": int(row["L"]),
            "width": int(row["W"]),
            "qty": int(row["Qty"]),
        }
        preview.setdefault("extras", []).append(compact)
        preview.setdefault("runtime_rows", []).append(
            {
                **compact,
                "section": "extra_panel",
                "edge_long_1": False,
                "edge_long_2": False,
                "edge_short_1": False,
                "edge_short_2": False,
                "board_type_id": row.get("board_type_id"),
            }
        )

    return preview


def _to_runtime_unit(unit: dict[str, Any], *, default_slide: dict[str, Any] | None) -> dict[str, Any]:
    extra_params = dict(unit.get("extra_params") or {})
    if default_slide:
        extra_params.setdefault("slide_brand", default_slide.get("brand", ""))
        extra_params.setdefault("slide_model", default_slide.get("model", ""))
        extra_params.setdefault("slide_code", default_slide.get("code", ""))
        extra_params.setdefault("slide_length", int(default_slide.get("length", 0) or 0))
        extra_params.setdefault("slide_side_length", int(default_slide.get("side_length", 0) or 0))
        extra_params.setdefault("slide_side_clearance_total", int(default_slide.get("side_clearance_total", 0) or 0))
        extra_params.setdefault("slide_side_height_uplift", int(default_slide.get("side_height_uplift", 0) or 0))
    return {
        "unit_number": int(unit["unit_number"]),
        "unit_type": str(unit["unit_type_key"]),
        "height": int(unit["height"]),
        "width": int(unit["width"]),
        "depth": int(unit["depth"]),
        "thickness": int(unit.get("thickness", 16) or 16),
        "extra_params": extra_params,
    }


def _price_quote(
    *,
    quote: dict[str, Any],
    units: list[dict[str, Any]],
    quote_extras: list[dict[str, Any]],
    runtime_service: CutlistRuntimeService,
    company_id: str,
    use_rulesets: bool,
    price_lookup: dict[tuple[str, str, str], dict[str, Any]],
    board_lookup: dict[str, dict[str, Any]],
    slide_lookup: dict[str, dict[str, Any]],
    hinge_lookup: dict[str, dict[str, Any]],
    handle_lookup: dict[str, dict[str, Any]],
    extra_lookup: dict[str, dict[str, Any]],
    active_price_list_id: str | None,
    markup_bps: int,
    vat_rate_bps: int,
) -> dict[str, Any]:
    cutting_list = _build_cutting_list_preview(
        company_id=company_id,
        quote=quote,
        units=units,
        runtime_service=runtime_service,
        use_rulesets=use_rulesets,
        board_lookup=board_lookup,
        slide_lookup=slide_lookup,
    )

    required: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add_required(
        *,
        item_type: str,
        item_key: str | None,
        price_component: str,
        description: str,
        qty: float,
        uom: str,
    ) -> None:
        if not item_key:
            return
        rounded_qty = float(qty)
        if rounded_qty <= 0:
            return
        key = (item_type, item_key, price_component)
        row = required.get(key)
        if row:
            row["qty"] += rounded_qty
            return
        required[key] = {
            "item_type": item_type,
            "item_key": item_key,
            "price_component": price_component,
            "description": description,
            "qty": rounded_qty,
            "uom": uom,
        }

    units_by_number = {int(unit["unit_number"]): unit for unit in units}
    board_usage: dict[str, dict[str, Any]] = {}
    for row in cutting_list.get("runtime_rows", []):
        section = str(row.get("section", ""))
        unit = units_by_number.get(int(row.get("unit_number", 0)))
        if section in {"carcass", "panel"} and not unit:
            continue

        board_id: str | None
        if section == "carcass":
            board_id = str(unit.get("carcass_board_type_id") or quote.get("default_carcass_board_type_id") or "")
        elif section == "panel":
            board_id = str(unit.get("door_board_type_id") or quote.get("default_door_board_type_id") or "")
        elif section == "extra_panel":
            explicit_board_id = str(row.get("board_type_id") or "").strip()
            board_id = explicit_board_id or str(
                quote.get("default_panel_board_type_id")
                or (unit or {}).get("door_board_type_id")
                or quote.get("default_door_board_type_id")
                or ""
            )
        else:
            continue
        if not board_id:
            continue

        length = int(row.get("length", 0) or 0)
        width = int(row.get("width", 0) or 0)
        qty = int(row.get("qty", 0) or 0)
        if length <= 0 or width <= 0 or qty <= 0:
            continue

        usage = board_usage.setdefault(board_id, {"piece_areas": [], "total_area_mm2": 0})
        usage["piece_areas"].extend([length * width] * qty)
        usage["total_area_mm2"] += length * width * qty

    for board_id, usage in board_usage.items():
        board = board_lookup.get(board_id)
        if not board:
            continue
        item_key = f"board::{board_id}"
        costing_mode = str(board.get("costing_mode", "sheet") or "sheet").strip().lower()
        description = _board_description(board)
        if costing_mode == "sqm":
            area_m2 = float(usage["total_area_mm2"]) / 1_000_000.0
            add_required(
                item_type="board",
                item_key=item_key,
                price_component="sqm",
                description=description,
                qty=area_m2,
                uom="m2",
            )
            continue
        sheet_area = int(board.get("length_mm", 0) or 0) * int(board.get("width_mm", 0) or 0)
        sheets_used = _estimate_boards_used(usage["piece_areas"], sheet_area)
        add_required(
            item_type="board",
            item_key=item_key,
            price_component="sheet",
            description=description,
            qty=float(sheets_used),
            uom="sheet",
        )

    for unit in units:
        canonical_type = canonical_unit_type_key(str(unit["unit_type_key"]))
        extra_params = unit.get("extra_params", {}) or {}
        height = int(unit.get("height", 0) or 0)
        num_drawers = _int_or_default(extra_params.get("num_drawers"), default=3 if canonical_type == "Base Draw" else 0, minimum=0)
        num_doors = _int_or_default(
            extra_params.get("num_doors"),
            default=2 if canonical_type in {"Base Door", "Wall Door", "Tall Door"} else 0,
            minimum=0,
        )

        if canonical_type == "Base Draw":
            slide_id = str(quote.get("default_slide_id") or "")
            add_required(
                item_type="slide",
                item_key=f"slide::{slide_id}" if slide_id else None,
                price_component="unit",
                description=_slide_description(slide_lookup.get(slide_id)),
                qty=float(num_drawers),
                uom="pairs",
            )
            drawer_handle_id = str(quote.get("default_drawer_handle_id") or "")
            drawer_handle_qty = _int_or_default(extra_params.get("handle_qty"), default=num_drawers, minimum=0)
            add_required(
                item_type="handle",
                item_key=f"handle::{drawer_handle_id}" if drawer_handle_id else None,
                price_component="unit",
                description=_handle_description(handle_lookup.get(drawer_handle_id)),
                qty=float(drawer_handle_qty),
                uom="pcs",
            )

        if canonical_type in {"Base Door", "Wall Door", "Tall Door"}:
            hinge_id = str(quote.get("default_hinge_id") or "")
            hinges_per_door = max(2, math.ceil(height / 600)) if height > 0 else 2
            add_required(
                item_type="hinge",
                item_key=f"hinge::{hinge_id}" if hinge_id else None,
                price_component="unit",
                description=_hinge_description(hinge_lookup.get(hinge_id)),
                qty=float(num_doors * hinges_per_door),
                uom="pcs",
            )

            if canonical_type == "Wall Door":
                handle_id = str(quote.get("default_wall_handle_id") or "")
            elif canonical_type == "Tall Door":
                handle_id = str(quote.get("default_tall_handle_id") or "")
            else:
                handle_id = str(quote.get("default_base_handle_id") or "")

            handle_qty = _int_or_default(extra_params.get("handle_qty"), default=num_doors, minimum=0)
            add_required(
                item_type="handle",
                item_key=f"handle::{handle_id}" if handle_id else None,
                price_component="unit",
                description=_handle_description(handle_lookup.get(handle_id)),
                qty=float(handle_qty),
                uom="pcs",
            )

    for selected_extra in quote_extras:
        extra_id = str(selected_extra.get("extra_id") or "")
        quantity = _int_or_default(selected_extra.get("quantity"), default=1, minimum=0)
        add_required(
            item_type="extra",
            item_key=f"extra::{extra_id}" if extra_id else None,
            price_component="unit",
            description=_extra_description(extra_lookup.get(extra_id)),
            qty=float(quantity),
            uom="pcs",
        )

    lines: list[dict[str, Any]] = []
    missing_items: list[str] = []
    subtotal_cents = 0
    for _, row in sorted(required.items(), key=lambda entry: (entry[1]["item_type"], entry[1]["description"])):
        lookup_key = (row["item_type"], row["item_key"], row["price_component"])
        active_price = price_lookup.get(lookup_key)
        unit_price_cents: int | None = None
        line_total_cents: int | None = None
        missing = active_price is None
        if active_price is None:
            missing_items.append(f"{row['item_key']}::{row['price_component']}")
        else:
            unit_price_cents = int(active_price["unit_price_cents"])
            line_total_cents = int(round(float(row["qty"]) * unit_price_cents))
            subtotal_cents += line_total_cents

        lines.append(
            {
                "item_type": row["item_type"],
                "item_key": row["item_key"],
                "price_component": row["price_component"],
                "description": row["description"],
                "qty": float(round(float(row["qty"]), 4)),
                "uom": row["uom"],
                "unit_price_cents": unit_price_cents,
                "line_total_cents": line_total_cents,
                "missing": missing,
            }
        )

    sell_before_vat_cents = int(round(subtotal_cents * (1.0 + (markup_bps / 10_000.0))))
    vat_cents = int(round(sell_before_vat_cents * (vat_rate_bps / 10_000.0)))
    grand_total_cents = sell_before_vat_cents + vat_cents

    return {
        "quote_id": quote["id"],
        "quote_name": quote["name"],
        "is_complete": bool(active_price_list_id) and len(missing_items) == 0,
        "missing_items": missing_items,
        "subtotal_cents": subtotal_cents,
        "sell_before_vat_cents": sell_before_vat_cents,
        "vat_cents": vat_cents,
        "grand_total_cents": grand_total_cents,
        "lines": lines,
    }


def _estimate_boards_used(piece_areas_mm2: list[int], sheet_area_mm2: int) -> int:
    if sheet_area_mm2 <= 0 or not piece_areas_mm2:
        return 0
    bins: list[int] = []
    for area in sorted((int(value) for value in piece_areas_mm2 if int(value) > 0), reverse=True):
        for index, remaining in enumerate(bins):
            if area <= remaining:
                bins[index] = remaining - area
                break
        else:
            bins.append(max(0, sheet_area_mm2 - area))
    return len(bins)


def _int_or_default(value: Any, *, default: int, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _board_description(board: dict[str, Any] | None) -> str:
    if not board:
        return "Board"
    return f"{board['brand']} {board['material']} ({board['thickness']}mm)"


def _slide_description(slide: dict[str, Any] | None) -> str:
    if not slide:
        return "Slide"
    code = str(slide.get("code", "")).strip()
    return f"{slide['brand']} {slide['model']}{f' ({code})' if code else ''}"


def _hinge_description(hinge: dict[str, Any] | None) -> str:
    if not hinge:
        return "Hinge"
    code = str(hinge.get("code", "")).strip()
    return f"{hinge['brand']} {hinge['model']}{f' ({code})' if code else ''}"


def _handle_description(handle: dict[str, Any] | None) -> str:
    if not handle:
        return "Handle"
    supplier = str(handle.get("supplier", "")).strip()
    return f"{handle['name']}{f' · {supplier}' if supplier else ''}"


def _extra_description(extra: dict[str, Any] | None) -> str:
    if not extra:
        return "Extra"
    supplier = str(extra.get("supplier", "")).strip()
    return f"{extra['name']}{f' · {supplier}' if supplier else ''}"
