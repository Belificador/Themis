from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .schemas import TestResult

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/test", response_model=TestResult)
async def test_notifications(channel: str = "all") -> TestResult:
    results = []
    if channel in ("all", "telegram"):
        results.append({"channel": "telegram", "status": "dry_run", "detail": "no credentials configured"})
    if channel in ("all", "whatsapp"):
        results.append({"channel": "whatsapp", "status": "dry_run", "detail": "no credentials configured"})
    return TestResult(event_id="test", results=results)
