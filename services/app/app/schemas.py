from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["phone", "tablet", "accessory"]
PaymentMethod = Literal["cash", "card", "transfer", "other", "cashea"]
Currency = Literal["USD"]


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    brand: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    storage_gb: int = Field(default=0, ge=0, le=4096)
    ram_gb: int = Field(default=0, ge=0, le=1024)
    color: str = Field(min_length=1, max_length=40)
    category: Category = "phone"
    price_usd: float = Field(ge=0)
    price_bcv_usd: float = Field(default=0, ge=0)
    price_cashea_usd: float = Field(default=0, ge=0)
    camera: Optional[str] = Field(default=None, max_length=120)
    ram_virtual_gb: int = Field(default=0, ge=0)
    threshold: int = Field(default=0, ge=0)

    @field_validator("sku", "brand", "model", "color")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be blank")
        return value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    brand: Optional[str] = Field(default=None, min_length=1, max_length=80)
    model: Optional[str] = Field(default=None, min_length=1, max_length=80)
    storage_gb: Optional[int] = Field(default=None, ge=0, le=4096)
    ram_gb: Optional[int] = Field(default=None, ge=0, le=1024)
    color: Optional[str] = Field(default=None, min_length=1, max_length=40)
    category: Optional[Category] = None
    price_usd: Optional[float] = Field(default=None, ge=0)
    price_bcv_usd: Optional[float] = Field(default=None, ge=0)
    price_cashea_usd: Optional[float] = Field(default=None, ge=0)
    camera: Optional[str] = Field(default=None, max_length=120)
    ram_virtual_gb: Optional[int] = Field(default=None, ge=0)
    threshold: Optional[int] = Field(default=None, ge=0)

    @field_validator("sku", "brand", "model", "color")
    @classmethod
    def _strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("field must not be blank")
        return value


class ProductRead(ProductBase):
    id: uuid.UUID
    product_name: str
    image_content_type: Optional[str]
    image_size: Optional[int]
    image_updated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockItemRead(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    threshold: int
    quantity: int
    alert_state: str
    active: bool
    low_stock: bool

    model_config = ConfigDict(from_attributes=True)


class StockMovementRead(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    movement_type: str
    delta: int
    quantity_before: int
    quantity_after: int
    note: Optional[str]
    reference_id: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementCreate(BaseModel):
    quantity: int = Field(gt=0)
    note: Optional[str] = Field(default=None, max_length=500)


class AdjustmentCreate(BaseModel):
    quantity: int = Field(ge=0)
    note: Optional[str] = Field(default=None, max_length=500)


class BatchMovementCreate(BaseModel):
    items: list[MovementCreate] = Field(min_length=1, max_length=50)
    reference_id: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=500)


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price: Optional[float] = Field(default=None, ge=0)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1, max_length=50)
    payment_method: PaymentMethod = "cash"
    currency: Currency = "USD"
    customer_name: Optional[str] = Field(default=None, max_length=120)
    vendedor: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)

    @field_validator("customer_name", "note", "idempotency_key", "vendedor")
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
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class SaleRead(BaseModel):
    id: uuid.UUID
    sale_number: str
    status: str
    customer_name: Optional[str]
    vendedor: Optional[str]
    payment_method: str
    note: Optional[str]
    currency: str
    total: float
    invoice_filename: Optional[str]
    invoice_content_type: Optional[str]
    invoice_size: Optional[int]
    invoice_uploaded_at: Optional[datetime]
    created_at: datetime
    items: list[SaleItemRead]

    model_config = ConfigDict(from_attributes=True)


class PeriodStats(BaseModel):
    sales: int
    units: int
    revenue: float
    average_ticket: float


class NotificationLogRead(BaseModel):
    id: uuid.UUID
    event_id: str
    event_type: str
    product_id: uuid.UUID
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


class NotificationChannelStat(BaseModel):
    channel: str
    status: str
    count: int


class NotificationStats(BaseModel):
    service: str
    dedupe_window_seconds: int
    processed_events: int
    by_channel_status: list[NotificationChannelStat]


class TestAlertRequest(BaseModel):
    sku: str = "TEST-SKU"
    product_name: str = "Producto de prueba"
    current_stock: int = 0
    threshold: int = 0
    channel: str = "all"


class TestResultItem(BaseModel):
    channel: str
    status: str
    attempts: Optional[int] = None
    detail: Optional[str] = None
    error: Optional[str] = None


class TestResult(BaseModel):
    event_id: str
    results: list[TestResultItem]


class SalesSummary(BaseModel):
    currency: Currency
    all_time: PeriodStats
    today: PeriodStats
    month: PeriodStats
    top_products: list[dict]
    daily: list[dict]

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
