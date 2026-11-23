from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..models import NotificationLog
from ..schemas import (
    NotificationLogRead,
    NotificationStats,
    TestAlertRequest,
    TestResult,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Canales disponibles. Sin credenciales configuradas operan en modo dry_run.
CHANNELS = ("telegram", "whatsapp")


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


@router.get("/stats", response_model=NotificationStats)
async def notification_stats(
    session: AsyncSession = Depends(get_session),
) -> NotificationStats:
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
        await session.execute(
            select(func.count(func.distinct(NotificationLog.event_id)))
        )
    ).scalar_one()
    return NotificationStats(
        service=settings.service_name,
        dedupe_window_seconds=settings.dedupe_window_seconds,
        processed_events=int(processed),
        by_channel_status=by_channel_status,
    )


@router.post("/test", response_model=TestResult)
async def send_test_alert(payload: TestAlertRequest) -> TestResult:
    event_id = f"test-{uuid.uuid4()}"
    results = []
    for channel in CHANNELS:
        if payload.channel not in ("all", channel):
            continue
        # Sin proveedores externos configurados: modo dry_run.
        results.append(
            {
                "channel": channel,
                "status": "dry_run",
                "detail": "credentials missing; message not sent",
            }
        )
    return TestResult(event_id=event_id, results=results)
