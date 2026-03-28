"""
Repositorio de respuestas — acceso a tabla `email_replies`.

Campos: id, campaign_id, contact_id, message_id, in_reply_to,
de, asunto, cuerpo, fecha, leido, respondido.
"""

from __future__ import annotations

from integrations.supabase_client import supabase
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "email_replies"


async def guardar_respuesta(reply: dict) -> dict:
    """Inserta una respuesta de email en la tabla."""
    try:
        resp = supabase.table(_TABLE).insert(reply).execute()
        log.info("Respuesta guardada de %s", reply.get("de"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error guardando respuesta: %s", exc)
        raise AppError("Error al guardar respuesta", "DB_REPLIES_CREATE", 500) from exc


async def listar_por_campana(campaign_id: str) -> list[dict]:
    """Lista todas las respuestas de una campana ordenadas por fecha desc."""
    try:
        resp = (
            supabase.table(_TABLE).select("*")
            .eq("campaign_id", campaign_id)
            .order("fecha", desc=True).execute()
        )
        return resp.data
    except Exception as exc:
        log.error("Error listando respuestas de campana %s: %s", campaign_id, exc)
        raise AppError("Error al listar respuestas", "DB_REPLIES_LIST", 500) from exc


async def obtener_por_id(id: str) -> dict:
    """Obtiene una respuesta por id."""
    try:
        resp = supabase.table(_TABLE).select("*").eq("id", id).limit(1).execute()
        if not resp.data:
            raise AppError("Respuesta no encontrada", "REPLY_NOT_FOUND", 404)
        return resp.data[0]
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo respuesta %s: %s", id, exc)
        raise AppError("Error al obtener respuesta", "DB_REPLIES_GET", 500) from exc


async def buscar_por_message_id(message_id: str) -> list[dict]:
    """Busca respuestas existentes por message_id (para evitar duplicados)."""
    try:
        resp = supabase.table(_TABLE).select("id").eq("message_id", message_id).execute()
        return resp.data
    except Exception as exc:
        log.error("Error buscando por message_id: %s", exc)
        raise AppError("Error al buscar respuesta", "DB_REPLIES_SEARCH", 500) from exc


async def marcar_leida(id: str) -> bool:
    """Marca una respuesta como leida."""
    try:
        resp = supabase.table(_TABLE).update({"leido": True}).eq("id", id).execute()
        return len(resp.data) > 0
    except Exception as exc:
        log.error("Error marcando leida %s: %s", id, exc)
        raise AppError("Error al marcar como leida", "DB_REPLIES_READ", 500) from exc


async def marcar_respondida(id: str) -> bool:
    """Marca una respuesta como respondida."""
    try:
        resp = supabase.table(_TABLE).update({"respondido": True}).eq("id", id).execute()
        return len(resp.data) > 0
    except Exception as exc:
        log.error("Error marcando respondida %s: %s", id, exc)
        raise AppError("Error al marcar como respondida", "DB_REPLIES_RESPOND", 500) from exc
