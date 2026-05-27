from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status

from corequote_api.database import DatabaseHealth, check_database_connection
from corequote_api.schemas import DatabaseHealthResponse, HealthResponse


router = APIRouter(prefix="/health", tags=["health"])
DatabaseChecker = Callable[[], DatabaseHealth]


def get_database_checker() -> DatabaseChecker:
    return check_database_connection


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok", service="corequote-api")


@router.get("/ready", response_model=HealthResponse)
def ready() -> HealthResponse:
    return HealthResponse(status="ok", service="corequote-api")


@router.get("/db", response_model=DatabaseHealthResponse)
def database(check_database: DatabaseChecker = Depends(get_database_checker)) -> DatabaseHealthResponse:
    result = check_database()
    if not result.ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "service": "corequote-api",
                "database": result.database,
                "message": result.message or "Database connection failed",
            },
        )

    return DatabaseHealthResponse(
        status="ok",
        service="corequote-api",
        database=result.database,
    )
