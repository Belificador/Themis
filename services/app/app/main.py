from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import auth, dashboard, notifications, products, rates, reports, sales, stock
from .security import SecurityHeadersMiddleware, RateLimitMiddleware, limiter, rate_limit_exceeded_handler
from .service import get_current_user

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
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

if settings.cors_origins or settings.cors_origin_regex:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )
app.include_router(auth.router)
app.include_router(
    products.router, dependencies=[Depends(get_current_user)]
)
app.include_router(
    sales.router, dependencies=[Depends(get_current_user)]
)
app.include_router(
    stock.router, dependencies=[Depends(get_current_user)]
)
app.include_router(
    notifications.router, dependencies=[Depends(get_current_user)]
)
app.include_router(
    dashboard.router, dependencies=[Depends(get_current_user)]
)
app.include_router(rates.router, dependencies=[Depends(get_current_user)])
app.include_router(reports.router, dependencies=[Depends(get_current_user)])


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
