from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StockRead(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    quantity: int
    threshold: int
    low_stock: bool
    alert_state: str
    active: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementCreate(BaseModel):
    quantity: int = Field(gt=0, le=1_000_000)
    note: Optional[str] = Field(default=None, max_length=500)


class AdjustmentCreate(BaseModel):
    quantity: int = Field(ge=0, le=1_000_000)
    note: Optional[str] = Field(default=None, max_length=500)


class BatchMovementItem(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0, le=1_000_000)


class BatchMovementCreate(BaseModel):
    items: list[BatchMovementItem] = Field(min_length=1, max_length=100)
    note: Optional[str] = Field(default=None, max_length=500)
    reference_id: Optional[str] = Field(default=None, max_length=100)


class MovementRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    movement_type: str
    delta: int
    quantity_before: int
    quantity_after: int
    note: Optional[str]
    reference_id: Optional[str]
    correlation_id: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
