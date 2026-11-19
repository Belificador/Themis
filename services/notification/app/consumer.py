from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .channels import Alert, build_channels, send_with_retry
from .config import settings
from .db import SessionLocal
from .models import DedupeRecord, NotificationLog, ProcessedEvent

logger = logging.getLogger(__name__)

CHANNELS = build_channels(settings)


def _make_log(
    alert: Alert,
    channel: Any,
    *,
    status: str,
    attempts: int,
    detail: Optional[str],
    error: Optional[str],
) -> NotificationLog:
    now = datetime.now(timezone.utc)
    return NotificationLog(
        event_id=alert.event_id,
        event_type=alert.event_type,
        product_id=alert.product_id,
        product_name=alert.product_name,
        channel=channel.name,
        destination=channel.destination,
        status=status,
        attempts=attempts,
        detail=detail,
        error=error,
        correlation_id=alert.correlation_id,
        sent_at=now if status == "sent" else None,
    )


async def handle_stock_event(
    payload: dict[str, Any], message_id: Optional[str] = None
) -> None:
    event_id = str(payload.get("event_id") or message_id or "")
    event_type = str(payload.get("event_type", ""))
    if not event_id:
        logger.warning("dropping stock event without event_id")
        return
    if event_type not in {"stock.depleted", "stock.replenished"}:
        logger.warning("ignoring unsupported stock event type=%s", event_type)
        return

    product_id = str(payload.get("product_id", ""))
    alert = Alert.from_payload(payload)
    stock_state = alert.stock_state

    async with SessionLocal() as session:
        if await session.get(ProcessedEvent, event_id) is not None:
            logger.info("duplicate event ignored event_id=%s", event_id)
            return

        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.dedupe_window_seconds
        )
        recent = (
            await session.execute(
                select(DedupeRecord.id)
                .where(
                    DedupeRecord.product_id == product_id,
                    DedupeRecord.stock_state == stock_state,
                    DedupeRecord.created_at >= cutoff,
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        if recent is not None:
            session.add(
                ProcessedEvent(
                    event_id=event_id,
                    event_type=event_type,
                    product_id=product_id,
                    status="skipped_dedupe",
                )
            )
            await session.commit()
            logger.info(
                "deduped within window state=%s product_id=%s", stock_state, product_id
            )
            return

        logs: list[NotificationLog] = []
        delivered_any = False

        for channel in CHANNELS:
            mode = channel.mode
            if mode == "disabled":
                logs.append(
                    _make_log(
                        alert,
                        channel,
                        status="disabled",
                        attempts=0,
                        detail="channel disabled by configuration",
                        error=None,
                    )
                )
                continue
            if mode == "dry_run":
                delivered_any = True
                logger.info(
                    "dry-run alert channel=%s event_id=%s text=%r",
                    channel.name,
                    event_id,
                    alert.product_name,
                )
                logs.append(
                    _make_log(
                        alert,
                        channel,
                        status="dry_run",
                        attempts=0,
                        detail="credentials missing; message not sent",
                        error=None,
                    )
                )
                continue

            result, attempts, error = await send_with_retry(
                channel, alert, settings.max_attempts
            )
            if result.status == "sent":
                delivered_any = True
                logger.info(
                    "alert sent channel=%s event_id=%s", channel.name, event_id
                )
            else:
                logger.error(
                    "alert failed channel=%s event_id=%s error=%s",
                    channel.name,
                    event_id,
                    error,
                )
            logs.append(
                _make_log(
                    alert,
                    channel,
                    status=result.status,
                    attempts=attempts,
                    detail=result.detail,
                    error=error,
                )
            )

        if delivered_any:
            session.add(
                DedupeRecord(
                    product_id=product_id,
                    stock_state=stock_state,
                    event_id=event_id,
                )
            )
        for log in logs:
            session.add(log)
        session.add(
            ProcessedEvent(
                event_id=event_id,
                event_type=event_type,
                product_id=product_id,
                status="processed",
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.info("duplicate event detected on commit event_id=%s", event_id)
