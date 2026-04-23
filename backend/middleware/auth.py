"""
Middleware de autenticacion dual: API Key y JWT.

Acepta tanto KARIA_API_KEY (para scripts/integraciones directas)
como JWT firmado con JWT_SECRET (para el frontend).
"""

import hmac

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

# Rutas que no requieren autenticacion
PUBLIC_PATHS = {"/health"}
# /track/ es publico porque los pixels se cargan desde clientes de correo.
# /api/auth/ es publico para permitir login sin token previo.
PUBLIC_PREFIXES = ("/track/", "/api/auth/", "/api/gmail/oauth/callback")


def get_rol_from_request(request: Request) -> str:
    """Extrae el rol del JWT del request. Devuelve 'user' si no se puede determinar."""
    settings = get_settings()
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token or not settings.JWT_SECRET:
        return "user"
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"],
                             audience="karia-reach", issuer="karia-reach-backend")
        return payload.get("rol", "user")
    except jwt.PyJWTError:
        return "user"


def get_usuario_id_from_request(request: Request) -> str:
    """Extrae el usuario_id del request.state (establecido por el middleware JWT).

    Raises:
        AppError: UNAUTHORIZED (401) si el request no tiene un JWT valido.
    """
    uid = getattr(request.state, "usuario_id", None)
    if not uid:
        raise AppError("No autorizado", "UNAUTHORIZED", 401)
    return uid


class AuthMiddleware(BaseHTTPMiddleware):
    """Valida API Key o JWT en cada request (excepto rutas publicas)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Intercepta el request y verifica credenciales."""
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        settings = get_settings()
        auth_header = request.headers.get("Authorization", "")
        log.debug("AUTH header recibido: '%s' (starts Bearer: %s)", auth_header[:20], auth_header.startswith("Bearer "))
        token = auth_header.removeprefix("Bearer ").strip()

        if not token:
            log.debug("AUTH token vacio despues de strip")
            return self._unauthorized(request)

        # Intento 1: verificar como API Key (comparacion en tiempo constante)
        if settings.KARIA_API_KEY and hmac.compare_digest(token, settings.KARIA_API_KEY):
            return await call_next(request)

        # Intento 2: verificar como JWT
        if settings.JWT_SECRET:
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"],
                                     audience="karia-reach", issuer="karia-reach-backend")
                request.state.usuario_id = payload.get("usuario_id")
                return await call_next(request)
            except jwt.ExpiredSignatureError:
                log.warning("JWT expirado desde %s", request.client.host if request.client else "unknown")
                return JSONResponse(
                    status_code=401,
                    content={"error": True, "message": "Sesion expirada", "code": "TOKEN_EXPIRED"},
                )
            except jwt.InvalidTokenError as exc:
                log.debug("JWT decode fallo: %s — token[:20]='%s'", exc, token[:20])
                return self._unauthorized(request)

        return self._unauthorized(request)

    @staticmethod
    def _unauthorized(request: Request) -> JSONResponse:
        """Respuesta 401 generica."""
        host = request.client.host if request.client else "unknown"
        log.warning("Auth fallida desde %s en %s", host, request.url.path)
        return JSONResponse(
            status_code=401,
            content={"error": True, "message": "No autorizado", "code": "UNAUTHORIZED"},
        )
