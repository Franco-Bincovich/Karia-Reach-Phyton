"""
Repositorio de bloques — acceso a tablas `bloques` y `bloques_contactos`.

Campos bloques: id, nombre, created_at.
Campos bloques_contactos: id, bloque_id, contacto_id, created_at.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)

_TABLE = "bloques"
_TABLE_REL = "bloques_contactos"


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los bloques con cantidad de contactos."""
    try:
        uid = uuid.UUID(usuario_id) if usuario_id else None
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT b.*, COALESCE(COUNT(bc.id), 0) AS cantidad_contactos
                FROM bloques b
                LEFT JOIN bloques_contactos bc ON bc.bloque_id = b.id
                WHERE ($1::uuid IS NULL OR b.usuario_id = $1)
                GROUP BY b.id
                ORDER BY b.created_at DESC
                """,
                uid,
            )
        result = []
        for r in rows:
            d = record_to_dict(r)
            d["cantidad_contactos"] = int(d.get("cantidad_contactos", 0))
            result.append(d)
        return result
    except Exception as exc:
        log.error("Error listando bloques: %s", exc)
        raise AppError("Error al listar bloques", "DB_BLOQUES_LIST", 500) from exc


async def crear(nombre: str, usuario_id: str = None) -> dict:
    """Crea un bloque nuevo."""
    try:
        uid = uuid.UUID(usuario_id) if usuario_id else None
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO bloques (nombre, usuario_id) VALUES ($1, $2) RETURNING *",
                nombre,
                uid,
            )
        log.info("Bloque creado: %s", nombre)
        return record_to_dict(row)
    except Exception as exc:
        log.error("Error creando bloque: %s", exc)
        raise AppError("Error al crear bloque", "DB_BLOQUES_CREATE", 500) from exc


async def eliminar(bloque_id: str, usuario_id: str) -> bool:
    """Elimina un bloque por id (cascade borra relaciones en bloques_contactos)."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM bloques WHERE id = $1 AND usuario_id = $2 RETURNING id",
                uuid.UUID(bloque_id), uuid.UUID(usuario_id),
            )
        eliminado = row is not None
        if eliminado:
            log.info("Bloque eliminado: %s", bloque_id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando bloque %s: %s", bloque_id, exc)
        raise AppError("Error al eliminar bloque", "DB_BLOQUES_DELETE", 500) from exc


async def agregar_contactos(bloque_id: str, contacto_ids: list[str], usuario_id: str) -> None:
    """Agrega contactos a un bloque (ignora duplicados)."""
    try:
        bid, uid = uuid.UUID(bloque_id), uuid.UUID(usuario_id)
        async with get_pool().acquire() as conn:
            if not await conn.fetchval(
                "SELECT 1 FROM bloques WHERE id = $1 AND usuario_id = $2", bid, uid
            ):
                raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)
            await conn.executemany(
                "INSERT INTO bloques_contactos (bloque_id, contacto_id) "
                "VALUES ($1, $2) ON CONFLICT (bloque_id, contacto_id) DO NOTHING",
                [(bid, uuid.UUID(cid)) for cid in contacto_ids],
            )
        log.info("Agregados %d contactos al bloque %s", len(contacto_ids), bloque_id)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error agregando contactos al bloque: %s", exc)
        raise AppError("Error al agregar contactos", "DB_BLOQUES_ADD", 500) from exc


async def actualizar(bloque_id: str, nombre: str, usuario_id: str) -> bool:
    """Actualiza el nombre de un bloque."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE bloques SET nombre = $1 WHERE id = $2 AND usuario_id = $3",
                nombre, uuid.UUID(bloque_id), uuid.UUID(usuario_id),
            )
        actualizado = result.startswith("UPDATE ") and int(result.split()[1]) > 0
        if actualizado:
            log.info("Bloque actualizado: %s -> %s", bloque_id, nombre)
        return actualizado
    except Exception as exc:
        log.error("Error actualizando bloque %s: %s", bloque_id, exc)
        raise AppError("Error al actualizar bloque", "DB_BLOQUES_UPDATE", 500) from exc


async def eliminar_contacto(bloque_id: str, contacto_id: str, usuario_id: str) -> bool:
    """Elimina un contacto de un bloque."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "DELETE FROM bloques_contactos WHERE bloque_id = $1 AND contacto_id = $2"
                " AND EXISTS (SELECT 1 FROM bloques WHERE id = $1 AND usuario_id = $3)",
                uuid.UUID(bloque_id), uuid.UUID(contacto_id), uuid.UUID(usuario_id),
            )
        eliminado = result.startswith("DELETE ") and int(result.split()[1]) > 0
        if eliminado:
            log.info("Contacto %s eliminado del bloque %s", contacto_id, bloque_id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando contacto del bloque: %s", exc)
        raise AppError("Error al eliminar contacto del bloque", "DB_BLOQUES_REMOVE", 500) from exc


async def obtener_contactos(bloque_id: str, usuario_id: str) -> list[dict]:
    """Devuelve los contactos completos de un bloque."""
    try:
        bid, uid = uuid.UUID(bloque_id), uuid.UUID(usuario_id)
        async with get_pool().acquire() as conn:
            if not await conn.fetchval(
                "SELECT 1 FROM bloques WHERE id = $1 AND usuario_id = $2", bid, uid
            ):
                raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)
            rows = await conn.fetch(
                "SELECT c.* FROM bloques_contactos bc "
                "JOIN contacts c ON c.id = bc.contacto_id WHERE bc.bloque_id = $1",
                bid,
            )
        return [record_to_dict(r) for r in rows]
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo contactos del bloque %s: %s", bloque_id, exc)
        raise AppError("Error al obtener contactos", "DB_BLOQUES_GET", 500) from exc
