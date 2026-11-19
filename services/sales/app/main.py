from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .db import Base, engine
from .routers import sales

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    await init_models(engine, Base, schema=settings.db_schema)
    logger.info("sales-service started")
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Themis Sales Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(sales.router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    database_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001
        pass
    return JSONResponse(
        {
            "status": "ok" if database_ok else "degraded",
            "service": settings.service_name,
            "database": database_ok,
        },
        status_code=200 if database_ok else 503,
    )
