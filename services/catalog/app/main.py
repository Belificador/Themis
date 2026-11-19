from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from egm_common.broker import create_broker
from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from egm_common.outbox import run_outbox_dispatcher
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .db import Base, SessionLocal, engine
from .outbox import OutboxEvent
from .routers import products

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    await init_models(engine, Base)

    broker = create_broker(
        settings.products_exchange, rabbitmq_url=settings.rabbitmq_url
    )
    await broker.connect_with_retry()
    dispatcher = asyncio.create_task(
        run_outbox_dispatcher(
            SessionLocal,
            OutboxEvent,
            broker,
            settings.outbox_interval_seconds,
            use_row_locks=not settings.database_url.startswith("sqlite"),
        )
    )
    app.state.broker = broker
    app.state.dispatcher = dispatcher
    logger.info("catalog-service started")
    try:
        yield
    finally:
        dispatcher.cancel()
        await asyncio.gather(dispatcher, return_exceptions=True)
        await broker.close()
        await engine.dispose()


app = FastAPI(title="Themis Catalog Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(products.router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    database_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001 - health endpoint must never raise
        pass
    broker = getattr(app.state, "broker", None)
    broker_ok = bool(broker and broker.is_connected)
    status = "ok" if database_ok and broker_ok else "degraded"
    return JSONResponse(
        {
            "status": status,
            "service": settings.service_name,
            "database": database_ok,
            "broker": broker_ok,
        },
        status_code=200 if status == "ok" else 503,
    )
