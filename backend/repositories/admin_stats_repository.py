"""
Admin stats repository — queries SQL de lectura para el panel de administracion.
"""
from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)


async def listar_usuarios() -> list[dict]:
    """Lista usuarios con stats de contactos y campanas."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id, u.nombre, u.email, u.rol, u.created_at,
                       COUNT(DISTINCT c.id)    AS total_contactos,
                       COUNT(DISTINCT camp.id) AS total_campanas,
                       COALESCE(SUM(camp.sent_count), 0) AS total_emails_enviados
                FROM usuarios_reach u
                LEFT JOIN contacts   c    ON c.usuario_id    = u.id
                LEFT JOIN campaigns  camp ON camp.usuario_id = u.id
                GROUP BY u.id, u.nombre, u.email, u.rol, u.created_at
                ORDER BY u.created_at DESC
                """
            )
        result = []
        for r in rows:
            d = record_to_dict(r)
            d["total_contactos"] = int(d.get("total_contactos", 0))
            d["total_campanas"] = int(d.get("total_campanas", 0))
            d["total_emails_enviados"] = int(d.get("total_emails_enviados", 0))
            result.append(d)
        return result
    except Exception as exc:
        log.error("Error listando usuarios: %s", exc)
        raise AppError("Error al listar usuarios", "DB_ADMIN_USERS_LIST", 500) from exc


async def obtener_usuario_por_id(usuario_id: str) -> dict | None:
    """Obtiene un usuario por id. Retorna None si no existe."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM usuarios_reach WHERE id = $1 LIMIT 1", uuid.UUID(usuario_id)
            )
        return record_to_dict(row) if row else None
    except Exception as exc:
        log.error("Error obteniendo usuario %s: %s", usuario_id, exc)
        raise AppError("Error al obtener usuario", "DB_ADMIN_USER_GET", 500) from exc


async def obtener_contactos_usuario(usuario_id: str, limit: int = 20) -> list[dict]:
    """Retorna los ultimos N contactos del usuario."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM contacts WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT $2",
                uuid.UUID(usuario_id), limit,
            )
        return [record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error obteniendo contactos usuario %s: %s", usuario_id, exc)
        raise AppError("Error al obtener contactos", "DB_ADMIN_CONTACTS_GET", 500) from exc


async def obtener_campanas_usuario(usuario_id: str, limit: int = 10) -> list[dict]:
    """Retorna las ultimas N campanas del usuario."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM campaigns WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT $2",
                uuid.UUID(usuario_id), limit,
            )
        return [record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error obteniendo campanas usuario %s: %s", usuario_id, exc)
        raise AppError("Error al obtener campanas", "DB_ADMIN_CAMPAIGNS_GET", 500) from exc


async def obtener_contadores_usuario(usuario_id: str) -> dict:
    """Retorna total_contactos y total_emails del usuario."""
    try:
        uid = uuid.UUID(usuario_id)
        async with get_pool().acquire() as conn:
            total_c = await conn.fetchval(
                "SELECT COUNT(*) FROM contacts WHERE usuario_id = $1", uid
            )
            total_e = await conn.fetchval(
                "SELECT COALESCE(SUM(sent_count), 0) FROM campaigns WHERE usuario_id = $1", uid
            )
        return {"total_contactos": int(total_c or 0), "total_emails": int(total_e or 0)}
    except Exception as exc:
        log.error("Error obteniendo contadores usuario %s: %s", usuario_id, exc)
        raise AppError("Error al obtener contadores", "DB_ADMIN_COUNTERS_GET", 500) from exc


async def obtener_integraciones_usuario(usuario_id: str) -> list[str]:
    """Retorna servicios activos del usuario. Falla silenciosamente."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT servicio FROM integraciones WHERE activo = true AND usuario_id = $1",
                uuid.UUID(usuario_id),
            )
        return [r["servicio"] for r in rows]
    except Exception as exc:
        log.warning("Error obteniendo integraciones usuario %s: %s", usuario_id, exc)
        return []


async def obtener_metodos_habilitados(usuario_id: str) -> list | None:
    """Retorna metodos_habilitados, o None si la columna es NULL.

    Raises:
        AppError: USER_NOT_FOUND (404) si el usuario no existe.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT metodos_habilitados FROM usuarios_reach WHERE id = $1 LIMIT 1",
                uuid.UUID(usuario_id),
            )
        if row is None:
            raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
        return list(row["metodos_habilitados"]) if row["metodos_habilitados"] else None
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo metodos usuario %s: %s", usuario_id, exc)
        raise AppError("Error al obtener metodos", "DB_ADMIN_METODOS_GET", 500) from exc
