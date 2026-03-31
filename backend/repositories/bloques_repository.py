"""
Repositorio de bloques — acceso a tablas `bloques` y `bloque_contactos`.

Campos bloques: id, nombre, created_at.
Campos bloque_contactos: id, bloque_id, contacto_id, created_at.
"""

from __future__ import annotations

import asyncio

from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "bloques"
_TABLE_REL = "bloque_contactos"


async def listar() -> list[dict]:
    """Devuelve todos los bloques con cantidad de contactos."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .select("*").order("created_at", desc=True).execute()
        ))
        bloques = resp.data
        # Contar contactos por bloque
        for bloque in bloques:
            count_resp = await loop.run_in_executor(None, lambda bid=bloque["id"]: (
                get_supabase_client().table(_TABLE_REL)
                .select("id", count="exact").eq("bloque_id", bid).execute()
            ))
            bloque["cantidad_contactos"] = count_resp.count or 0
        return bloques
    except Exception as exc:
        log.error("Error listando bloques: %s", exc)
        raise AppError("Error al listar bloques", "DB_BLOQUES_LIST", 500) from exc


async def crear(nombre: str) -> dict:
    """Crea un bloque nuevo."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .insert({"nombre": nombre}).execute()
        ))
        log.info("Bloque creado: %s", nombre)
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando bloque: %s", exc)
        raise AppError("Error al crear bloque", "DB_BLOQUES_CREATE", 500) from exc


async def eliminar(bloque_id: str) -> bool:
    """Elimina un bloque por id (cascade borra relaciones)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .delete().eq("id", bloque_id).execute()
        ))
        eliminado = len(resp.data) > 0
        if eliminado:
            log.info("Bloque eliminado: %s", bloque_id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando bloque %s: %s", bloque_id, exc)
        raise AppError("Error al eliminar bloque", "DB_BLOQUES_DELETE", 500) from exc


async def agregar_contactos(bloque_id: str, contacto_ids: list[str]) -> None:
    """Agrega contactos a un bloque (ignora duplicados)."""
    rows = [{"bloque_id": bloque_id, "contacto_id": cid} for cid in contacto_ids]
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE_REL)
            .upsert(rows, on_conflict="bloque_id,contacto_id", ignore_duplicates=True)
            .execute()
        ))
        log.info("Agregados %d contactos al bloque %s", len(contacto_ids), bloque_id)
    except Exception as exc:
        log.error("Error agregando contactos al bloque: %s", exc)
        raise AppError("Error al agregar contactos", "DB_BLOQUES_ADD", 500) from exc


async def actualizar(bloque_id: str, nombre: str) -> bool:
    """Actualiza el nombre de un bloque."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .update({"nombre": nombre}).eq("id", bloque_id).execute()
        ))
        actualizado = len(resp.data) > 0
        if actualizado:
            log.info("Bloque actualizado: %s -> %s", bloque_id, nombre)
        return actualizado
    except Exception as exc:
        log.error("Error actualizando bloque %s: %s", bloque_id, exc)
        raise AppError("Error al actualizar bloque", "DB_BLOQUES_UPDATE", 500) from exc


async def eliminar_contacto(bloque_id: str, contacto_id: str) -> bool:
    """Elimina un contacto de un bloque."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE_REL)
            .delete().eq("bloque_id", bloque_id).eq("contacto_id", contacto_id)
            .execute()
        ))
        eliminado = len(resp.data) > 0
        if eliminado:
            log.info("Contacto %s eliminado del bloque %s", contacto_id, bloque_id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando contacto del bloque: %s", exc)
        raise AppError("Error al eliminar contacto del bloque", "DB_BLOQUES_REMOVE", 500) from exc


async def obtener_contactos(bloque_id: str) -> list[dict]:
    """Devuelve los contactos completos de un bloque."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE_REL)
            .select("contacto_id, contacts(*)")
            .eq("bloque_id", bloque_id).execute()
        ))
        return [row["contacts"] for row in resp.data if row.get("contacts")]
    except Exception as exc:
        log.error("Error obteniendo contactos del bloque %s: %s", bloque_id, exc)
        raise AppError("Error al obtener contactos", "DB_BLOQUES_GET", 500) from exc
