from __future__ import annotations

import os
from collections.abc import Callable, Iterable

import psycopg
from psycopg.rows import dict_row

from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.schemas import CutlistUnitRequest

BoardThicknessLookup = Callable[[str, set[str]], dict[str, int]]


def preview_cutlist(
    units: Iterable[CutlistUnitRequest],
    *,
    company_id: str,
    runtime_service: CutlistRuntimeService | None = None,
    use_db_rulesets: bool | None = None,
    board_thickness_lookup: BoardThicknessLookup | None = None,
) -> dict:
    payload_units = _runtime_units_from_preview_request(
        units,
        company_id=company_id,
        board_thickness_lookup=board_thickness_lookup or _load_board_thicknesses,
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
) -> list[dict]:
    payload_units = [unit.model_dump() for unit in units]
    board_ids = {str(unit["board_type_id"]).strip() for unit in payload_units}
    thickness_by_board_id = board_thickness_lookup(company_id, board_ids)

    for unit in payload_units:
        board_id = str(unit.pop("board_type_id")).strip()
        thickness = int(thickness_by_board_id.get(board_id, 0) or 0)
        if thickness <= 0:
            raise ValueError(f"Board type is not visible for this company: {board_id}")
        unit["thickness"] = thickness
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


def _is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
