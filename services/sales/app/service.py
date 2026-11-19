from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import settings
from .models import Sale, SaleItem
from .schemas import SaleCreate

logger = logging.getLogger(__name__)

CENT = Decimal("0.01")


def _money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _float(value: Decimal | float | int) -> float:
    return float(_money(value))


def _sale_number(sale_id: uuid.UUID, created_at: datetime) -> str:
    return f"V-{created_at:%Y%m%d}-{str(sale_id)[:6].upper()}"


def _load_options():
    return selectinload(Sale.items)


async def _by_id(session: AsyncSession, sale_id: uuid.UUID) -> Optional[Sale]:
    result = await session.execute(
        select(Sale).options(_load_options()).where(Sale.id == sale_id)
    )
    return result.scalar_one_or_none()


async def _by_key(
    session: AsyncSession, idempotency_key: Optional[str]
) -> Optional[Sale]:
    if not idempotency_key:
        return None
    result = await session.execute(
        select(Sale)
        .options(_load_options())
        .where(Sale.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def _fetch_product(
    client: httpx.AsyncClient, product_id: uuid.UUID
) -> dict[str, Any]:
    base = settings.catalog_url.rstrip("/")
    response = await client.get(f"{base}/products/{product_id}")
    if response.status_code == 404:
        raise HTTPException(
            status_code=404, detail=f"product not found: {product_id}"
        )
    response.raise_for_status()
    return response.json()


async def _send_stock_exit(
    client: httpx.AsyncClient, sale: Sale
) -> None:
    base = settings.inventory_url.rstrip("/")
    payload = {
        "items": [
            {"product_id": str(item.product_id), "quantity": item.quantity}
            for item in sale.items
        ],
        "reference_id": str(sale.id),
        "note": f"Venta {sale.sale_number}",
    }
    try:
        response = await client.post(f"{base}/stock/batch-exits", json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"inventory unavailable, retry with the same idempotency key: {exc}",
        )
    if response.status_code == 409:
        detail = "insufficient stock"
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
        raise HTTPException(status_code=409, detail=detail)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"inventory rejected the sale: {response.text[:300]}",
        )


async def _complete_pending(
    session: AsyncSession, sale: Sale, client: httpx.AsyncClient
) -> Sale:
    if sale.status == "completed":
        return sale
    try:
        await _send_stock_exit(client, sale)
    except HTTPException as exc:
        if exc.status_code == 409:
            await session.delete(sale)
            await session.commit()
        raise
    sale.status = "completed"
    await session.commit()
    loaded = await _by_id(session, sale.id)
    assert loaded is not None
    return loaded


async def create_sale(session: AsyncSession, payload: SaleCreate) -> Sale:
    existing = await _by_key(session, payload.idempotency_key)
    if existing is not None and existing.status == "completed":
        return existing

    async with httpx.AsyncClient(
        timeout=settings.request_timeout_seconds
    ) as client:
        if existing is not None:
            return await _complete_pending(session, existing, client)

        merged: dict[uuid.UUID, dict[str, Any]] = {}
        for item in payload.items:
            current = merged.get(item.product_id)
            if current is None:
                merged[item.product_id] = {
                    "quantity": item.quantity,
                    "unit_price": (
                        _money(item.unit_price)
                        if item.unit_price is not None
                        else None
                    ),
                }
                continue
            if (
                item.unit_price is not None
                and current["unit_price"] is not None
                and _money(item.unit_price) != current["unit_price"]
            ):
                raise HTTPException(
                    status_code=400,
                    detail="duplicate product with different unit_price",
                )
            current["quantity"] += item.quantity
            if item.unit_price is not None:
                current["unit_price"] = _money(item.unit_price)

        snapshots: dict[uuid.UUID, dict[str, Any]] = {}
        try:
            for product_id in merged:
                snapshots[product_id] = await _fetch_product(client, product_id)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"catalog unavailable: {exc}"
            )

        currency = payload.currency
        price_key = f"price_{currency.lower()}"
        cost_key = f"cost_price_{currency.lower()}"

        sale_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        currency_total = Decimal("0")
        cost_total = Decimal("0")
        items: list[SaleItem] = []

        for product_id, requested in merged.items():
            snapshot = snapshots[product_id]
            quantity = int(requested["quantity"])
            unit_price = (
                requested["unit_price"]
                if requested["unit_price"] is not None
                else _money(snapshot[price_key])
            )
            unit_cost = _money(snapshot.get(cost_key, 0))
            line_total = _money(unit_price * quantity)
            line_cost = _money(unit_cost * quantity)
            line_margin = _money(line_total - line_cost)
            currency_total += line_total
            cost_total += line_cost
            items.append(
                SaleItem(
                    product_id=product_id,
                    sku=str(snapshot["sku"]),
                    product_name=str(snapshot["product_name"]),
                    category=str(snapshot.get("category", "phone")),
                    quantity=quantity,
                    unit_price=unit_price,
                    unit_cost=unit_cost,
                    line_total=line_total,
                    line_cost=line_cost,
                    line_margin=line_margin,
                )
            )

        sale = Sale(
            id=sale_id,
            sale_number=_sale_number(sale_id, created_at),
            idempotency_key=payload.idempotency_key,
            status="pending",
            customer_name=payload.customer_name,
            payment_method=payload.payment_method,
            note=payload.note,
            currency=currency,
            total=_money(currency_total),
            cost_total=_money(cost_total),
            margin=_money(currency_total - cost_total),
            created_at=created_at,
            items=items,
        )
        session.add(sale)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            duplicate = await _by_key(session, payload.idempotency_key)
            if duplicate is not None:
                return await _complete_pending(session, duplicate, client)
            raise HTTPException(
                status_code=409, detail="sale conflict, retry"
            )

        created = await _by_id(session, sale_id)
        assert created is not None
        return await _complete_pending(session, created, client)


