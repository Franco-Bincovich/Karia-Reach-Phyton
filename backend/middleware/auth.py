"""
Middleware de autenticacion por API Key.

Valida el header `Authorization: Bearer {key}` contra KARIA_API_KEY.
El endpoint /health queda excluido.
"""

import hmac

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from config.settings import get_settings
from logger import get_logger

log = get_logger(__name__)

# Rutas que no requieren autenticacion
PUBLIC_PATHS = {"/health"}
# /track/ es publico porque los pixels de apertura se cargan desde clientes
# de email (Gmail, Outlook) que no envian headers de autenticacion.
PUBLIC_PREFIXES = ("/track/",)


class AuthMiddleware(BaseHTTPMiddleware):
    """Valida API Key en cada request (excepto rutas publicas)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Intercepta el request y verifica la API Key."""
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()

        # Comparacion en tiempo constante para evitar timing attacks
        if not token or not hmac.compare_digest(token, settings.KARIA_API_KEY):
            log.warning("Auth fallida desde %s en %s", request.client.host, request.url.path)
            return JSONResponse(
                status_code=401,
                content={"error": True, "message": "No autorizado", "code": "UNAUTHORIZED"},
            )

        return await call_next(request)
