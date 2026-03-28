"""
Punto de entrada de Karia Reach Backend.

Configura FastAPI con CORS, security headers, rate limiting,
error handling y registra los routers.
"""

import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.settings import get_settings
from logger import get_logger
from middleware.auth import AuthMiddleware
from middleware.error_handler import AppError, app_error_handler, generic_error_handler
from middleware.rate_limiter import limiter
from routes import apollo, compose, contacts, replies, send, tracking

log = get_logger(__name__)
settings = get_settings()


# --- Security Headers (equivalente a helmet en Express) ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Agrega headers de seguridad a cada respuesta."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Inyecta headers de seguridad estilo helmet."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response


# --- Lifespan (startup + shutdown) ---

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Maneja startup y shutdown de la aplicacion."""
    _log_startup_status()

    # Graceful shutdown ante SIGTERM (Docker stop)
    def handle_sigterm(signum: int, frame: object) -> None:  # noqa: ARG001
        """Captura SIGTERM para cerrar limpiamente."""
        log.info("SIGTERM recibido — cerrando...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    log.info("Karia Reach Backend listo en puerto %s", settings.PORT)
    yield
    log.info("Karia Reach Backend cerrado")


def _log_startup_status() -> None:
    """Loguea el estado de las variables criticas al arrancar."""
    checks = {
        "SUPABASE_URL": bool(settings.SUPABASE_URL),
        "SUPABASE_SERVICE_KEY": bool(settings.SUPABASE_SERVICE_KEY),
        "ANTHROPIC_API_KEY": bool(settings.ANTHROPIC_API_KEY),
        "GMAIL_CLIENT_ID": bool(settings.GMAIL_CLIENT_ID),
        "KARIA_API_KEY": bool(settings.KARIA_API_KEY),
    }
    for var, ok in checks.items():
        status = "OK" if ok else "FALTA"
        level = log.info if ok else log.warning
        level("  %s: %s", var, status)
    # Checks de seguridad criticos — el servidor NO arranca sin estas variables
    if len(settings.SECRET_KEY) < 16:
        log.error("  SECRET_KEY: FALTA o muy corta (min 16 chars) — ABORTANDO")
        sys.exit(1)
    if len(settings.KARIA_API_KEY) < 16:
        log.error("  KARIA_API_KEY: FALTA o muy corta (min 16 chars) — ABORTANDO")
        sys.exit(1)
    if not settings.ENCRYPTION_KEY:
        log.warning("  ENCRYPTION_KEY: FALTA — API keys de terceros se guardaran SIN cifrar")


# --- App ---

app = FastAPI(
    title="Karia Reach Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Middlewares (se ejecutan en orden inverso al de registro)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Error handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# Routers
app.include_router(contacts.router)
app.include_router(compose.router)
app.include_router(send.router)
app.include_router(replies.router)
app.include_router(apollo.router)
app.include_router(tracking.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Endpoint de health check — sin autenticacion."""
    return {"status": "ok", "service": "karia-reach-backend"}
