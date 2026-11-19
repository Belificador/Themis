from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..invoices import attach_invoice, clear_invoice, invoice_path
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


@router.get("/{sale_id}/invoice")
async def download_invoice(
    sale_id: uuid.UUID,
    download: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    sale = await get_sale(session, sale_id)
    path = invoice_path(sale)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="invoice not found")
    return FileResponse(
        path,
        media_type=sale.invoice_content_type or "application/octet-stream",
        filename=sale.invoice_filename or path.name,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.delete("/{sale_id}/invoice", status_code=204)
async def delete_invoice(
    sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    sale = await get_sale(session, sale_id)
    clear_invoice(sale)
    await session.commit()
    return Response(status_code=204)


@router.get("/{sale_id}", response_model=SaleRead)
async def get_sale_detail(
    sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Sale:
    return await get_sale(session, sale_id)
