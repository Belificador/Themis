"""Outbound messaging channels, isolated from the inventory domain.

Each channel only knows how to render and deliver an already-built Alert.
Changing providers (Telegram, Meta WhatsApp Cloud API, Twilio, ...) never
touches catalog or inventory code.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class ChannelDeliveryError(Exception):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class Alert:
    event_id: str
    event_type: str
    product_id: str
    sku: str
    product_name: str
    current_stock: int
    threshold: int
    timestamp: str
    correlation_id: Optional[str]
    stock_state: str  # "depleted" | "replenished"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Alert":
        state = (
            "depleted"
            if payload.get("event_type") == "stock.depleted"
            else "replenished"
        )
        return cls(
            event_id=str(payload.get("event_id", "")),
            event_type=str(payload.get("event_type", "")),
            product_id=str(payload.get("product_id", "")),
            sku=str(payload.get("sku", "")),
            product_name=str(payload.get("product_name", "")),
            current_stock=int(payload.get("current_stock", 0)),
            threshold=int(payload.get("threshold", 0)),
            timestamp=str(
                payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
            ),
            correlation_id=payload.get("correlation_id"),
            stock_state=state,
        )


@dataclass
class ChannelResult:
    status: str  # sent | dry_run | disabled | failed
    detail: Optional[str] = None


def format_alert(alert: Alert) -> str:
    if alert.stock_state == "depleted":
        header = "🚨 SIN STOCK"
    else:
        header = "✅ STOCK RECUPERADO"
    return "\n".join(
        [
            header,
            f"Producto: {alert.product_name}",
            f"SKU: {alert.sku}",
            f"Stock actual: {alert.current_stock} (umbral {alert.threshold})",
            f"Hora: {alert.timestamp}",
            f"Evento: {alert.event_id}",
        ]
    )


class TelegramChannel:
    name = "telegram"

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.telegram_enabled
        self.token = settings.telegram_bot_token.strip()
        self.chat_id = settings.telegram_chat_id.strip()

    @property
    def mode(self) -> str:
        if not self._enabled:
            return "disabled"
        if not self.token or not self.chat_id:
            return "dry_run"
        return "live"

    @property
    def destination(self) -> Optional[str]:
        return self.chat_id or None

    async def send(self, alert: Alert) -> ChannelResult:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": format_alert(alert),
                    "disable_web_page_preview": True,
                },
            )
        if response.status_code >= 300:
            raise ChannelDeliveryError(
                f"telegram HTTP {response.status_code}: {response.text[:300]}",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        payload = response.json()
        message_id = payload.get("result", {}).get("message_id")
        return ChannelResult(status="sent", detail=f"telegram message_id={message_id}")


class WhatsAppChannel:
    """Meta WhatsApp Cloud API adapter."""

    name = "whatsapp"

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.whatsapp_enabled
        self.token = settings.whatsapp_token.strip()
        self.phone_number_id = settings.whatsapp_phone_number_id.strip()
        self.recipient = settings.whatsapp_recipient.strip()
        self.api_version = settings.whatsapp_api_version.strip() or "v20.0"

    @property
    def mode(self) -> str:
        if not self._enabled:
            return "disabled"
        if not self.token or not self.phone_number_id or not self.recipient:
            return "dry_run"
        return "live"

    @property
    def destination(self) -> Optional[str]:
        return self.recipient or None

    async def send(self, alert: Alert) -> ChannelResult:
        url = (
            f"https://graph.facebook.com/{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": self.recipient,
                    "type": "text",
                    "text": {"body": format_alert(alert)},
                },
            )
        if response.status_code >= 300:
            raise ChannelDeliveryError(
                f"whatsapp HTTP {response.status_code}: {response.text[:300]}",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        payload = response.json()
        message_id = None
        messages = payload.get("messages") or []
        if messages:
            message_id = messages[0].get("id")
        return ChannelResult(
            status="sent", detail=f"whatsapp message_id={message_id}"
        )


def build_channels(settings: Settings) -> list[Any]:
    return [TelegramChannel(settings), WhatsAppChannel(settings)]


async def send_with_retry(
    channel: Any, alert: Alert, max_attempts: int
) -> tuple[ChannelResult, int, Optional[str]]:
    """Send with bounded exponential backoff. Never raises."""
    last_error: Optional[str] = None
    attempts = 0
    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            return await channel.send(alert), attempts, None
        except ChannelDeliveryError as exc:
            last_error = str(exc)
            if not exc.retryable or attempt == max_attempts:
                break
        except Exception as exc:  # noqa: BLE001 - network errors are retryable
            last_error = str(exc)
            if attempt == max_attempts:
                break
        delay = min(2 ** attempt, 10) + random.uniform(0, 0.5)
        logger.warning(
            "%s delivery failed (%s/%s), retrying in %.1fs: %s",
            channel.name,
            attempt,
            max_attempts,
            delay,
            last_error,
        )
        await asyncio.sleep(delay)
    return ChannelResult(status="failed", detail=last_error), attempts, last_error
