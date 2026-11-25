from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from ..config import settings
from ..db import get_session
from ..models import Product, StockItem, Sale, SaleItem

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _build_sales_excel(sales: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"

    header = [
        "Nº Venta",
        "Fecha",
        "Cliente",
        "Vendedor",
        "Método de pago",
        "Moneda",
        "Total",
        "Estado",
    ]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            start_color="1FA6A6", end_color="1FA6A6", fill_type="solid"
        )
        cell.alignment = Alignment(horizontal="center")

    for s in sales:
        ws.append(
            [
                s.sale_number,
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                s.customer_name or "",
                s.vendedor or "",
                s.payment_method,
                s.currency,
                float(s.total),
                s.status,
            ]
        )

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 40)
        ws.column_dimensions[column].width = adjusted_width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _build_stock_excel(products: list, stock_items: list) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"

    header = [
        "SKU",
        "Producto",
        "Marca",
        "Modelo",
        "Categoría",
        "Stock",
        "Umbral",
        "Estado",
        "PVP USD",
        "Ref. BCV",
        "Cashea",
    ]
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            start_color="1FA6A6", end_color="1FA6A6", fill_type="solid"
        )
        cell.alignment = Alignment(horizontal="center")

    stock_by_id = {item.product_id: item for item in stock_items}
    for p in products:
        stock = stock_by_id.get(p.id)
        quantity = int(stock.quantity) if stock else 0
        threshold = int(stock.threshold) if stock else 0
        if quantity == 0:
            estado = "Sin stock"
        elif quantity <= threshold:
            estado = "Bajo stock"
        else:
            estado = "Disponible"
        ws.append(
            [
                p.sku,
                p.product_name,
                p.brand,
                p.model,
                p.category,
                quantity,
                threshold,
                estado,
                float(p.price_usd),
                float(p.price_bcv_usd),
                float(p.price_cashea_usd),
            ]
        )

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 40)
        ws.column_dimensions[column].width = adjusted_width

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@router.get("/export-sales")
async def export_sales(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Sale).order_by(Sale.created_at.desc()))
    sales = list(result.scalars().all())
    if not sales:
        raise HTTPException(status_code=404, detail="No hay ventas para exportar")

    file_bytes = _build_sales_excel(sales)
    filename = f"ventas_{settings.now_venezuela().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export-stock")
async def export_stock(session: AsyncSession = Depends(get_session)):
    result_products = await session.execute(
        select(Product).order_by(Product.brand, Product.model)
    )
    products = list(result_products.scalars().all())
    result_stock = await session.execute(select(StockItem))
    stock_items = list(result_stock.scalars().all())
    if not products:
        raise HTTPException(status_code=404, detail="No hay productos para exportar")

    file_bytes = _build_stock_excel(products, stock_items)
    filename = f"stock_{settings.now_venezuela().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
