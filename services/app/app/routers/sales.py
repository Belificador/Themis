from __future__ import annotations

import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..invoices import attach_invoice, clear_invoice_metadata, invoice_storage_path, _supabase_delete, _supabase_signed_url, _use_supabase
from ..models import Sale
from ..schemas import Currency, SaleCreate, SaleRead
from ..service import create_sale, delete_sale, get_sale, list_sales, sales_summary

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.post("", response_model=SaleRead, status_code=201)
async def register_sale(payload: SaleCreate, session: AsyncSession = Depends(get_session)) -> Sale:
    return await create_sale(session, payload)


@router.get("", response_model=list[SaleRead])
async def get_sales(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), status: Optional[str] = Query(default=None), search: Optional[str] = Query(default=None), session: AsyncSession = Depends(get_session)) -> list[Sale]:
    return await list_sales(session, limit=limit, offset=offset, status=status, search=search)


@router.get("/summary")
async def get_summary(currency: Currency = Query(default="USD"), session: AsyncSession = Depends(get_session)) -> dict:
    return await sales_summary(session, currency=currency)


@router.post("/{sale_id}/invoice", response_model=SaleRead)
async def upload_invoice(sale_id: uuid.UUID, file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> Sale:
    sale = await get_sale(session, sale_id)
    await attach_invoice(sale, file)
    await session.commit()
    return await get_sale(session, sale.id)


@router.get("/{sale_id}/invoice-url")
async def get_invoice_url(sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    sale = await get_sale(session, sale_id)
    storage_path = invoice_storage_path(sale)
    if not storage_path:
        raise HTTPException(status_code=404, detail="invoice not found")
    if _use_supabase() and settings.supabase_service_role_key and sale.invoice_stored_name:
        download_url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{settings.supabase_bucket_invoices}/{storage_path}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                download_url,
                headers={"Authorization": f"Bearer {settings.supabase_service_role_key}"},
            )
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type=sale.invoice_content_type or "application/octet-stream",
                    headers={"Cache-Control": "public, max-age=86400"},
                )
            raise HTTPException(
                status_code=resp.status_code,
                detail="Error al obtener factura de Supabase",
            )
    # Servir desde almacenamiento local
    if sale.invoice_stored_name:
        path = Path(settings.media_dir) / sale.invoice_stored_name
        if path.is_file():
            return FileResponse(
                path,
                media_type=sale.invoice_content_type or "application/octet-stream",
                filename=Path(path).name,
                content_disposition_type="inline",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    raise HTTPException(status_code=404, detail="invoice not found")


@router.delete("/{sale_id}/invoice", status_code=204)
async def delete_invoice(sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Response:
    sale = await get_sale(session, sale_id)
    if _use_supabase() and settings.supabase_service_role_key and sale.invoice_stored_name:
        await _supabase_delete(sale.invoice_stored_name)
    elif sale.invoice_stored_name:
        path = Path(settings.media_dir) / sale.invoice_stored_name
        if path.is_file():
            path.unlink(missing_ok=True)
    clear_invoice_metadata(sale)
    await session.commit()
    return Response(status_code=204)


@router.get("/{sale_id}", response_model=SaleRead)
async def get_sale_detail(sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Sale:
    return await get_sale(session, sale_id)


@router.delete("/{sale_id}", status_code=204)
async def delete_sale_endpoint(sale_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Response:
    await delete_sale(session, sale_id)
    return Response(status_code=204)
