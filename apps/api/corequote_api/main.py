from __future__ import annotations

from fastapi import FastAPI

from corequote_api.routers import auth, companies, cutlists, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="CoreQuote API",
        version="0.1.0",
        description="API layer for CoreQuote quoting and cutlist workflows.",
    )
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(companies.router, prefix="/api/v1")
    app.include_router(cutlists.router, prefix="/api/v1")
    return app


app = create_app()
