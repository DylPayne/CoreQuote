from __future__ import annotations

import os
from collections.abc import Callable, Iterable

import psycopg
from psycopg.rows import dict_row

from corequote_core.channel_handles import attach_profile_handle_lookup, selected_profile_handle_ids
from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.schemas import CutlistUnitRequest

BoardThicknessLookup = Callable[[str, set[str]], dict[str, int]]
HandleLookup = Callable[[str, set[str]], dict[str, dict]]


def preview_cutlist(
    units: Iterable[CutlistUnitRequest],
    *,
    company_id: str,
    runtime_service: CutlistRuntimeService | None = None,
    use_db_rulesets: bool | None = None,
    board_thickness_lookup: BoardThicknessLookup | None = None,
    handle_lookup: HandleLookup | None = None,
) -> dict:
    payload_units = _runtime_units_from_preview_request(
        units,
        company_id=company_id,
        board_thickness_lookup=board_thickness_lookup or _load_board_thicknesses,
        handle_lookup=handle_lookup or _load_handles,
    )
    service = runtime_service or CutlistRuntimeService()
    use_rulesets = _is_enabled("CUTLIST_USE_DB_RULESETS") if use_db_rulesets is None else use_db_rulesets
    return service.build_preview(
        company_id=company_id,
        units=payload_units,
        use_db_rulesets=use_rulesets,
    )


def _runtime_units_from_preview_request(
    units: Iterable[CutlistUnitRequest],
    *,
    company_id: str,
    board_thickness_lookup: BoardThicknessLookup,
    handle_lookup: HandleLookup,
) -> list[dict]:
    payload_units = [unit.model_dump() for unit in units]
    board_ids = {str(unit["board_type_id"]).strip() for unit in payload_units}
    thickness_by_board_id = board_thickness_lookup(company_id, board_ids)
    handle_ids: set[str] = set()
    for unit in payload_units:
        extra_params = unit.get("extra_params") if isinstance(unit.get("extra_params"), dict) else {}
        handle_ids.update(selected_profile_handle_ids(extra_params))
    handles_by_id = handle_lookup(company_id, handle_ids) if handle_ids else {}

    for unit in payload_units:
        board_id = str(unit.pop("board_type_id")).strip()
        thickness = int(thickness_by_board_id.get(board_id, 0) or 0)
        if thickness <= 0:
            raise ValueError(f"Board type is not visible for this company: {board_id}")
        unit["thickness"] = thickness
        extra_params = unit.get("extra_params") if isinstance(unit.get("extra_params"), dict) else {}
        unit["extra_params"] = attach_profile_handle_lookup(extra_params, handles_by_id)
    return payload_units


def _load_board_thicknesses(company_id: str, board_ids: set[str]) -> dict[str, int]:
    if not board_ids:
        return {}
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required to resolve board thickness")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT id::text, thickness
            FROM board_types
            WHERE company_id = %s
              AND id::text = ANY(%s)
            """,
            (company_id, sorted(board_ids)),
        ).fetchall()
    return {row["id"]: int(row["thickness"]) for row in rows}


def _load_handles(company_id: str, handle_ids: set[str]) -> dict[str, dict]:
    if not handle_ids:
        return {}
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required to resolve profile handles")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            SELECT
                h.id::text,
                h.name,
                h.supplier_id::text,
                COALESCE(s.name, '') AS supplier_name,
                handle_type,
                front_reduction_mm
            FROM handles h
            LEFT JOIN suppliers s
              ON s.company_id = h.company_id
             AND s.id = h.supplier_id
            WHERE h.company_id = %s
              AND h.id::text = ANY(%s)
            """,
            (company_id, sorted(handle_ids)),
        ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def _is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
