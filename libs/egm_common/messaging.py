"""Thin async wrapper around aio-pika used by every service.

Each service owns its own exchanges/queues. The wrapper only provides delivery
mechanics (persistent publishes, manual acks, prefetch and reconnect); it does
not encode any domain knowledge.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractExchange, AbstractQueue, AbstractRobustConnection

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any], Optional[str]], Awaitable[None]]


class MessageBroker:
    def __init__(
        self,
        url: str,
        exchange_name: str,
        exchange_type: ExchangeType = ExchangeType.TOPIC,
    ) -> None:
        self.url = url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel = None
        self._exchange: Optional[AbstractExchange] = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return bool(
            self._connection is not None
            and not self._connection.is_closed
            and self._exchange is not None
        )

    @property
    def channel(self):
        return self._channel

    @property
    def connection(self) -> Optional[AbstractRobustConnection]:
        return self._connection

    async def connect(self) -> None:
        async with self._lock:
            if self.is_connected:
                return
            self._connection = await aio_pika.connect_robust(self.url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=20)
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name, self.exchange_type, durable=True
            )
            logger.info(
                "connected to rabbitmq exchange=%s", self.exchange_name,
                extra={"extra_fields": {"exchange": self.exchange_name}},
            )

    async def connect_with_retry(self, delay_seconds: float = 2.0) -> None:
        while True:
            try:
                await self.connect()
                return
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception as exc:  # noqa: BLE001 - retry any connection error
                logger.warning(
                    "rabbitmq connection failed, retrying: %s", exc,
                    extra={"extra_fields": {"exchange": self.exchange_name}},
                )
                await asyncio.sleep(delay_seconds)

    async def publish(
        self,
        routing_key: str,
        payload: dict[str, Any],
        event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        if not self.is_connected:
            await self.connect()
        assert self._exchange is not None
        body = json.dumps(payload, default=str).encode("utf-8")
        message = Message(
            body=body,
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event_id,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
        )
        await self._exchange.publish(message, routing_key=routing_key)

    async def consume(
        self,
        queue_name: str,
        routing_keys: Iterable[str],
        handler: Handler,
        queue_arguments: Optional[dict[str, Any]] = None,
    ) -> AbstractQueue:
        if not self.is_connected:
            await self.connect()
        assert self._channel is not None and self._exchange is not None
        queue = await self._channel.declare_queue(
            queue_name, durable=True, arguments=queue_arguments
        )
        for routing_key in routing_keys:
            await queue.bind(self._exchange, routing_key=routing_key)

        async def _on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            message_id = message.message_id
            try:
                payload = json.loads(message.body.decode("utf-8"))
            except Exception:  # noqa: BLE001 - malformed payloads must not loop
                logger.exception("dropping malformed message id=%s", message_id)
                await message.reject(requeue=False)
                return
            try:
                await handler(payload, message_id)
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception:  # noqa: BLE001 - handler must not kill the consumer
                logger.exception("handler failed for message id=%s", message_id)
                await message.reject(requeue=False)
            else:
                await message.ack()

        await queue.consume(_on_message)
        logger.info(
            "consuming queue=%s keys=%s", queue_name, list(routing_keys),
            extra={"extra_fields": {"queue": queue_name}},
        )
        return queue

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None
        self._exchange = None
