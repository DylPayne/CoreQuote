from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from corequote_core.cutlist import build_cutlist

from corequote_api.schemas import CutlistRowResponse, CutlistUnitRequest


def preview_cutlist(units: Iterable[CutlistUnitRequest]) -> tuple[list[CutlistRowResponse], list[CutlistRowResponse]]:
    unit_dicts = [unit.model_dump() for unit in units]
    carcass_df, panels_df = build_cutlist(unit_dicts)
    return _rows_from_df(carcass_df), _rows_from_df(panels_df)


def _rows_from_df(df: pd.DataFrame) -> list[CutlistRowResponse]:
    rows: list[CutlistRowResponse] = []
    for record in df.to_dict(orient="records"):
        rows.append(
            CutlistRowResponse(
                unit_number=int(record["Unit #"]),
                desc=str(record["Desc"]),
                length=int(record["L"]),
                width=int(record["W"]),
                qty=int(record["Qty"]),
            )
        )
    return rows

