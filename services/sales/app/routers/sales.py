from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..invoices import (
    attach_invoice,
    clear_invoice_metadata,
    invoice_storage_path,
    _supabase_delete,
    _supabase_signed_url,
    _use_supabase,
)
from ..models import Sale
from ..schemas import Currency, SaleCreate, SaleRead
from ..service import create_sale, get_sale, list_sales, sales_summary

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleRead, status_code=201)
async def register_sale(
    payload: SaleCreate, session: AsyncSession = Depends(get_session)
) -> Sale:
    return await create_sale(session, payload)


@router.get("", response_model=list[SaleRead])
async def get_sales(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[Sale]:
    return await list_sales(
        session, limit=limit, offset=offset, status=status, search=search
    )


@router.get("/summary")
async def get_summary(
    currency: Currency = Query(default="EUR"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await sales_summary(session, currency=currency)


@router.post("/{sale_id}/invoice", response_model=SaleRead)
async def upload_invoice(
    sale_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> Sale:
    sale = await get_sale(session, sale_id)
    await attach_invoice(sale, file)
    await session.commit()
    return await get_sale(session, sale.id)


@router.get("/{sale_id}/invoice-url")
async def get_invoice_url(
    sale_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    sale = await get_sale(session, sale_id)
    storage_path = invoice_storage_path(sale)
    if not storage_path:
        raise HTTPException(status_code=404, detail="invoice not found")
    signed = await _supabase_signed_url(storage_path)
    return {"url": signed}


@router.delete("/{sale_id}/invoice", status_code=204)
async def delete_invoice(
    sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    sale = await get_sale(session, sale_id)
    if _use_supabase() and sale.invoice_stored_name:
        await _supabase_delete(sale.invoice_stored_name)
    clear_invoice_metadata(sale)
    await session.commit()
    return Response(status_code=204)


@router.get("/{sale_id}", response_model=SaleRead)
async def get_sale_detail(
    sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Sale:
    return await get_sale(session, sale_id)
