from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from aio_pika import ExchangeType
from egm_common.broker import create_broker
from egm_common.db import init_models
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .consumer import handle_stock_event
from .db import Base, engine
from .routers import notifications

logger = logging.getLogger(__name__)

DEAD_LETTER_EXCHANGE = "notification.dlx"
DEAD_LETTER_QUEUE = "notification.dead_letter"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.log_level)
    await init_models(engine, Base)

    broker = create_broker(
        settings.stock_exchange, rabbitmq_url=settings.rabbitmq_url
    )
    await broker.connect_with_retry()

    queue_arguments = None
    if broker.supports_dead_letter:
        channel = broker.channel
        assert channel is not None
        dead_letter_exchange = await channel.declare_exchange(
            DEAD_LETTER_EXCHANGE, ExchangeType.DIRECT, durable=True
        )
        dead_letter_queue = await channel.declare_queue(
            DEAD_LETTER_QUEUE, durable=True
        )
        await dead_letter_queue.bind(
            dead_letter_exchange, routing_key=DEAD_LETTER_QUEUE
        )
        queue_arguments = {
            "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
            "x-dead-letter-routing-key": DEAD_LETTER_QUEUE,
        }

    await broker.consume(
        settings.notification_queue,
        ["stock.depleted", "stock.replenished"],
        handle_stock_event,
        queue_arguments=queue_arguments,
    )

    app.state.broker = broker
    logger.info("notification-service started")
    try:
        yield
    finally:
        await broker.close()
        await engine.dispose()


app = FastAPI(
    title="Themis Notification Service", version="0.1.0", lifespan=lifespan
)
app.add_middleware(CorrelationIdMiddleware)
app.include_router(notifications.router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    database_ok = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001
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
            "channels": {
                "telegram": "configured"
                if settings.telegram_bot_token and settings.telegram_chat_id
                else "dry_run",
                "whatsapp": "configured"
                if settings.whatsapp_token
                and settings.whatsapp_phone_number_id
                and settings.whatsapp_recipient
                else "dry_run",
            },
        },
        status_code=200 if status == "ok" else 503,
    )
