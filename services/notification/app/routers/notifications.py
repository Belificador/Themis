from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..channels import Alert, send_with_retry
from ..config import settings
from ..consumer import CHANNELS
from ..db import get_session
from ..models import NotificationLog, ProcessedEvent
from ..schemas import NotificationLogRead, TestAlertRequest

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationLogRead])
async def list_notifications(
    limit: int = Query(default=100, ge=1, le=500),
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> list[NotificationLog]:
    stmt = select(NotificationLog).order_by(NotificationLog.created_at.desc())
    if status:
        stmt = stmt.where(NotificationLog.status == status)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/stats")
async def notification_stats(
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = await session.execute(
        select(
            NotificationLog.channel,
            NotificationLog.status,
            func.count(NotificationLog.id),
        ).group_by(NotificationLog.channel, NotificationLog.status)
    )
    by_channel_status = [
        {"channel": channel, "status": status, "count": count}
        for channel, status, count in rows.all()
    ]
    processed = (
        await session.execute(select(func.count(ProcessedEvent.event_id)))
    ).scalar_one()
    return {
        "service": settings.service_name,
        "dedupe_window_seconds": settings.dedupe_window_seconds,
        "processed_events": processed,
        "by_channel_status": by_channel_status,
    }


@router.post("/test")
async def send_test_alert(payload: TestAlertRequest) -> dict:
    alert = Alert(
        event_id=f"test-{uuid.uuid4()}",
        event_type="stock.depleted",
        product_id=str(uuid.uuid4()),
        sku=payload.sku,
        product_name=payload.product_name,
        current_stock=payload.current_stock,
        threshold=payload.threshold,
        timestamp=datetime.now(timezone.utc).isoformat(),
        correlation_id=None,
        stock_state="depleted",
    )
    results = []
    for channel in CHANNELS:
        if payload.channel not in ("all", channel.name):
            continue
        mode = channel.mode
        if mode == "disabled":
            results.append(
                {
                    "channel": channel.name,
                    "status": "disabled",
                    "detail": "channel disabled by configuration",
                }
            )
            continue
        if mode == "dry_run":
            results.append(
                {
                    "channel": channel.name,
                    "status": "dry_run",
                    "detail": "credentials missing; message not sent",
                }
            )
            continue
        result, attempts, error = await send_with_retry(
            channel, alert, settings.max_attempts
        )
        results.append(
            {
                "channel": channel.name,
                "status": result.status,
                "attempts": attempts,
                "detail": result.detail,
                "error": error,
            }
        )
    return {"event_id": alert.event_id, "results": results}
