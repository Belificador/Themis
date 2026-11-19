from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .models import StockItem


def build_stock_event(
    event_id: str,
    event_type: str,
    item: StockItem,
    correlation_id: Optional[str],
) -> dict[str, Any]:
    """Payload aligned with contracts/stock.depleted.schema.json."""
    return {
        "event_id": event_id,
        "event_type": event_type,
        "product_id": str(item.product_id),
        "sku": item.sku,
        "product_name": item.product_name,
        "current_stock": item.quantity,
        "threshold": item.threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
