from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from egm_common.broker import create_broker
from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from egm_common.outbox import run_outbox_dispatcher
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .consumer import handle_product_event
from .db import Base, SessionLocal, engine
from .outbox import OutboxEvent
from .routers import stock

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    await init_models(engine, Base, schema=settings.db_schema)

    products_broker = create_broker(
        settings.products_exchange, rabbitmq_url=settings.rabbitmq_url
    )
    await products_broker.connect_with_retry()
    await products_broker.consume(
        settings.inventory_queue,
        ["product.created", "product.updated", "product.deleted"],
        handle_product_event,
    )

    stock_broker = create_broker(
        settings.stock_exchange, rabbitmq_url=settings.rabbitmq_url
    )
    await stock_broker.connect_with_retry()
    dispatcher = asyncio.create_task(
        run_outbox_dispatcher(
            SessionLocal,
            OutboxEvent,
            stock_broker,
            settings.outbox_interval_seconds,
            use_row_locks=not settings.database_url.startswith("sqlite"),
        )
    )

    app.state.products_broker = products_broker
    app.state.stock_broker = stock_broker
    app.state.dispatcher = dispatcher
    logger.info("inventory-service started")

    try:
        yield
    finally:
        dispatcher.cancel()
        await asyncio.gather(dispatcher, return_exceptions=True)
        await products_broker.close()
        await stock_broker.close()
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
    products_broker = getattr(app.state, "products_broker", None)
    stock_broker = getattr(app.state, "stock_broker", None)
    broker_ok = bool(
        products_broker
        and products_broker.is_connected
        and stock_broker
        and stock_broker.is_connected
    )
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
