from __future__ import annotations

from fastapi import APIRouter

from ..rates import get_bcv_rates

router = APIRouter(prefix="/api/rates", tags=["rates"])


@router.get("/bcv")
async def bcv_rates() -> dict:
    return await get_bcv_rates()
