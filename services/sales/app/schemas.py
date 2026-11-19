from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PaymentMethod = Literal["cash", "card", "transfer", "other", "cashea"]
Currency = Literal["EUR", "USD"]


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price: Optional[float] = Field(default=None, ge=0)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1, max_length=50)
    payment_method: PaymentMethod = "cash"
    currency: Currency = "EUR"
    customer_name: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)

    @field_validator("customer_name", "note", "idempotency_key")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SaleItemRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    product_name: str
    category: str
    quantity: int
    unit_price: float
    unit_cost: float
    line_total: float
    line_cost: float
    line_margin: float

    model_config = ConfigDict(from_attributes=True)


class SaleRead(BaseModel):
    id: uuid.UUID
    sale_number: str
    status: str
    customer_name: Optional[str]
    payment_method: str
    note: Optional[str]
    currency: str
    total: float
    cost_total: float
    margin: float
    invoice_filename: Optional[str]
    invoice_content_type: Optional[str]
    invoice_size: Optional[int]
    invoice_uploaded_at: Optional[datetime]
    created_at: datetime
    items: list[SaleItemRead]

    model_config = ConfigDict(from_attributes=True)
