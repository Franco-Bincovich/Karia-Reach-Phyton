"""
Repositorio de autenticacion — acceso a tabla `usuarios_reach`.

Campos: id, nombre, email, password_hash, rol, activo, created_at.
"""

from __future__ import annotations

from typing import Optional

from integrations.supabase_client import supabase
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "usuarios_reach"


async def buscar_usuario_por_email(email: str) -> Optional[dict]:
    """
    Busca un usuario activo por email.

    Args:
        email: direccion de email del usuario.

    Returns:
        Dict del usuario o None si no existe/inactivo.
    """
    try:
        resp = (
            supabase.table(_TABLE).select("*")
            .eq("email", email).eq("activo", True)
            .limit(1).execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as exc:
        log.error("Error buscando usuario %s: %s", email, exc)
        raise AppError("Error al buscar usuario", "DB_AUTH_SEARCH", 500) from exc
