"""Structured JSON logging with request-scoped correlation ids."""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def current_correlation_id() -> str:
    return correlation_id_ctx.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", os.getenv("SERVICE_NAME", "service")),
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": current_correlation_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


class _ServiceFilter(logging.Filter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service_name
        return True


def configure_logging(service_name: str, level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_ServiceFilter(service_name))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    logging.getLogger("httpx").setLevel(logging.WARNING)


def log_extra(**fields: Any) -> dict[str, Any]:
    """Convenience helper for ``logger.info(..., extra={"extra_fields": ...})``."""
    return {"extra_fields": fields}


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Propagates `X-Correlation-ID`, generating one when absent."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        token = correlation_id_ctx.set(correlation_id)
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)
        response.headers["x-correlation-id"] = correlation_id
        return response
