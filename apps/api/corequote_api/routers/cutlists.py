from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from corequote_api.schemas import CutlistPreviewRequest, CutlistPreviewResponse
from corequote_api.services import preview_cutlist


router = APIRouter(prefix="/cutlists", tags=["cutlists"])


@router.post("/preview", response_model=CutlistPreviewResponse)
def create_cutlist_preview(payload: CutlistPreviewRequest) -> CutlistPreviewResponse:
    try:
        carcass, panels = preview_cutlist(payload.units)
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CutlistPreviewResponse(carcass=carcass, panels=panels)

