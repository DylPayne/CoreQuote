from __future__ import annotations

import os
from collections.abc import Iterable

from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.schemas import CutlistUnitRequest


def preview_cutlist(
    units: Iterable[CutlistUnitRequest],
    *,
    company_id: str,
    runtime_service: CutlistRuntimeService | None = None,
    use_db_rulesets: bool | None = None,
) -> dict:
    payload_units = [unit.model_dump() for unit in units]
    service = runtime_service or CutlistRuntimeService()
    use_rulesets = _is_enabled("CUTLIST_USE_DB_RULESETS") if use_db_rulesets is None else use_db_rulesets
    return service.build_preview(
        company_id=company_id,
        units=payload_units,
        use_db_rulesets=use_rulesets,
    )


def _is_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
