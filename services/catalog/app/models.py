from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    ram_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    color: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, default="phone"
    )
    cost_price_eur: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    price_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    price_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_stored_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    image_content_type: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    image_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    @property
    def product_name(self) -> str:
        parts = [self.brand, self.model]
        if self.ram_gb:
            parts.append(f"{self.ram_gb}GB")
        if self.storage_gb:
            parts.append(f"{self.storage_gb}GB")
        parts.append(self.color)
        return " ".join(parts)
