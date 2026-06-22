from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from corequote_api.authorization import require_permission
from corequote_api.cutting_runtime import CutlistRuntimeService
from corequote_api.projects_quotes import (
    WorkspaceConflict,
    WorkspaceNotFound,
    WorkspaceStore,
    WorkspaceValidationError,
)
from corequote_api.schemas import (
    AuthUserResponse,
    PricingSettingsRequest,
    ProjectPricingResponse,
    ProjectPricingSettingsResponse,
    ProjectRequest,
    ProjectResponse,
    QuoteCustomPanelsRequest,
    QuoteCustomPanelsResponse,
    QuoteCuttingListResponse,
    QuoteExtrasRequest,
    QuoteExtrasResponse,
    QuoteOutputReviewResponse,
    QuotePricingSettingsResponse,
    QuoteProductionHandoffResponse,
    QuoteReadinessResponse,
    QuoteRequest,
    QuoteResponse,
    QuoteStatusRequest,
    QuoteUnitBulkApplyRequest,
    QuoteUnitBulkSaveRequest,
    QuoteUnitReorderRequest,
    QuoteUnitRequest,
    QuoteUnitResponse,
)


router = APIRouter(tags=["projects", "quotes"])


def get_workspace_store() -> WorkspaceStore:
    return WorkspaceStore()


def get_cutlist_runtime_service() -> CutlistRuntimeService:
    return CutlistRuntimeService()


ProjectsReader = Annotated[AuthUserResponse, Depends(require_permission("projects:read"))]
ProjectsWriter = Annotated[AuthUserResponse, Depends(require_permission("projects:write"))]
QuotesReader = Annotated[AuthUserResponse, Depends(require_permission("quotes:read"))]
QuotesWriter = Annotated[AuthUserResponse, Depends(require_permission("quotes:write"))]
PricingReader = Annotated[AuthUserResponse, Depends(require_permission("pricing:read"))]
PricingWriter = Annotated[AuthUserResponse, Depends(require_permission("pricing:update"))]
ProductionReader = Annotated[AuthUserResponse, Depends(require_permission("production:read"))]
StoreDep = Annotated[WorkspaceStore, Depends(get_workspace_store)]
CutlistRuntimeDep = Annotated[CutlistRuntimeService, Depends(get_cutlist_runtime_service)]
INTERNAL_QUOTE_FIELDS = {"hardware_catalog_snapshot"}


def _quote_response(row: dict[str, Any]) -> QuoteResponse:
    return QuoteResponse.model_validate(_public_quote_payload(row))


def _public_quote_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(row).items() if key not in INTERNAL_QUOTE_FIELDS}


@router.get("/projects", response_model=list[ProjectResponse], summary="List projects")
def list_projects(
    current_user: ProjectsReader,
    store: StoreDep,
    search: str | None = None,
) -> list[ProjectResponse]:
    return [ProjectResponse.model_validate(row) for row in store.list_projects(current_user.company_id, search=search)]


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Create project")
def create_project(
    payload: ProjectRequest,
    current_user: ProjectsWriter,
    store: StoreDep,
) -> ProjectResponse:
    return _create_response(ProjectResponse, store.create_project, current_user.company_id, payload)


@router.get("/projects/{project_id}", response_model=ProjectResponse, summary="Get project")
def get_project(
    project_id: str,
    current_user: ProjectsReader,
    store: StoreDep,
) -> ProjectResponse:
    return _get_response(ProjectResponse, store.get_project, current_user.company_id, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectResponse, summary="Update project")
def update_project(
    project_id: str,
    payload: ProjectRequest,
    current_user: ProjectsWriter,
    store: StoreDep,
) -> ProjectResponse:
    return _update_response(ProjectResponse, store.update_project, current_user.company_id, project_id, payload)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete project")
def delete_project(
    project_id: str,
    current_user: ProjectsWriter,
    store: StoreDep,
) -> Response:
    return _delete_response(store.delete_project, current_user.company_id, project_id)


