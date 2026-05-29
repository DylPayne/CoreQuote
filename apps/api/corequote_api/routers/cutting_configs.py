from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from corequote_api.authorization import require_permission
from corequote_api.cutting_configs import CuttingConfigConflict, CuttingConfigNotFound, CuttingConfigStore
from corequote_api.schemas import (
    AuthUserResponse,
    CuttingRulesetRequest,
    CuttingRulesetResponse,
    CuttingRulesetSummaryResponse,
    UnitConfigRequest,
    UnitConfigResponse,
)


router = APIRouter(prefix="/cutting", tags=["cutting"])


def get_cutting_config_store() -> CuttingConfigStore:
    return CuttingConfigStore()


CuttingReader = Annotated[AuthUserResponse, Depends(require_permission("cutlists:read"))]
CuttingWriter = Annotated[AuthUserResponse, Depends(require_permission("cutlists:write"))]
StoreDep = Annotated[CuttingConfigStore, Depends(get_cutting_config_store)]


@router.get("/unit-configs", response_model=list[UnitConfigResponse], summary="List visible unit configs")
def list_unit_configs(
    current_user: CuttingReader,
    store: StoreDep,
    include_archived: bool = False,
) -> list[UnitConfigResponse]:
    return [
        UnitConfigResponse.model_validate(row)
        for row in store.list_unit_configs(current_user.company_id, include_archived=include_archived)
    ]


@router.get("/unit-configs/{unit_config_id}", response_model=UnitConfigResponse, summary="Get a unit config")
def get_unit_config(
    unit_config_id: str,
    current_user: CuttingReader,
    store: StoreDep,
) -> UnitConfigResponse:
    return _get_response(UnitConfigResponse, store.get_unit_config, current_user.company_id, unit_config_id)


@router.post(
    "/unit-configs",
    response_model=UnitConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company unit config",
)
def create_unit_config(
    payload: UnitConfigRequest,
    current_user: CuttingWriter,
    store: StoreDep,
) -> UnitConfigResponse:
    return _create_response(UnitConfigResponse, store.create_unit_config, current_user.company_id, payload)


@router.patch("/unit-configs/{unit_config_id}", response_model=UnitConfigResponse, summary="Update a company unit config")
def update_unit_config(
    unit_config_id: str,
    payload: UnitConfigRequest,
    current_user: CuttingWriter,
    store: StoreDep,
) -> UnitConfigResponse:
    return _update_response(UnitConfigResponse, store.update_unit_config, current_user.company_id, unit_config_id, payload)


@router.get("/rulesets", response_model=list[CuttingRulesetSummaryResponse], summary="List visible cutting rulesets")
def list_rulesets(
    current_user: CuttingReader,
    store: StoreDep,
    unit_type_key: str | None = None,
    include_archived: bool = False,
) -> list[CuttingRulesetSummaryResponse]:
    return [
        CuttingRulesetSummaryResponse.model_validate(row)
        for row in store.list_rulesets(
            current_user.company_id,
            unit_type_key=unit_type_key,
            include_archived=include_archived,
        )
    ]


@router.post(
    "/rulesets",
    response_model=CuttingRulesetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company cutting ruleset",
)
def create_ruleset(
    payload: CuttingRulesetRequest,
    current_user: CuttingWriter,
    store: StoreDep,
) -> CuttingRulesetResponse:
    return _create_response(CuttingRulesetResponse, store.create_ruleset, current_user.company_id, payload)


@router.get("/rulesets/{ruleset_id}", response_model=CuttingRulesetResponse, summary="Get a cutting ruleset")
def get_ruleset(
    ruleset_id: str,
    current_user: CuttingReader,
    store: StoreDep,
) -> CuttingRulesetResponse:
    return _get_response(CuttingRulesetResponse, store.get_ruleset, current_user.company_id, ruleset_id)


@router.patch("/rulesets/{ruleset_id}", response_model=CuttingRulesetResponse, summary="Update a company cutting ruleset")
def update_ruleset(
    ruleset_id: str,
    payload: CuttingRulesetRequest,
    current_user: CuttingWriter,
    store: StoreDep,
) -> CuttingRulesetResponse:
    return _update_response(CuttingRulesetResponse, store.update_ruleset, current_user.company_id, ruleset_id, payload)


def _payload(payload: Any) -> dict[str, Any]:
    return payload.model_dump()


def _create_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except CuttingConfigConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CuttingConfigNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc) or "Cutting config not found") from exc
    return response_model.model_validate(row)


def _get_response(response_model, callback, *args):
    try:
        row = callback(*args)
    except CuttingConfigNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc) or "Cutting config not found") from exc
    return response_model.model_validate(row)


def _update_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except CuttingConfigConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CuttingConfigNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc) or "Cutting config not found") from exc
    return response_model.model_validate(row)
