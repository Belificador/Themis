"""Broker factory: RabbitMQ by default, HTTP relay for local development."""

from __future__ import annotations

import os
from typing import Union

from aio_pika import ExchangeType

from .http_broker import HttpMessageBroker
from .messaging import MessageBroker

Broker = Union[MessageBroker, HttpMessageBroker]


def event_bus_name() -> str:
    return os.getenv("EVENT_BUS", "rabbitmq").strip().lower()


def create_broker(
    exchange_name: str,
    *,
    rabbitmq_url: str,
    exchange_type: ExchangeType = ExchangeType.TOPIC,
) -> Broker:
    if event_bus_name() in {"http", "relay"}:
        return HttpMessageBroker(
            os.getenv("EVENT_RELAY_URL", "http://localhost:8090"), exchange_name
        )
    return MessageBroker(rabbitmq_url, exchange_name, exchange_type)
