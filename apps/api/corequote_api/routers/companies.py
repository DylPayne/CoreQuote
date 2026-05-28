from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from corequote_api.authorization import require_permission
from corequote_api.companies import CompanyConflict, CompanyNotFound, CompanyStore
from corequote_api.schemas import (
    AuthUserResponse,
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
)


router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_store() -> CompanyStore:
    return CompanyStore()


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
    responses={
        201: {"description": "Company was created."},
        401: {"description": "The bearer token is missing, expired, revoked, or invalid."},
        403: {"description": "The current user cannot create companies."},
        409: {"description": "The generated company slug conflicts with an existing company."},
    },
)
def create_company(
    payload: CompanyCreateRequest,
    current_user: Annotated[AuthUserResponse, Depends(require_permission("companies:create"))],
    store: Annotated[CompanyStore, Depends(get_company_store)],
) -> CompanyResponse:
    try:
        company = store.create_company(name=payload.name)
    except CompanyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CompanyResponse.model_validate(company)


@router.get(
    "",
    response_model=list[CompanyResponse],
    summary="List companies",
    responses={
        200: {"description": "Companies visible to the current user."},
        401: {"description": "The bearer token is missing, expired, revoked, or invalid."},
    },
)
def list_companies(
    current_user: Annotated[AuthUserResponse, Depends(require_permission("companies:read"))],
    store: Annotated[CompanyStore, Depends(get_company_store)],
) -> list[CompanyResponse]:
    try:
        company = store.get_company(current_user.company_id)
    except CompanyNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found") from exc
    return [CompanyResponse.model_validate(company)]


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Get a company",
    responses={
        200: {"description": "Company was found."},
        401: {"description": "The bearer token is missing, expired, revoked, or invalid."},
        404: {"description": "Company was not found."},
    },
)
def get_company(
    company_id: str,
    current_user: Annotated[AuthUserResponse, Depends(require_permission("companies:read"))],
    store: Annotated[CompanyStore, Depends(get_company_store)],
) -> CompanyResponse:
    _require_visible_company(company_id, current_user)
    try:
        company = store.get_company(company_id)
    except CompanyNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found") from exc
    return CompanyResponse.model_validate(company)


@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
    responses={
        200: {"description": "Company was updated."},
        401: {"description": "The bearer token is missing, expired, revoked, or invalid."},
        403: {"description": "The current user cannot update this company."},
        404: {"description": "Company was not found."},
    },
)
def update_company(
    company_id: str,
    payload: CompanyUpdateRequest,
    current_user: Annotated[AuthUserResponse, Depends(require_permission("companies:update"))],
    store: Annotated[CompanyStore, Depends(get_company_store)],
) -> CompanyResponse:
    _require_visible_company(company_id, current_user)
    try:
        company = store.update_company(company_id=company_id, name=payload.name)
    except CompanyNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found") from exc
    return CompanyResponse.model_validate(company)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
    responses={
        204: {"description": "Company was deleted."},
        401: {"description": "The bearer token is missing, expired, revoked, or invalid."},
        403: {"description": "The current user cannot delete this company."},
        404: {"description": "Company was not found."},
        409: {"description": "Company still has related records."},
    },
)
def delete_company(
    company_id: str,
    current_user: Annotated[AuthUserResponse, Depends(require_permission("companies:delete"))],
    store: Annotated[CompanyStore, Depends(get_company_store)],
) -> Response:
    _require_visible_company(company_id, current_user)
    try:
        store.delete_company(company_id)
    except CompanyNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found") from exc
    except CompanyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_visible_company(company_id: str, current_user: AuthUserResponse) -> None:
    if current_user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
