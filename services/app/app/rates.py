"""Consulta de tasas BCV (dólar paralelo / oficial) vía dolarapi.com.

No requiere clave de API. Los resultados se cachean en memoria durante
``bcv_cache_seconds`` para no saturar el proveedor.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from .config import settings

logger = logging.getLogger(__name__)

_cache: dict = {"value": None, "ts": 0.0}


async def get_bcv_rates(client: Optional[httpx.AsyncClient] = None) -> dict:
    now = time.time()
    if (
        _cache["value"] is not None
        and now - float(_cache["ts"]) < settings.bcv_cache_seconds
    ):
        return dict(_cache["value"])  # type: ignore[arg-type]

    close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10)

    try:
        base = settings.bcv_api_url.rstrip("/")
        oficial = await client.get(f"{base}/oficial")
        paralelo = await client.get(f"{base}/paralelo")
        of = float(oficial.json().get("promedio") or 0)
        pa = float(paralelo.json().get("promedio") or 0)
        value = {
            "oficial": of,
            "paralelo": pa,
            "factor": (pa / of) if of else 1.0,
        }
        _cache["value"] = value
        _cache["ts"] = now
        return value
    except Exception as exc:  # noqa: BLE001 - fall back gracefully
        logger.warning("no se pudo obtener tasa BCV: %s", exc)
        return {"oficial": 0.0, "paralelo": 0.0, "factor": 1.0}
    finally:
        if close:
            await client.aclose()


def price_bcv_usd(price_usd: float, factor: float) -> float:
    from decimal import ROUND_HALF_UP, Decimal

    return float(
        Decimal(str(price_usd * factor)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )
