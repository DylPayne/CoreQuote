from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from corequote_api.routers import auth, companies, cutlists, health, libraries


DEFAULT_CORS_ORIGIN_REGEX = r"^http://(localhost|127\.0\.0\.1):\d+$"


def _cors_origins() -> list[str]:
    raw_origins = os.environ.get("COREQUOTE_CORS_ORIGINS", "")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="CoreQuote API",
        version="0.1.0",
        description="API layer for CoreQuote quoting and cutlist workflows.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_headers=["Accept", "Authorization", "Content-Type"],
        allow_methods=["DELETE", "GET", "OPTIONS", "PATCH", "POST"],
        allow_origin_regex=os.environ.get("COREQUOTE_CORS_ORIGIN_REGEX") or DEFAULT_CORS_ORIGIN_REGEX,
        allow_origins=_cors_origins(),
    )
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(companies.router, prefix="/api/v1")
    app.include_router(cutlists.router, prefix="/api/v1")
    app.include_router(libraries.router, prefix="/api/v1")
    return app


app = create_app()
