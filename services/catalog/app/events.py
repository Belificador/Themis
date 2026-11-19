from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .models import Product


def build_product_event(
    event_id: str,
    event_type: str,
    product: Product,
    correlation_id: Optional[str],
) -> dict[str, Any]:
    """Serialize a product snapshot for the `products` exchange.

    Only JSON-native values are used so the payload can be persisted in the
    outbox JSON column without custom encoders.
    """
    return {
        "event_id": event_id,
        "event_type": event_type,
        "product_id": str(product.id),
        "sku": product.sku,
        "product_name": product.product_name,
        "brand": product.brand,
        "model": product.model,
        "ram_gb": product.ram_gb,
        "storage_gb": product.storage_gb,
        "color": product.color,
        "category": product.category,
        "cost_price_eur": str(product.cost_price_eur),
        "price_eur": str(product.price_eur),
        "cost_price_usd": str(product.cost_price_usd),
        "price_usd": str(product.price_usd),
        "threshold": product.threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
    }
