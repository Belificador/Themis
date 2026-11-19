from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .db import SessionLocal
from .models import StockItem

logger = logging.getLogger(__name__)


async def handle_product_event(
    payload: dict[str, Any], message_id: Optional[str] = None
) -> None:
    """Build the local stock read model from catalog events.

    This consumer writes only to inventory-service's own database. It never
    queries the catalog database directly.
    """
    event_type = payload.get("event_type")
    raw_product_id = payload.get("product_id")
    if not raw_product_id:
        logger.warning("ignoring product event without product_id id=%s", message_id)
        return

    product_id = uuid.UUID(str(raw_product_id))
    now = datetime.now(timezone.utc)

    async with SessionLocal() as session:
        item = await session.get(StockItem, product_id)

        if event_type == "product.deleted":
            if item is not None:
                item.active = False
                item.updated_at = now
                await session.commit()
                logger.info("deactivated stock item product_id=%s", product_id)
            return

        if event_type not in {"product.created", "product.updated"}:
            logger.warning("ignoring unsupported event_type=%s", event_type)
            return

        product_name = payload.get("product_name") or " ".join(
            str(payload.get(key, "")).strip()
            for key in ("brand", "model", "ram_gb", "storage_gb", "color")
        ).strip()
        threshold = int(payload.get("threshold") or 0)

        if item is None:
            item = StockItem(
                product_id=product_id,
                sku=str(payload.get("sku", "")),
                product_name=product_name or "unknown product",
                threshold=threshold,
                quantity=0,
                alert_state="normal",
                active=True,
            )
            session.add(item)
        else:
            item.sku = str(payload.get("sku", item.sku))
            item.product_name = product_name or item.product_name
            item.threshold = threshold
            item.active = True
            item.updated_at = now

        await session.commit()
        logger.info(
            "upserted stock snapshot product_id=%s event=%s",
            product_id,
            event_type,
        )
