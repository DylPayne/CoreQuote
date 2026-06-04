from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from corequote_api.authorization import require_permission
from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.schemas import AuthUserResponse, CutlistPreviewRequest, CutlistPreviewResponse
from corequote_api.services import BoardThicknessLookup, _load_board_thicknesses, preview_cutlist


router = APIRouter(prefix="/cutlists", tags=["cutlists"])


def get_cutlist_runtime_service() -> CutlistRuntimeService:
    return CutlistRuntimeService()


def get_board_thickness_lookup() -> BoardThicknessLookup:
    return _load_board_thicknesses


@router.post("/preview", response_model=CutlistPreviewResponse)
def create_cutlist_preview(
    payload: CutlistPreviewRequest,
    current_user: Annotated[AuthUserResponse, Depends(require_permission("cutlists:preview"))],
    runtime_service: Annotated[CutlistRuntimeService, Depends(get_cutlist_runtime_service)],
    board_thickness_lookup: Annotated[BoardThicknessLookup, Depends(get_board_thickness_lookup)],
) -> CutlistPreviewResponse:
    try:
        result = preview_cutlist(
            payload.units,
            company_id=current_user.company_id,
            runtime_service=runtime_service,
            board_thickness_lookup=board_thickness_lookup,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CutlistPreviewResponse.model_validate(result)
