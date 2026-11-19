"""HTTP event-bus implementation for local development.

This is a drop-in alternative to RabbitMQ for environments without a container
runtime. It keeps the same broker interface used by the outbox dispatcher and
consumers, and relies on a tiny persistent relay (SQLite-backed) so separate
processes can exchange events. Production deployments use RabbitMQ.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable, Optional

import httpx

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any], Optional[str]], Awaitable[None]]


class HttpMessageBroker:
    supports_dead_letter = False

    def __init__(self, relay_url: str, exchange_name: str) -> None:
        self.relay_url = relay_url.rstrip("/")
        self.exchange_name = exchange_name
        self._client: Optional[httpx.AsyncClient] = None
        self._tasks: list[asyncio.Task] = []

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(base_url=self.relay_url, timeout=30.0)
        response = await self._client.get("/health")
        response.raise_for_status()
        logger.info(
            "connected to http event relay exchange=%s", self.exchange_name,
            extra={"extra_fields": {"exchange": self.exchange_name}},
        )

    async def connect_with_retry(self, delay_seconds: float = 2.0) -> None:
        while True:
            try:
                await self.connect()
                return
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception as exc:  # noqa: BLE001 - wait for relay startup
                logger.warning(
                    "event relay connection failed (%s), retrying: %s",
                    self.relay_url,
                    exc,
                )
                await asyncio.sleep(delay_seconds)

    async def publish(
        self,
        routing_key: str,
        payload: dict[str, Any],
        event_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        if self._client is None:
            await self.connect()
        assert self._client is not None
        response = await self._client.post(
            "/publish",
            json={
                "exchange": self.exchange_name,
                "routing_key": routing_key,
                "payload": payload,
                "message_id": event_id,
                "correlation_id": correlation_id,
            },
        )
        response.raise_for_status()

    async def consume(
        self,
        queue_name: str,
        routing_keys: Iterable[str],
        handler: Handler,
        queue_arguments: Optional[dict[str, Any]] = None,
    ) -> None:
        if self._client is None:
            await self.connect()
        keys = set(routing_keys)

        async def loop() -> None:
            assert self._client is not None
            last_id = 0
            while True:
                try:
                    response = await self._client.get(
                        "/poll",
                        params={
                            "exchange": self.exchange_name,
                            "after_id": last_id,
                            "limit": 100,
                        },
                    )
                    response.raise_for_status()
                    for event in response.json().get("events", []):
                        last_id = max(last_id, int(event["id"]))
                        if event["routing_key"] not in keys:
                            continue
                        try:
                            await handler(
                                event["payload"], event.get("message_id")
                            )
                        except Exception:  # noqa: BLE001 - keep polling
                            logger.exception(
                                "handler failed for event id=%s", event["id"]
                            )
                    await asyncio.sleep(0.25)
                except asyncio.CancelledError:  # pragma: no cover
                    raise
                except Exception as exc:  # noqa: BLE001 - relay hiccup
                    logger.warning("event relay poll failed: %s", exc)
                    await asyncio.sleep(1.0)

        self._tasks.append(asyncio.create_task(loop()))
        logger.info(
            "consuming http queue=%s keys=%s", queue_name, sorted(keys)
        )

    async def close(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
