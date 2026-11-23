from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    image_content_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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


class StockItem(Base):
    __tablename__ = "stock_items"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal"
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    @property
    def low_stock(self) -> bool:
        return self.quantity <= self.threshold


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        UniqueConstraint(
            "reference_id",
            "product_id",
            "movement_type",
            name="uq_stock_movement_reference",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sale_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(120), unique=True, index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    customer_name: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    vendedor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="cash"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    margin: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    invoice_stored_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    invoice_filename: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    invoice_content_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    invoice_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invoice_uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="phone")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_margin: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="items")