@router.get("/projects/{project_id}/quotes", response_model=list[QuoteResponse], summary="List project quotes")
def list_quotes(
    project_id: str,
    current_user: QuotesReader,
    store: StoreDep,
) -> list[QuoteResponse]:
    try:
        rows = store.list_quotes(current_user.company_id, project_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    return [_quote_response(row) for row in rows]


@router.post(
    "/projects/{project_id}/quotes",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quote",
)
def create_quote(
    project_id: str,
    payload: QuoteRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteResponse:
    try:
        row = store.create_quote(current_user.company_id, project_id, _payload(payload))
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _quote_response(row)


@router.get("/quotes/{quote_id}", response_model=QuoteResponse, summary="Get quote")
def get_quote(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
) -> QuoteResponse:
    return _get_response(QuoteResponse, store.get_quote, current_user.company_id, quote_id)


@router.patch("/quotes/{quote_id}", response_model=QuoteResponse, summary="Update quote")
def update_quote(
    quote_id: str,
    payload: QuoteRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteResponse:
    return _update_response(QuoteResponse, store.update_quote, current_user.company_id, quote_id, payload)


@router.patch("/quotes/{quote_id}/status", response_model=QuoteResponse, summary="Update quote status")
def update_quote_status(
    quote_id: str,
    payload: QuoteStatusRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteResponse:
    try:
        row = store.update_quote_status(current_user.company_id, quote_id, payload.status)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _quote_response(row)


@router.post(
    "/quotes/{quote_id}/duplicate",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate quote",
)
def duplicate_quote(
    quote_id: str,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteResponse:
    try:
        row = store.duplicate_quote(current_user.company_id, quote_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _quote_response(row)


@router.post(
    "/quotes/{quote_id}/revisions",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quote revision",
)
def create_quote_revision(
    quote_id: str,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteResponse:
    try:
        row = store.create_quote_revision(current_user.company_id, quote_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _quote_response(row)


@router.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete quote")
def delete_quote(
    quote_id: str,
    current_user: QuotesWriter,
    store: StoreDep,
) -> Response:
    return _delete_response(store.delete_quote, current_user.company_id, quote_id)


@router.get("/quotes/{quote_id}/units", response_model=list[QuoteUnitResponse], summary="List quote units")
def list_units(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
) -> list[QuoteUnitResponse]:
    try:
        rows = store.list_units(current_user.company_id, quote_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    return [QuoteUnitResponse.model_validate(row) for row in rows]


@router.post(
    "/quotes/{quote_id}/units",
    response_model=QuoteUnitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create quote unit",
)
def create_unit(
    quote_id: str,
    payload: QuoteUnitRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteUnitResponse:
    try:
        row = store.create_unit(current_user.company_id, quote_id, _payload(payload))
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return QuoteUnitResponse.model_validate(row)


@router.post(
    "/quotes/{quote_id}/units/{unit_id}/duplicate",
    response_model=QuoteUnitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate quote unit",
)
def duplicate_unit(
    quote_id: str,
    unit_id: str,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteUnitResponse:
    try:
        row = store.duplicate_unit(current_user.company_id, quote_id, unit_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return QuoteUnitResponse.model_validate(row)


@router.put(
    "/quotes/{quote_id}/units/bulk",
    response_model=list[QuoteUnitResponse],
    summary="Bulk save quote units",
)
def bulk_save_units(
    quote_id: str,
    payload: QuoteUnitBulkSaveRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> list[QuoteUnitResponse]:
    try:
        rows = store.bulk_save_units(
            current_user.company_id,
            quote_id,
            [row.model_dump() for row in payload.units],
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return [QuoteUnitResponse.model_validate(row) for row in rows]


@router.patch(
    "/quotes/{quote_id}/units/bulk-apply",
    response_model=list[QuoteUnitResponse],
    summary="Bulk apply selected unit overrides",
)
def bulk_apply_unit_overrides(
    quote_id: str,
    payload: QuoteUnitBulkApplyRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> list[QuoteUnitResponse]:
    try:
        rows = store.bulk_apply_unit_overrides(
            current_user.company_id,
            quote_id,
            payload.model_dump(exclude_unset=True),
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return [QuoteUnitResponse.model_validate(row) for row in rows]


@router.put(
    "/quotes/{quote_id}/units/reorder",
    response_model=list[QuoteUnitResponse],
    summary="Reorder quote units",
)
def reorder_units(
    quote_id: str,
    payload: QuoteUnitReorderRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> list[QuoteUnitResponse]:
    try:
        rows = store.reorder_units(current_user.company_id, quote_id, payload.unit_ids)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return [QuoteUnitResponse.model_validate(row) for row in rows]


@router.patch(
    "/quotes/{quote_id}/units/{unit_id}",
    response_model=QuoteUnitResponse,
    summary="Update quote unit",
)
def update_unit(
    quote_id: str,
    unit_id: str,
    payload: QuoteUnitRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteUnitResponse:
    try:
        row = store.update_unit(current_user.company_id, quote_id, unit_id, _payload(payload))
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return QuoteUnitResponse.model_validate(row)


@router.delete(
    "/quotes/{quote_id}/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete quote unit",
)
def delete_unit(
    quote_id: str,
    unit_id: str,
    current_user: QuotesWriter,
    store: StoreDep,
) -> Response:
    try:
        store.delete_unit(current_user.company_id, quote_id, unit_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/quotes/{quote_id}/cutting-list", response_model=QuoteCuttingListResponse, summary="Build quote cutting list")
def get_quote_cutting_list(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> QuoteCuttingListResponse:
    try:
        payload = store.get_quote_cutting_list(
            current_user.company_id,
            quote_id,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteCuttingListResponse.model_validate({"quote_id": quote_id, **payload})


@router.get("/quotes/{quote_id}/readiness", response_model=QuoteReadinessResponse, summary="Check quote readiness")
def get_quote_readiness(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> QuoteReadinessResponse:
    try:
        payload = store.get_quote_readiness(
            current_user.company_id,
            quote_id,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    return QuoteReadinessResponse.model_validate(payload)


@router.get(
    "/quotes/{quote_id}/output-review",
    response_model=QuoteOutputReviewResponse,
    summary="Review quote outputs",
)
def get_quote_output_review(
    quote_id: str,
    current_user: PricingReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> QuoteOutputReviewResponse:
    try:
        payload = store.get_quote_output_review(
            current_user.company_id,
            quote_id,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteOutputReviewResponse.model_validate(payload)


@router.get(
    "/quotes/{quote_id}/production-handoff",
    response_model=QuoteProductionHandoffResponse,
    summary="Build quote production handoff",
)
def get_quote_production_handoff(
    quote_id: str,
    current_user: ProductionReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> QuoteProductionHandoffResponse:
    try:
        payload = store.get_quote_production_handoff(
            current_user.company_id,
            quote_id,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteProductionHandoffResponse.model_validate(payload)


@router.get(
    "/quotes/{quote_id}/production-handoff.csv",
    summary="Download production handoff CSV",
    responses={
        200: {
            "description": "Workshop-facing production cutting schedule CSV.",
            "content": {"text/csv": {}},
        },
        404: {"description": "Quote was not found or is not visible to the current company."},
        422: {"description": "Quote has no production rows to export."},
    },
)
def download_production_handoff_csv(
    quote_id: str,
    current_user: ProductionReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> Response:
    return _download_production_handoff_export(
        quote_id=quote_id,
        current_user=current_user,
        store=store,
        runtime_service=runtime_service,
        export_format="csv",
        media_type="text/csv",
    )


@router.get(
    "/quotes/{quote_id}/production-handoff.xlsx",
    summary="Download production handoff XLSX",
    responses={
        200: {
            "description": "Workshop-facing production handoff workbook.",
            "content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
        },
        404: {"description": "Quote was not found or is not visible to the current company."},
        422: {"description": "Quote has no production rows to export."},
    },
)
def download_production_handoff_xlsx(
    quote_id: str,
    current_user: ProductionReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> Response:
    return _download_production_handoff_export(
        quote_id=quote_id,
        current_user=current_user,
        store=store,
        runtime_service=runtime_service,
        export_format="xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _download_production_handoff_export(
    *,
    quote_id: str,
    current_user: AuthUserResponse,
    store: WorkspaceStore,
    runtime_service: CutlistRuntimeService,
    export_format: str,
    media_type: str,
) -> Response:
    try:
        payload = store.generate_production_handoff_export(
            current_user.company_id,
            quote_id,
            export_format=export_format,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return Response(
        content=payload["content"],
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
    )


@router.get(
    "/quotes/{quote_id}/customer-quote.pdf",
    summary="Download customer quote PDF",
    responses={
        200: {
            "description": "Customer-facing quote PDF.",
            "content": {"application/pdf": {}},
        },
        404: {"description": "Quote was not found or is not visible to the current company."},
        422: {"description": "Quote readiness or pricing blocks customer PDF generation."},
    },
)
def download_customer_quote_pdf(
    quote_id: str,
    current_user: PricingReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> Response:
    try:
        payload = store.generate_customer_quote_pdf(
            current_user.company_id,
            quote_id,
            company={
                "name": current_user.company_name,
                "contact_name": current_user.name,
                "contact_email": current_user.email,
            },
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return Response(
        content=payload["content"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
    )


@router.get(
    "/quotes/{quote_id}/workshop-schedule.pdf",
    summary="Download workshop cutting schedule PDF",
    responses={
        200: {
            "description": "Workshop-facing cutting schedule PDF.",
            "content": {"application/pdf": {}},
        },
        404: {"description": "Quote was not found or is not visible to the current company."},
        422: {"description": "Quote has no cutting schedule rows to export."},
    },
)
def download_workshop_schedule_pdf(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> Response:
    try:
        payload = store.generate_workshop_schedule_pdf(
            current_user.company_id,
            quote_id,
            company={
                "name": current_user.company_name,
                "contact_name": current_user.name,
                "contact_email": current_user.email,
            },
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return Response(
        content=payload["content"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
    )


@router.get("/quotes/{quote_id}/extras", response_model=QuoteExtrasResponse, summary="List selected quote extras")
def list_quote_extras(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
) -> QuoteExtrasResponse:
    try:
        rows = store.list_quote_extras(current_user.company_id, quote_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    return QuoteExtrasResponse.model_validate({"quote_id": quote_id, "items": rows})


@router.put("/quotes/{quote_id}/extras", response_model=QuoteExtrasResponse, summary="Replace selected quote extras")
def replace_quote_extras(
    quote_id: str,
    payload: QuoteExtrasRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteExtrasResponse:
    try:
        rows = store.replace_quote_extras(
            current_user.company_id,
            quote_id,
            [item.model_dump() for item in payload.items],
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteExtrasResponse.model_validate({"quote_id": quote_id, "items": rows})


@router.get(
    "/quotes/{quote_id}/custom-panels",
    response_model=QuoteCustomPanelsResponse,
    summary="Get quote custom panel configuration",
)
def get_quote_custom_panels(
    quote_id: str,
    current_user: QuotesReader,
    store: StoreDep,
) -> QuoteCustomPanelsResponse:
    try:
        payload = store.get_quote_custom_panels(current_user.company_id, quote_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteCustomPanelsResponse.model_validate(payload)


@router.put(
    "/quotes/{quote_id}/custom-panels",
    response_model=QuoteCustomPanelsResponse,
    summary="Replace quote custom panel configuration",
)
def replace_quote_custom_panels(
    quote_id: str,
    payload: QuoteCustomPanelsRequest,
    current_user: QuotesWriter,
    store: StoreDep,
) -> QuoteCustomPanelsResponse:
    try:
        result = store.replace_quote_custom_panels(current_user.company_id, quote_id, _payload(payload))
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return QuoteCustomPanelsResponse.model_validate(result)


@router.get("/projects/{project_id}/pricing", response_model=ProjectPricingResponse, summary="Build project pricing summary")
def get_project_pricing(
    project_id: str,
    current_user: PricingReader,
    store: StoreDep,
    runtime_service: CutlistRuntimeDep,
) -> ProjectPricingResponse:
    try:
        payload = store.get_project_pricing(
            current_user.company_id,
            project_id,
            runtime_service=runtime_service,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ProjectPricingResponse.model_validate(payload)


@router.get(
    "/projects/{project_id}/pricing-settings",
    response_model=ProjectPricingSettingsResponse,
    summary="Get project pricing defaults",
)
def get_project_pricing_settings(
    project_id: str,
    current_user: PricingReader,
    store: StoreDep,
) -> ProjectPricingSettingsResponse:
    return _get_response(ProjectPricingSettingsResponse, store.get_project_pricing_settings, current_user.company_id, project_id)


@router.patch(
    "/projects/{project_id}/pricing-settings",
    response_model=ProjectPricingSettingsResponse,
    summary="Update project pricing defaults",
)
def update_project_pricing_settings(
    project_id: str,
    payload: PricingSettingsRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> ProjectPricingSettingsResponse:
    try:
        row = store.update_project_pricing_settings(
            current_user.company_id,
            project_id,
            payload.model_dump(exclude_unset=True),
        )
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
    return ProjectPricingSettingsResponse.model_validate(row)


@router.get(
    "/quotes/{quote_id}/pricing-settings",
    response_model=QuotePricingSettingsResponse,
    summary="Get quote pricing settings",
)
def get_quote_pricing_settings(
    quote_id: str,
    current_user: PricingReader,
    store: StoreDep,
) -> QuotePricingSettingsResponse:
    return _get_response(QuotePricingSettingsResponse, store.get_quote_pricing_settings, current_user.company_id, quote_id)


@router.patch(
    "/quotes/{quote_id}/pricing-settings",
    response_model=QuotePricingSettingsResponse,
    summary="Update quote pricing settings",
)
def update_quote_pricing_settings(
    quote_id: str,
    payload: PricingSettingsRequest,
    current_user: PricingWriter,
    store: StoreDep,
) -> QuotePricingSettingsResponse:
    try:
        row = store.update_quote_pricing_settings(
            current_user.company_id,
            quote_id,
            payload.model_dump(exclude_unset=True),
        )
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found") from exc
    return QuotePricingSettingsResponse.model_validate(row)


def _payload(payload: Any) -> dict[str, Any]:
    return payload.model_dump()


def _create_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _model_response(response_model, row)


def _get_response(response_model, callback, *args):
    try:
        row = callback(*args)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _model_response(response_model, row)


def _update_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _model_response(response_model, row)


def _model_response(response_model, row: dict[str, Any]):
    if response_model is QuoteResponse:
        return _quote_response(row)
    return response_model.model_validate(row)


def _delete_response(callback, *args) -> Response:
    try:
        callback(*args)
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
