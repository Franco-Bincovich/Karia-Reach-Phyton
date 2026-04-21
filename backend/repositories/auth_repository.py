"""
Repositorio de autenticacion — acceso a tabla `usuarios_reach`.

Campos: id, nombre, email, password_hash, rol, activo, created_at, updated_at.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

from typing import Optional

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "usuarios_reach"

_QUERY = """
    SELECT id, nombre, email, password_hash, rol, activo, created_at, updated_at
    FROM usuarios_reach
    WHERE email = $1 AND activo = true
    LIMIT 1
"""


async def buscar_usuario_por_email(email: str) -> Optional[dict]:
    """
    Busca un usuario activo por email usando asyncpg/Postgres.

    Args:
        email: direccion de email del usuario.

    Returns:
        Dict del usuario o None si no existe/inactivo.
        Keys: id (str), nombre, email, password_hash, rol, activo (bool),
        created_at (str ISO), updated_at (str ISO o None).
    """
    try:
        async with get_pool().acquire() as conn:
            record = await conn.fetchrow(_QUERY, email)

        if record is None:
            return None

        row = dict(record)
        row["id"] = str(row["id"])
        if row.get("created_at") is not None:
            row["created_at"] = row["created_at"].isoformat()
        if row.get("updated_at") is not None:
            row["updated_at"] = row["updated_at"].isoformat()
        return row

    except AppError:
        raise
    except Exception as exc:
        log.error("Error buscando usuario %s: %s", email, exc)
        raise AppError("Error al buscar usuario", "DB_AUTH_SEARCH", 500) from exc
