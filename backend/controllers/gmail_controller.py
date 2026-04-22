"""
Controller de Gmail OAuth — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from typing import Optional

from fastapi.responses import RedirectResponse

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import gmail_repository
from services import gmail_oauth_service

log = get_logger(__name__)
settings = get_settings()


def _require_uid(usuario_id: Optional[str]) -> str:
    if not usuario_id:
        raise AppError("Token inválido o expirado", "AUTH_REQUIRED", 401)
    return usuario_id


async def estado(usuario_id: Optional[str]) -> dict:
    """Retorna si el usuario tiene Gmail conectado y el email asociado."""
    uid = _require_uid(usuario_id)
    row = await gmail_repository.obtener_por_usuario(uid)
    if row:
        return {"data": {"conectado": True, "email": row["email"]}}
    return {"data": {"conectado": False, "email": None}}


async def autorizar(usuario_id: Optional[str]) -> dict:
    """Genera la URL de autorización de Google OAuth para el usuario."""
    uid = _require_uid(usuario_id)
    url = gmail_oauth_service.generar_url_autorizacion(uid)
    return {"data": {"url": url}}


async def callback(
    code: Optional[str],
    state: Optional[str],
    error: Optional[str],
) -> RedirectResponse:
    """
    Procesa el callback de Google OAuth.

    En caso de error (parámetro `error` presente o excepción) redirige al frontend
    con ?gmail=error&reason=<código>. En caso de éxito redirige con ?gmail=connected.
    """
    base = settings.frontend_url.rstrip("/")
    if error or not code or not state:
        reason = error or "missing_params"
        log.warning("Gmail OAuth callback con error: %s", reason)
        return RedirectResponse(url=f"{base}/configuracion?gmail=error&reason={reason}")

    try:
        usuario_id = gmail_oauth_service.validar_state(state)
        await gmail_oauth_service.procesar_callback(code=code, usuario_id=usuario_id)
        return RedirectResponse(url=f"{base}/configuracion?gmail=connected")
    except AppError as exc:
        log.warning("Gmail OAuth callback AppError: %s (%s)", exc.message, exc.code)
        return RedirectResponse(url=f"{base}/configuracion?gmail=error&reason={exc.code}")
    except Exception as exc:
        log.error("Gmail OAuth callback error inesperado: %s", exc)
        return RedirectResponse(url=f"{base}/configuracion?gmail=error&reason=unexpected_error")


async def desconectar(usuario_id: Optional[str]) -> dict:
    """Desconecta la integración Gmail del usuario."""
    uid = _require_uid(usuario_id)
    desconectado = await gmail_repository.desconectar(uid)
    if not desconectado:
        raise AppError("No hay integración Gmail activa para este usuario", "GMAIL_NOT_CONNECTED", 404)
    return {"data": {"desconectado": True}}
