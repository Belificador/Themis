from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationLogRead(BaseModel):
    id: uuid.UUID
    event_id: str
    event_type: str
    product_id: str
    product_name: str
    channel: str
    destination: Optional[str]
    status: str
    attempts: int
    detail: Optional[str]
    error: Optional[str]
    correlation_id: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TestAlertRequest(BaseModel):
    channel: str = "all"
    product_name: str = "Demo Phone X 128GB Black"
    sku: str = "DEMO-X-128-BLK"
    current_stock: int = 0
    threshold: int = 1
