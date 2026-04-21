"""
Repositorio de templates — unico punto de acceso a la tabla `templates`.

Campos: id, nombre, asunto, cuerpo, tono, objetivo, usuario_id, created_at, updated_at.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "templates"

_COLUMNAS_PERMITIDAS = frozenset({
    "nombre", "asunto", "cuerpo", "tono", "objetivo",
    "usuario_id", "created_at", "updated_at",
})


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in row.items():
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los templates ordenados por fecha de creacion desc."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                rows = await conn.fetch(
                    "SELECT * FROM templates WHERE usuario_id = $1 ORDER BY created_at DESC",
                    uuid.UUID(usuario_id),
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM templates ORDER BY created_at DESC"
                )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando templates: %s", exc)
        raise AppError("Error al listar templates", "DB_TEMPLATES_LIST", 500) from exc


async def contar(usuario_id: str = None) -> int:
    """Devuelve el total de templates."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM templates WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
                )
            else:
                result = await conn.fetchval("SELECT COUNT(*) FROM templates")
        return int(result or 0)
    except Exception as exc:
        log.error("Error contando templates: %s", exc)
        raise AppError("Error al contar templates", "DB_TEMPLATES_COUNT", 500) from exc


async def crear(template: dict) -> dict:
    """
    Inserta un template nuevo.

    Args:
        template: dict con nombre, asunto, cuerpo, tono, objetivo, usuario_id.

    Returns:
        Dict del template creado con id y timestamps.
    """
    try:
        datos = {k: v for k, v in template.items() if k in _COLUMNAS_PERMITIDAS}
        if "usuario_id" in datos and isinstance(datos["usuario_id"], str):
            datos["usuario_id"] = uuid.UUID(datos["usuario_id"])
        cols = list(datos.keys())
        vals = list(datos.values())
        placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
        query = (
            f"INSERT INTO templates ({', '.join(cols)}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Template creado: %s", template.get("nombre"))
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error creando template: %s", exc)
        raise AppError("Error al crear template", "DB_TEMPLATES_CREATE", 500) from exc


async def eliminar(id: str) -> bool:
    """
    Elimina un template por id.

    Args:
        id: UUID del template.

    Returns:
        True si se elimino, False si no existia.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM templates WHERE id = $1 RETURNING id",
                uuid.UUID(id),
            )
        eliminado = row is not None
        if eliminado:
            log.info("Template eliminado: %s", id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando template %s: %s", id, exc)
        raise AppError("Error al eliminar template", "DB_TEMPLATES_DELETE", 500) from exc
