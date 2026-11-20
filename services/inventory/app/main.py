from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import stock

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    await init_models(engine, Base, schema=settings.db_schema)
    logger.info("inventory-service started")
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Themis Inventory Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(stock.router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    database_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001
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
