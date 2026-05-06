"""FastAPI application entry point for Soigneur.

Configures the app, mounts static files, sets up Jinja2 templates,
and includes the dashboard router.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.routers.dashboard import router as dashboard_router

app = FastAPI(title="Soigneur")

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

app.include_router(dashboard_router)
