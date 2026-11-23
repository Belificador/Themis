from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import dashboard, notifications, products, sales, stock

logger = logging.getLogger(__name__)


def _find_frontend_dist() -> Path | None:
    candidates = []
    env_dir = Path(os.environ["FRONTEND_DIST"]) if os.environ.get("FRONTEND_DIST") else None
    if env_dir:
        candidates.append(env_dir)
    here = Path(__file__).resolve()
    # services/app/app/main.py -> repo root is parents[3]
    for depth in (3, 2, 1):
        if len(here.parents) > depth:
            candidates.append(here.parents[depth] / "frontend" / "dist")
    candidates.append(Path.cwd() / "frontend" / "dist")
    candidates.append(Path.cwd() / "dist")
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


FRONTEND_DIST = _find_frontend_dist()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    await init_models(engine, Base, schema=settings.db_schema)
    logger.info("themis-app started")
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Themis App", version="1.0.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(stock.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    database_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        pass
    status = "ok" if database_ok else "degraded"
    return JSONResponse(
        {
            "status": status,
            "service": settings.service_name,
            "database": database_ok,
        },
        status_code=200 if status == "ok" else 503,
    )


# Sirve el frontend compilado si existe (despliegue de un solo servicio).
if FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "frontend not built"}, status_code=404)
