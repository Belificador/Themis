from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .alerts import record_stock_alert
from egm_common.auth import verify_password, decode_token, create_access_token
from .config import settings, VENEZUELA_TZ
from .db import get_session
from .models import (
    Product,
    Sale,
    SaleItem,
    StockItem,
    StockMovement,
    StockUnit,
    User,
)
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


async def _by_key(session: AsyncSession, idempotency_key: Optional[str]) -> Optional[Sale]:
    if not idempotency_key:
        return None
    result = await session.execute(
        select(Sale)
        .options(_load_options())
        .where(Sale.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


def _split_imeis(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _join_imeis(imeis: list[str]) -> Optional[str]:
    joined = ""
    for imei in imeis:
        candidate = f"{joined}, {imei}" if joined else imei
        if len(candidate) > 64:
            break
        joined = candidate
    return joined or None


async def _mark_units_sold(
    session: AsyncSession, sale: Sale, item: SaleItem, imeis: list[str]
) -> None:
    if not imeis:
        return
    result = await session.execute(
        select(StockUnit).where(
            StockUnit.product_id == item.product_id,
            StockUnit.imei.in_(imeis),
        )
    )
    units = {unit.imei: unit for unit in result.scalars().all()}
    for imei in imeis:
        unit = units.get(imei)
        if unit is None:
            continue
        if unit.status != "available":
            raise HTTPException(
                status_code=409, detail=f"IMEI {imei} no está disponible"
            )
        unit.status = "sold"
        unit.sale_id = sale.id
        unit.updated_at = settings.now_venezuela()


async def _send_stock_exit(
    session: AsyncSession,
    sale: Sale,
    imeis_by_product: Optional[dict[uuid.UUID, list[str]]] = None,
) -> None:
    for item in sale.items:
        stock_item = await session.get(StockItem, item.product_id)
        if not stock_item:
            raise HTTPException(
                status_code=404, detail=f"stock not found for product {item.product_id}"
            )
        if stock_item.quantity < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"insufficient stock for {stock_item.sku}: current={stock_item.quantity}, requested={item.quantity}",
            )
        stock_item.quantity -= item.quantity
        stock_item.updated_at = settings.now_venezuela()
        quantity_before = stock_item.quantity + item.quantity

        session.add(
            StockMovement(
                product_id=item.product_id,
                movement_type="exit",
                delta=-item.quantity,
                quantity_before=quantity_before,
                quantity_after=stock_item.quantity,
                note=f"Venta {sale.sale_number}",
                reference_id=str(sale.id),
            )
        )
        record_stock_alert(
            session,
            stock_item,
            quantity_before=quantity_before,
            quantity_after=stock_item.quantity,
        )
        item_imeis = (
            imeis_by_product.get(item.product_id)
            if imeis_by_product is not None
            else None
        ) or _split_imeis(item.imei)
        await _mark_units_sold(session, sale, item, item_imeis)


async def _complete_pending(
    session: AsyncSession,
    sale: Sale,
    imeis_by_product: Optional[dict[uuid.UUID, list[str]]] = None,
) -> Sale:
    if sale.status == "completed":
        return sale
    await _send_stock_exit(session, sale, imeis_by_product)
    sale.status = "completed"
    await session.commit()
    loaded = await _by_id(session, sale.id)
    assert loaded is not None
    return loaded


async def create_sale(session: AsyncSession, payload: SaleCreate) -> Sale:
    if not payload.customer_name or not payload.customer_name.strip():
        raise HTTPException(status_code=400, detail="El cliente es obligatorio")
    if not payload.vendedor or not payload.vendedor.strip():
        raise HTTPException(status_code=400, detail="El vendedor es obligatorio")

    # Validar que los precios no sean negativos
    for item in payload.items:
        if item.unit_price is not None and item.unit_price < 0:
            raise HTTPException(status_code=400, detail="El precio unitario no puede ser negativo")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")

    existing = await _by_key(session, payload.idempotency_key)
    if existing is not None:
        if existing.status == "completed":
            return existing
        # Un intento anterior quedó pendiente (por ejemplo, un IMEI no
        # disponible). Se descarta para no reutilizar datos obsoletos.
        await session.delete(existing)
        await session.commit()

    merged: dict[uuid.UUID, dict[str, Any]] = {}
    for item in payload.items:
        current = merged.get(item.product_id)
        incoming_imeis = list(item.imeis) or ([item.imei] if item.imei else [])
        if current is None:
            merged[item.product_id] = {
                "quantity": item.quantity,
                "unit_price": _money(item.unit_price) if item.unit_price is not None else None,
                "imeis": incoming_imeis,
            }
            continue
        if item.unit_price is not None and current["unit_price"] is not None and _money(item.unit_price) != current["unit_price"]:
            raise HTTPException(status_code=400, detail="duplicate product with different unit_price")
        current["quantity"] += item.quantity
        current["imeis"].extend(
            imei for imei in incoming_imeis if imei not in current["imeis"]
        )
        if item.unit_price is not None:
            current["unit_price"] = _money(item.unit_price)

    snapshots: dict[uuid.UUID, dict[str, Any]] = {}
    for product_id in merged:
        snapshot = await session.get(Product, product_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"product not found: {product_id}")
        snapshots[product_id] = snapshot

    for product_id, requested in merged.items():
        imeis = requested["imeis"]
        if not imeis:
            continue
        result = await session.execute(
            select(StockUnit).where(
                StockUnit.product_id == product_id,
                StockUnit.imei.in_(imeis),
            )
        )
        units = {unit.imei: unit for unit in result.scalars().all()}
        for imei in imeis:
            unit = units.get(imei)
            if unit is not None and unit.status != "available":
                raise HTTPException(
                    status_code=409,
                    detail=f"IMEI {imei} no está disponible",
                )

    currency = payload.currency

    sale_id = uuid.uuid4()
    created_at = settings.now_venezuela()
    currency_total = Decimal("0")
    items: list[SaleItem] = []

    for product_id, requested in merged.items():
        snapshot = snapshots[product_id]
        quantity = int(requested["quantity"])
        unit_price = requested["unit_price"]
        if unit_price is None:
            if payload.payment_method == "cashea" and snapshot.price_cashea_usd:
                unit_price = _money(snapshot.price_cashea_usd)
            else:
                unit_price = _money(snapshot.price_usd)
        else:
            unit_price = _money(unit_price)
        line_total = _money(unit_price * quantity)
        currency_total += line_total
        items.append(
            SaleItem(
                product_id=product_id,
                sku=snapshot.sku,
                product_name=snapshot.product_name,
                category=snapshot.category,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                imei=_join_imeis(requested["imeis"]),
            )
        )

    imeis_by_product = {
        pid: requested["imeis"]
        for pid, requested in merged.items()
        if requested["imeis"]
    }

    sale = Sale(
        id=sale_id,
        sale_number=_sale_number(sale_id, created_at),
        idempotency_key=payload.idempotency_key,
        status="pending",
        customer_name=payload.customer_name,
        vendedor=payload.vendedor,
        payment_method=payload.payment_method,
        note=payload.note,
        currency=currency,
        total=_money(currency_total),
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
            return await _complete_pending(
                session, duplicate, imeis_by_product
            )
        raise HTTPException(status_code=409, detail="sale conflict, retry")

    created = await _by_id(session, sale_id)
    assert created is not None
    return await _complete_pending(session, created, imeis_by_product)


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
        stmt = stmt.where(Sale.sale_number.ilike(like) | Sale.customer_name.ilike(like) | Sale.vendedor.ilike(like))
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
    return value.astimezone(VENEZUELA_TZ).date()


def _period(sales: list[Sale]) -> dict[str, float]:
    total = sum((sale.total for sale in sales), Decimal("0"))
    units = sum(item.quantity for sale in sales for item in sale.items)
    count = len(sales)
    return {
        "sales": count,
        "units": units,
        "revenue": _float(total),
        "average_ticket": _float(total / count) if count else 0.0,
    }


async def sales_summary(session: AsyncSession, currency: str = "USD") -> dict[str, Any]:
    result = await session.execute(
        select(Sale)
        .options(_load_options())
        .where(Sale.status == "completed", Sale.currency == currency)
    )
    sales = list(result.scalars().all())

    now = settings.now_venezuela()
    today = now.date()
    month_start = today.replace(day=1)

    today_sales = [sale for sale in sales if _as_date(sale.created_at) == today]
    month_sales = [sale for sale in sales if _as_date(sale.created_at) >= month_start]

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

    top_products = sorted(product_totals.values(), key=lambda entry: entry["units"], reverse=True)[:5]

    daily = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_sales = [sale for sale in sales if _as_date(sale.created_at) == day]
        daily.append({
            "date": day.isoformat(),
            "sales": len(day_sales),
            "revenue": _float(sum((sale.total for sale in day_sales), Decimal("0"))),
        })

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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def authenticate_user(
    session: AsyncSession, username: str, password: str
):
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def delete_sale(session: AsyncSession, sale_id: uuid.UUID) -> Sale:
    sale = await _by_id(session, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="venta no encontrada")

    # Restaurar stock de cada ítem
    for item in sale.items:
        stock_item = await session.get(StockItem, item.product_id)
        if stock_item:
            stock_item.quantity = int(stock_item.quantity) + int(item.quantity)
            stock_item.updated_at = settings.now_venezuela()

    # Liberar los IMEIs vendidos en esta venta
    units = await session.execute(
        select(StockUnit).where(StockUnit.sale_id == sale.id)
    )
    for unit in units.scalars().all():
        unit.status = "available"
        unit.sale_id = None
        unit.updated_at = settings.now_venezuela()

    # Eliminar movimientos de stock asociados a esta venta
    result = await session.execute(
        select(StockMovement).where(
            StockMovement.reference_id == str(sale.id)
        )
    )
    for movement in result.scalars().all():
        await session.delete(movement)

    await session.delete(sale)
    await session.commit()
    return sale


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo"
        )
    return user
