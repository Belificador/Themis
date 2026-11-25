from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import NotificationLog, StockItem

CHANNELS = ("telegram", "whatsapp")


def _state_for(quantity: int, threshold: int) -> str:
    if quantity <= 0:
        return "depleted"
    if quantity <= threshold:
        return "low"
    return "normal"


def record_stock_alert(
    session: AsyncSession,
    item: StockItem,
    *,
    quantity_before: int,
    quantity_after: int,
    correlation_id: Optional[str] = None,
) -> None:
    """Actualiza el estado de alerta y registra un aviso en las transiciones.

    Sin proveedores externos configurados, los avisos quedan como ``dry_run``
    para que sean visibles en la pestaña de Alertas.
    """
    previous_state = item.alert_state
    new_state = _state_for(quantity_after, item.threshold)
    item.alert_state = new_state

    if new_state == previous_state or new_state == "normal":
        return

    event_type = "stock.depleted" if new_state == "depleted" else "stock.low"
    now = settings.now_venezuela()
    event_id = f"{event_type}-{item.product_id}-{uuid.uuid4()}"

    for channel in CHANNELS:
        session.add(
            NotificationLog(
                event_id=event_id,
                event_type=event_type,
                product_id=item.product_id,
                product_name=item.product_name,
                channel=channel,
                status="dry_run",
                attempts=0,
                detail="credentials missing; message not sent",
                correlation_id=correlation_id,
                created_at=now,
            )
        )
