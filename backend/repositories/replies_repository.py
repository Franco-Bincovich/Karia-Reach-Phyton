"""
Repositorio de respuestas — acceso a tabla `email_replies`.

Campos: id, campaign_id, contact_id, message_id, in_reply_to,
de, asunto, cuerpo, fecha, leido, respondido.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import uuid
from typing import Optional

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)

_TABLE = "email_replies"

_COLUMNAS_REPLIES = frozenset({
    "campaign_id", "contact_id", "message_id", "in_reply_to",
    "de", "asunto", "cuerpo", "fecha", "leido", "respondido",
})

_COLUMNAS_TIMESTAMPS = frozenset({"fecha"})


def _coerce_timestamp(col: str, val):
    """Si col es timestamp y val es string ISO, convertirlo a datetime."""
    if col in _COLUMNAS_TIMESTAMPS and isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return val
    return val


async def guardar_respuesta(reply: dict) -> dict:
    """Inserta una respuesta de email en la tabla."""
    try:
        datos = {k: v for k, v in reply.items() if k in _COLUMNAS_REPLIES}
        cols, placeholders, vals = [], [], []
        for i, (col, val) in enumerate(datos.items(), 1):
            cols.append(col)
            placeholders.append(f"${i}")
            if col in ("campaign_id", "contact_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            val = _coerce_timestamp(col, val)
            vals.append(val)
        query = (
            f"INSERT INTO email_replies ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Respuesta guardada de %s", reply.get("de"))
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error guardando respuesta: %s", exc)
        raise AppError("Error al guardar respuesta", "DB_REPLIES_CREATE", 500) from exc


async def verificar_campana_usuario(campaign_id: str, usuario_id: str) -> bool:
    """Verifica que una campana pertenezca al usuario dado.

    Args:
        campaign_id: UUID de la campana.
        usuario_id: UUID del usuario que realiza la operacion.

    Returns:
        True si la campana pertenece al usuario.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM campaigns WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(campaign_id),
                uuid.UUID(usuario_id),
            )
        return row is not None
    except Exception as exc:
        log.error("Error verificando ownership campana %s: %s", campaign_id, exc)
        return False


async def listar_por_campana(campaign_id: str) -> list[dict]:
    """Lista todas las respuestas de una campana ordenadas por fecha desc."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM email_replies WHERE campaign_id = $1 ORDER BY fecha DESC",
                uuid.UUID(campaign_id),
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando respuestas de campana %s: %s", campaign_id, exc)
        raise AppError("Error al listar respuestas", "DB_REPLIES_LIST", 500) from exc


async def obtener_por_id(id: str) -> dict:
    """Obtiene una respuesta por id."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM email_replies WHERE id = $1 LIMIT 1",
                uuid.UUID(id),
            )
        if not row:
            raise AppError("Respuesta no encontrada", "REPLY_NOT_FOUND", 404)
        return _record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo respuesta %s: %s", id, exc)
        raise AppError("Error al obtener respuesta", "DB_REPLIES_GET", 500) from exc


async def buscar_por_message_id(message_id: str) -> list[dict]:
    """Busca respuestas existentes por message_id (para evitar duplicados)."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM email_replies WHERE message_id = $1",
                message_id,
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error buscando por message_id: %s", exc)
        raise AppError("Error al buscar respuesta", "DB_REPLIES_SEARCH", 500) from exc


async def marcar_leida(id: str) -> bool:
    """Marca una respuesta como leida."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE email_replies SET leido = true WHERE id = $1",
                uuid.UUID(id),
            )
        return result.startswith("UPDATE ") and int(result.split()[1]) > 0
    except Exception as exc:
        log.error("Error marcando leida %s: %s", id, exc)
        raise AppError("Error al marcar como leida", "DB_REPLIES_READ", 500) from exc


async def marcar_respondida(id: str) -> bool:
    """Marca una respuesta como respondida."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE email_replies SET respondido = true WHERE id = $1",
                uuid.UUID(id),
            )
        return result.startswith("UPDATE ") and int(result.split()[1]) > 0
    except Exception as exc:
        log.error("Error marcando respondida %s: %s", id, exc)
        raise AppError("Error al marcar como respondida", "DB_REPLIES_RESPOND", 500) from exc
