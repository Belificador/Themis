from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Product, StockItem
from ..rates import get_bcv_rates, price_bcv_usd
from ..schemas import ProductRead

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(session: AsyncSession = Depends(get_session)) -> dict:
    products = list(
        (await session.execute(select(Product).order_by(Product.brand, Product.model)))
        .scalars()
        .all()
    )
    stock_items = list((await session.execute(select(StockItem))).scalars().all())
    stock_by_id = {item.product_id: item for item in stock_items}
    factor_info = await get_bcv_rates()
    factor = float(factor_info.get("factor") or 1.0)

    rows = []
    for product in products:
        stock = stock_by_id.get(product.id)
        quantity = int(stock.quantity) if stock else 0
        threshold = int(stock.threshold) if stock else product.threshold
        row = ProductRead.model_validate(product).model_dump(mode="json")
        row.update(
            {
                "quantity": quantity,
                "threshold": threshold,
                "low_stock": quantity <= threshold,
                "alert_state": stock.alert_state if stock else "pending",
                "active": stock.active if stock else True,
                "stock_synced": stock is not None,
                "price_bcv_effective_usd": price_bcv_usd(
                    float(product.price_usd), factor
                ),
            }
        )
        rows.append(row)

    entry: dict[str, float | int | str] = {
        "currency": "USD",
        "units": 0,
        "retail_value": 0.0,
        "bcv_retail_value": 0.0,
        "phone_units": 0,
        "phone_retail_value": 0.0,
        "phone_bcv_retail_value": 0.0,
    }
    for row in rows:
        quantity = int(row["quantity"])
        retail = float(row.get("price_usd") or 0) * quantity
        bcv = float(row.get("price_bcv_effective_usd") or 0) * quantity
        entry["units"] += quantity
        entry["retail_value"] += retail
        entry["bcv_retail_value"] += bcv
        if row.get("category") == "phone":
            entry["phone_units"] += quantity
            entry["phone_retail_value"] += retail
            entry["phone_bcv_retail_value"] += bcv
    for key in (
        "retail_value",
        "bcv_retail_value",
        "phone_retail_value",
        "phone_bcv_retail_value",
    ):
        entry[key] = round(float(entry[key]), 2)

    return {
        "count": len(rows),
        "low_stock_count": sum(1 for row in rows if row["low_stock"]),
        "total_units": sum(int(row["quantity"]) for row in rows),
        "bcv_factor": factor,
        "bcv_rates": factor_info,
        "totals": [entry],
        "products": rows,
    }
