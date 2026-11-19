"""Generic transactional-outbox dispatcher.

Services write business state and an outbox row in the same database
transaction. A background task then publishes pending rows to RabbitMQ and
marks them as published. This yields at-least-once delivery without
distributed transactions; consumers must be idempotent.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

logger = logging.getLogger(__name__)


class OutboxMixin:
    """Columns shared by every service's outbox table."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    routing_key: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


async def run_outbox_dispatcher(
    session_factory,
    model,
    broker,
    interval_seconds: float = 1.0,
    batch_size: int = 50,
    use_row_locks: bool = True,
) -> None:
    """Publish pending outbox rows forever (until cancelled)."""
    while True:
        try:
            async with session_factory() as session:
                statement = (
                    select(model)
                    .where(model.published_at.is_(None))
                    .order_by(model.created_at)
                    .limit(batch_size)
                )
                if use_row_locks:
                    statement = statement.with_for_update(skip_locked=True)
                result = await session.execute(statement)
                rows = result.scalars().all()
                for row in rows:
                    try:
                        await broker.publish(
                            row.routing_key,
                            row.payload,
                            event_id=row.id,
                            correlation_id=row.correlation_id,
                        )
                        row.published_at = datetime.now(timezone.utc)
                        row.last_error = None
                    except Exception as exc:  # noqa: BLE001 - retry next tick
                        row.attempts += 1
                        row.last_error = str(exc)[:1000]
                        logger.warning(
                            "outbox publish failed id=%s attempts=%s: %s",
                            row.id,
                            row.attempts,
                            exc,
                            extra={"extra_fields": {"event_id": row.id}},
                        )
                if rows:
                    await session.commit()
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            raise
        except Exception:  # noqa: BLE001 - keep the dispatcher alive
            logger.exception("outbox dispatcher iteration failed")
        await asyncio.sleep(interval_seconds)
