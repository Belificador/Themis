from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx
from egm_common.logging import CorrelationIdMiddleware, configure_logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import settings

logger = logging.getLogger(__name__)


def _correlation_headers(request: Request) -> dict[str, str]:
    correlation_id: Optional[str] = getattr(request.state, "correlation_id", None)
    return {"x-correlation-id": correlation_id} if correlation_id else {}


async def _proxy(request: Request, base_url: str, path: str) -> Response:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if path else base_url
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _correlation_headers(request)
    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type
    body = await request.body()

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        try:
            upstream = await client.request(
                request.method, url, content=body or None, headers=headers
            )
        except httpx.HTTPError as exc:
            logger.error("upstream error url=%s: %s", url, exc)
            raise HTTPException(status_code=502, detail=f"upstream unavailable: {exc}")

    excluded = {
        "content-encoding",
        "transfer-encoding",
        "connection",
        "content-length",
        "keep-alive",
    }
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in excluded
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


def create_app() -> FastAPI:
    configure_logging(settings.service_name, settings.log_level)

    app = FastAPI(title="Themis API Gateway", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.api_route(
        "/api/catalog",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["catalog"],
    )
    @app.api_route(
        "/api/catalog/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["catalog"],
    )
    async def catalog_proxy(request: Request, path: str = "") -> Response:
        return await _proxy(request, settings.catalog_url, path or "products")

    @app.api_route(
        "/api/inventory",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["inventory"],
    )
    @app.api_route(
        "/api/inventory/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["inventory"],
    )
    async def inventory_proxy(request: Request, path: str = "") -> Response:
        return await _proxy(request, settings.inventory_url, path or "stock")

    @app.api_route(
        "/api/notifications",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["notifications"],
    )
    @app.api_route(
        "/api/notifications/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["notifications"],
    )
    async def notifications_proxy(request: Request, path: str = "") -> Response:
        suffix = f"notifications/{path}" if path else "notifications"
        return await _proxy(request, settings.notification_url, suffix)

    @app.api_route(
        "/api/sales",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["sales"],
    )
    @app.api_route(
        "/api/sales/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["sales"],
    )
    async def sales_proxy(request: Request, path: str = "") -> Response:
        suffix = f"sales/{path}" if path else "sales"
        return await _proxy(request, settings.sales_url, suffix)

    @app.get("/api/dashboard", tags=["dashboard"])
    async def dashboard(request: Request) -> JSONResponse:
        headers = _correlation_headers(request)
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            try:
                products_response, stock_response = await asyncio.gather(
                    client.get(
                        f"{settings.catalog_url}/products?limit=500", headers=headers
                    ),
                    client.get(f"{settings.inventory_url}/stock", headers=headers),
                )
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502, detail=f"upstream unavailable: {exc}"
                )

        if products_response.status_code != 200:
            raise HTTPException(
                status_code=products_response.status_code,
                detail=products_response.text,
            )
        if stock_response.status_code != 200:
            raise HTTPException(
                status_code=stock_response.status_code, detail=stock_response.text
            )

        products = products_response.json()
        stock_by_id = {
            item["product_id"]: item for item in stock_response.json()
        }

        rows = []
        for product in products:
            stock = stock_by_id.get(product["id"])
            quantity = int(stock["quantity"]) if stock else 0
            threshold = int(
                stock["threshold"] if stock else product.get("threshold", 0)
            )
            rows.append(
                {
                    **product,
                    "quantity": quantity,
                    "threshold": threshold,
                    "low_stock": quantity <= threshold,
                    "alert_state": stock["alert_state"] if stock else "pending",
                    "active": stock["active"] if stock else True,
                    "stock_synced": stock is not None,
                }
            )

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

        return JSONResponse(
            {
                "count": len(rows),
                "low_stock_count": sum(1 for row in rows if row["low_stock"]),
                "total_units": sum(int(row["quantity"]) for row in rows),
                "totals": totals,
                "products": rows,
            }
        )

    @app.get("/health", tags=["health"])
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "service": settings.service_name})

    static_dir = Path(settings.static_dir)
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:

        @app.get("/", include_in_schema=False)
        async def frontend_not_built() -> JSONResponse:
            return JSONResponse(
                {
                    "service": settings.service_name,
                    "message": "frontend bundle not found; run the Vite dev server or build it",
                    "static_dir": str(static_dir),
                }
            )

    return app


app = create_app()
