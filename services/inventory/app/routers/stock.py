from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..domain import evaluate_transition
from ..events import build_stock_event
from ..models import StockItem, StockMovement
from ..outbox import OutboxEvent
from ..schemas import (
    AdjustmentCreate,
    BatchMovementCreate,
    MovementCreate,
    MovementRead,
    StockRead,
)

router = APIRouter(prefix="/stock", tags=["stock"])


def _correlation_id(request: Request) -> Optional[str]:
    return getattr(request.state, "correlation_id", None)


def _row_locks_enabled() -> bool:
    return not settings.database_url.startswith("sqlite")


async def _load_for_update(
    session: AsyncSession, product_id: uuid.UUID
) -> StockItem:
    statement = select(StockItem).where(StockItem.product_id == product_id)
    if _row_locks_enabled():
        statement = statement.with_for_update()
    result = await session.execute(statement)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    return item


async def _load_many_for_update(
    session: AsyncSession, product_ids: list[uuid.UUID]
) -> dict[uuid.UUID, StockItem]:
    statement = select(StockItem).where(StockItem.product_id.in_(product_ids))
    if _row_locks_enabled():
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return {item.product_id: item for item in result.scalars().all()}


def _apply_movement(
    session: AsyncSession,
    request: Request,
    item: StockItem,
    movement_type: str,
    *,
    quantity: int,
    note: Optional[str],
    reference_id: Optional[str] = None,
) -> None:
    before = item.quantity
    if movement_type == "entry":
        after = before + quantity
    elif movement_type == "exit":
        after = before - quantity
        if after < 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"insufficient stock for {item.sku}: "
                    f"current={before}, requested={quantity}"
                ),
            )
    elif movement_type == "adjustment":
        after = quantity
    else:  # pragma: no cover - internal misuse guard
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
            correlation_id=_correlation_id(request),
        )
    )

    threshold = item.threshold or 0
    transition = evaluate_transition(item.alert_state, after, threshold)
    item.alert_state = transition.alert_state
    event_type = transition.event_type

    if event_type is not None:
        event_id = str(uuid.uuid4())
        correlation_id = _correlation_id(request)
        session.add(
            OutboxEvent(
                id=event_id,
                event_type=event_type,
                routing_key=event_type,
                payload=build_stock_event(
                    event_id, event_type, item, correlation_id
                ),
                correlation_id=correlation_id,
            )
        )


async def _mutate(
    session: AsyncSession,
    request: Request,
    product_id: uuid.UUID,
    movement_type: str,
    *,
    quantity: int,
    note: Optional[str],
    reference_id: Optional[str] = None,
) -> StockItem:
    item = await _load_for_update(session, product_id)
    if not item.active:
        raise HTTPException(status_code=409, detail="product is inactive")

    _apply_movement(
        session,
        request,
        item,
        movement_type,
        quantity=quantity,
        note=note,
        reference_id=reference_id,
    )
    await session.commit()
    await session.refresh(item)
    return item


async def _existing_batch(
    session: AsyncSession,
    product_ids: list[uuid.UUID],
    reference_id: Optional[str],
    movement_type: str,
) -> Optional[list[StockItem]]:
    if not reference_id:
        return None
    result = await session.execute(
        select(StockMovement.product_id).where(
            StockMovement.reference_id == reference_id,
            StockMovement.movement_type == movement_type,
        )
    )
    if not result.scalars().all():
        return None
    items = await _load_many_for_update(session, product_ids)
    found = [items[product_id] for product_id in product_ids if product_id in items]
    return found or None


async def _mutate_batch(
    session: AsyncSession,
    request: Request,
    movement_type: str,
    payload: BatchMovementCreate,
) -> list[StockItem]:
    product_ids = [item.product_id for item in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400, detail="duplicate product_id in batch"
        )

    existing = await _existing_batch(
        session, product_ids, payload.reference_id, movement_type
    )
    if existing is not None:
        return existing

    items = await _load_many_for_update(session, product_ids)
    missing = [str(product_id) for product_id in product_ids if product_id not in items]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"stock item not found: {', '.join(missing)}",
        )

    inactive = [
        items[product_id].sku
        for product_id in product_ids
        if not items[product_id].active
    ]
    if inactive:
        raise HTTPException(
            status_code=409,
            detail=f"product is inactive: {', '.join(inactive)}",
        )

    if movement_type == "exit":
        for requested in payload.items:
            item = items[requested.product_id]
            if item.quantity < requested.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"insufficient stock for {item.sku}: "
                        f"current={item.quantity}, "
                        f"requested={requested.quantity}"
                    ),
                )

    for requested in payload.items:
        _apply_movement(
            session,
            request,
            items[requested.product_id],
            movement_type,
            quantity=requested.quantity,
            note=payload.note,
            reference_id=payload.reference_id,
        )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await _existing_batch(
            session, product_ids, payload.reference_id, movement_type
        )
        if existing is not None:
            return existing
        raise HTTPException(
            status_code=409, detail="batch movement conflict, retry"
        )

    refreshed: list[StockItem] = []
    for product_id in product_ids:
        item = await session.get(StockItem, product_id)
        if item is not None:
            await session.refresh(item)
            refreshed.append(item)
    return refreshed


@router.get("", response_model=list[StockRead])
async def list_stock(
    include_inactive: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[StockItem]:
    stmt = select(StockItem).order_by(StockItem.updated_at.desc())
    if not include_inactive:
        stmt = stmt.where(StockItem.active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/batch-exits", response_model=list[StockRead], status_code=201)
async def batch_exits(
    payload: BatchMovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[StockItem]:
    return await _mutate_batch(session, request, "exit", payload)


@router.post("/batch-entries", response_model=list[StockRead], status_code=201)
async def batch_entries(
    payload: BatchMovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[StockItem]:
    return await _mutate_batch(session, request, "entry", payload)


@router.get("/{product_id}", response_model=StockRead)
async def get_stock(
    product_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> StockItem:
    item = await session.get(StockItem, product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="stock item not found")
    return item


@router.get("/{product_id}/movements", response_model=list[MovementRead])
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


@router.post("/{product_id}/entries", response_model=StockRead, status_code=201)
async def add_entry(
    product_id: uuid.UUID,
    payload: MovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    return await _mutate(
        session,
        request,
        product_id,
        "entry",
        quantity=payload.quantity,
        note=payload.note,
    )


@router.post("/{product_id}/exits", response_model=StockRead, status_code=201)
async def add_exit(
    product_id: uuid.UUID,
    payload: MovementCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    return await _mutate(
        session,
        request,
        product_id,
        "exit",
        quantity=payload.quantity,
        note=payload.note,
    )


@router.post("/{product_id}/adjustments", response_model=StockRead, status_code=201)
async def adjust_stock(
    product_id: uuid.UUID,
    payload: AdjustmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StockItem:
    return await _mutate(
        session,
        request,
        product_id,
        "adjustment",
        quantity=payload.quantity,
        note=payload.note,
    )
