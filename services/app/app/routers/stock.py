from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..alerts import record_stock_alert
from ..db import get_session
from ..models import StockItem, StockMovement
from ..schemas import (
    AdjustmentCreate,
    BatchMovementCreate,
    MovementCreate,
    StockItemRead,
    StockMovementRead,
)

router = APIRouter(prefix="/api/inventory/stock", tags=["stock"])


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


async def _apply_movement(
    session: AsyncSession,
    item: StockItem,
    movement_type: str,
    *,
    quantity: int,
    note: Optional[str],
    reference_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    before = item.quantity
    if movement_type == "entry":
        after = before + quantity
    elif movement_type == "exit":
        after = before - quantity
        if after < 0:
            raise HTTPException(
                status_code=409,
                detail=f"insufficient stock for {item.sku}: current={before}, requested={quantity}",
            )
    elif movement_type == "adjustment":
        after = quantity
    else:
        raise ValueError(f"unsupported movement type {movement_type}")

    delta = after - before
    item.quantity = after
    item.updated_at = datetime.now(timezone.utc)

    session.add(
        StockMovement(
            product_id=item.product_id,
            movement_type=movement_type,
            delta=delta,
            quantity_before=before,
            quantity_after=after,
            note=(note or "").strip() or None,
            reference_id=reference_id,
            correlation_id=correlation_id,
        )
    )
    record_stock_alert(
        session,
        item,
        quantity_before=before,
        quantity_after=after,
        correlation_id=correlation_id,
    )


@router.get("", response_model=list[StockItemRead])
async def list_stock(session: AsyncSession = Depends(get_session)) -> list[StockItem]:
    result = await session.execute(
        select(StockItem).order_by(StockItem.updated_at.desc())
    )
    return list(result.scalars().all())


@router.post("/batch-exits", response_model=list[StockItemRead], status_code=201)
async def batch_exits(
    payload: BatchMovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[StockItem]:
    correlation_id = _correlation_id(request)
    product_ids = [item.product_id for item in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="duplicate product_id in batch")
    result = await session.execute(
        select(StockItem).where(StockItem.product_id.in_(product_ids))
    )
    items_map = {item.product_id: item for item in result.scalars().all()}
    for requested in payload.items:
        item = items_map.get(requested.product_id)
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"stock item not found: {requested.product_id}",
            )
        if item.quantity < requested.quantity:
            raise HTTPException(
                status_code=409, detail=f"insufficient stock for {item.sku}"
            )
    for requested in payload.items:
        item = items_map[requested.product_id]
        await _apply_movement(
            session,
            item,
            "exit",
            quantity=requested.quantity,
            note=payload.note,
            reference_id=payload.reference_id,
            correlation_id=correlation_id,
        )
    await session.commit()
    refreshed = []
    for pid in product_ids:
        item = await session.get(StockItem, pid)
        if item:
            await session.refresh(item)
            refreshed.append(item)
    return refreshed


@router.post("/batch-entries", response_model=list[StockItemRead], status_code=201)
async def batch_entries(
    payload: BatchMovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[StockItem]:
    correlation_id = _correlation_id(request)
    product_ids = [item.product_id for item in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="duplicate product_id in batch")
    result = await session.execute(
        select(StockItem).where(StockItem.product_id.in_(product_ids))
    )
    items_map = {item.product_id: item for item in result.scalars().all()}
    for requested in payload.items:
        item = items_map.get(requested.product_id)
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"stock item not found: {requested.product_id}",
            )
        await _apply_movement(
            session,
            item,
            "entry",
            quantity=requested.quantity,
            note=payload.note,
            reference_id=payload.reference_id,
            correlation_id=correlation_id,
        )
    await session.commit()
    refreshed = []
    for pid in product_ids:
        item = await session.get(StockItem, pid)
        if item:
            await session.refresh(item)
            refreshed.append(item)
    return refreshed


@router.get("/{product_id}", response_model=StockItemRead)
async def get_stock(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> StockItem:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    return item


@router.get("/{product_id}/movements", response_model=list[StockMovementRead])
async def list_movements(
    product_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[StockMovement]:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    result = await session.execute(
        select(StockMovement)
        .where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/{product_id}/entries", response_model=StockItemRead, status_code=201)
async def add_entry(
    product_id: uuid.UUID,
    payload: MovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    await _apply_movement(
        session,
        item,
        "entry",
        quantity=payload.quantity,
        note=payload.note,
        correlation_id=_correlation_id(request),
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/{product_id}/exits", response_model=StockItemRead, status_code=201)
async def add_exit(
    product_id: uuid.UUID,
    payload: MovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    await _apply_movement(
        session,
        item,
        "exit",
        quantity=payload.quantity,
        note=payload.note,
        correlation_id=_correlation_id(request),
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/{product_id}/adjustments", response_model=StockItemRead, status_code=201)
async def adjust_stock(
    product_id: uuid.UUID,
    payload: AdjustmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    await _apply_movement(
        session,
        item,
        "adjustment",
        quantity=payload.quantity,
        note=payload.note,
        correlation_id=_correlation_id(request),
    )
    await session.commit()
    await session.refresh(item)
    return item
