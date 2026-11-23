from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Product, StockItem
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
            }
        )
        rows.append(row)

    totals = []
    for currency, price_key, cost_key in (
        ("EUR", "price_eur", "cost_price_eur"),
        ("USD", "price_usd", "cost_price_usd"),
    ):
        entry: dict[str, float | int | str] = {
            "currency": currency,
            "units": 0,
            "retail_value": 0.0,
            "cost_value": 0.0,
            "phone_units": 0,
            "phone_retail_value": 0.0,
            "phone_cost_value": 0.0,
        }
        for row in rows:
            quantity = int(row["quantity"])
            retail = float(row.get(price_key) or 0) * quantity
            cost = float(row.get(cost_key) or 0) * quantity
            entry["units"] += quantity
            entry["retail_value"] += retail
            entry["cost_value"] += cost
            if row.get("category") == "phone":
                entry["phone_units"] += quantity
                entry["phone_retail_value"] += retail
                entry["phone_cost_value"] += cost
        for key in (
            "retail_value",
            "cost_value",
            "phone_retail_value",
            "phone_cost_value",
        ):
            entry[key] = round(float(entry[key]), 2)
        totals.append(entry)

    return {
        "count": len(rows),
        "low_stock_count": sum(1 for row in rows if row["low_stock"]),
        "total_units": sum(int(row["quantity"]) for row in rows),
        "totals": totals,
        "products": rows,
    }
