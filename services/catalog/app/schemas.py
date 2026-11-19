from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    brand: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    storage_gb: int = Field(default=0, ge=0, le=4096)
    ram_gb: int = Field(default=0, ge=0, le=1024)
    color: str = Field(min_length=1, max_length=40)
    category: Literal["phone", "tablet", "accessory"] = "phone"
    cost_price_eur: float = Field(default=0, ge=0)
    price_eur: float = Field(ge=0)
    cost_price_usd: float = Field(default=0, ge=0)
    price_usd: float = Field(ge=0)
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
    category: Optional[Literal["phone", "tablet", "accessory"]] = None
    cost_price_eur: Optional[float] = Field(default=None, ge=0)
    price_eur: Optional[float] = Field(default=None, ge=0)
    cost_price_usd: Optional[float] = Field(default=None, ge=0)
    price_usd: Optional[float] = Field(default=None, ge=0)
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
