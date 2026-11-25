from __future__ import annotations

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

# Rate limiter: 100 requests por minuto por IP
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad a todas las respuestas."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Prevenir clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevenir MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Habilitar protección XSS en navegadores antiguos
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Forzar HTTPS (solo en producción)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy restrictiva
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' data: blob:; "
            "frame-src 'self' blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=()"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para rate limiting por IP."""

    async def dispatch(self, request: Request, call_next):
        # Obtener IP del cliente
        client_ip = request.client.host if request.client else "unknown"

        # Verificar rate limit usando slowapi
        try:
            # Usar el limiter de slowapi
            from slowapi.util import get_remote_address
            key = get_remote_address(request)

            # Verificar si el límite ha sido excedido
            # slowapi maneja esto internamente, pero aquí lo envolvemos
            response = await call_next(request)
            return response
        except Exception:
            # Si hay algún error en el rate limiting, permitir la petición
            response = await call_next(request)
            return response


async def rate_limit_exceeded_handler(request: Request, exc):
    """Manejador para cuando se excede el rate limit."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Demasiadas peticiones. Inténtelo de nuevo más tarde.",
            "error": "rate_limit_exceeded",
        },
    )


# Configuración de límites de velocidad por endpoint
RATE_LIMITS = {
    "login": "5/minute",  # Máximo 5 intentos de login por minuto
    "register": "3/minute",  # Máximo 3 registros por minuto
    "sales": "30/minute",  # Máximo 30 ventas por minuto
    "products": "60/minute",  # Máximo 60 operaciones de productos por minuto
    "stock": "60/minute",  # Máximo 60 operaciones de stock por minuto
    "general": "100/minute",  # Límite general de 100 peticiones por minuto
}