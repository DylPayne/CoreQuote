from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from corequote_api.authorization import require_permission
from corequote_api.projects_quotes import (
    WorkspaceConflict,
    WorkspaceNotFound,
    WorkspaceStore,
    WorkspaceValidationError,
)
from corequote_api.schemas import (
    AuthUserResponse,
    ProjectRequest,
    ProjectResponse,
    QuoteRequest,
    QuoteResponse,
    QuoteUnitRequest,
    QuoteUnitResponse,
)


router = APIRouter(tags=["projects", "quotes"])


def get_workspace_store() -> WorkspaceStore:
    return WorkspaceStore()


ProjectsReader = Annotated[AuthUserResponse, Depends(require_permission("projects:read"))]
ProjectsWriter = Annotated[AuthUserResponse, Depends(require_permission("projects:write"))]
QuotesReader = Annotated[AuthUserResponse, Depends(require_permission("quotes:read"))]
QuotesWriter = Annotated[AuthUserResponse, Depends(require_permission("quotes:write"))]
StoreDep = Annotated[WorkspaceStore, Depends(get_workspace_store)]


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
    return [QuoteResponse.model_validate(row) for row in rows]


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
    return QuoteResponse.model_validate(row)


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
    return response_model.model_validate(row)


def _get_response(response_model, callback, *args):
    try:
        row = callback(*args)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return response_model.model_validate(row)


def _update_response(response_model, callback, *args):
    try:
        row = callback(*args[:-1], _payload(args[-1]))
    except WorkspaceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return response_model.model_validate(row)


def _delete_response(callback, *args) -> Response:
    try:
        callback(*args)
    except WorkspaceConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