async def list_sales(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> list[Sale]:
    stmt = select(Sale).options(_load_options()).order_by(Sale.created_at.desc())
    if status:
        stmt = stmt.where(Sale.status == status)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            Sale.sale_number.ilike(like) | Sale.customer_name.ilike(like)
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_sale(session: AsyncSession, sale_id: uuid.UUID) -> Sale:
    sale = await _by_id(session, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="sale not found")
    return sale


def _as_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(timezone.utc).date()


def _period(sales: list[Sale]) -> dict[str, float]:
    total = sum((sale.total for sale in sales), Decimal("0"))
    cost = sum((sale.cost_total for sale in sales), Decimal("0"))
    margin = sum((sale.margin for sale in sales), Decimal("0"))
    units = sum(
        item.quantity for sale in sales for item in sale.items
    )
    count = len(sales)
    return {
        "sales": count,
        "units": units,
        "revenue": _float(total),
        "cost": _float(cost),
        "margin": _float(margin),
        "average_ticket": _float(total / count) if count else 0.0,
    }


async def sales_summary(
    session: AsyncSession, currency: str = "EUR"
) -> dict[str, Any]:
    result = await session.execute(
        select(Sale)
        .options(_load_options())
        .where(Sale.status == "completed", Sale.currency == currency)
    )
    sales = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)

    today_sales = [sale for sale in sales if _as_date(sale.created_at) == today]
    month_sales = [
        sale for sale in sales if _as_date(sale.created_at) >= month_start
    ]

    product_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "product_id": "",
            "product_name": "",
            "category": "phone",
            "units": 0,
            "revenue": Decimal("0"),
        }
    )
    for sale in sales:
        for item in sale.items:
            entry = product_totals[str(item.product_id)]
            entry["product_id"] = str(item.product_id)
            entry["product_name"] = item.product_name
            entry["category"] = item.category
            entry["units"] += item.quantity
            entry["revenue"] += item.line_total

    top_products = sorted(
        product_totals.values(), key=lambda entry: entry["units"], reverse=True
    )[:5]

    daily = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_sales = [sale for sale in sales if _as_date(sale.created_at) == day]
        daily.append(
            {
                "date": day.isoformat(),
                "sales": len(day_sales),
                "revenue": _float(
                    sum((sale.total for sale in day_sales), Decimal("0"))
                ),
            }
        )

    return {
        "currency": currency,
        "all_time": _period(sales),
        "today": _period(today_sales),
        "month": _period(month_sales),
        "top_products": [
            {
                "product_id": entry["product_id"],
                "product_name": entry["product_name"],
                "category": entry["category"],
                "units": entry["units"],
                "revenue": _float(entry["revenue"]),
            }
            for entry in top_products
        ],
        "daily": daily,
    }
