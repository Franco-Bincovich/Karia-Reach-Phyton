"""
Repositorio de campanas programadas — acceso a `campanas_programadas`.

Funciones: crear, listar, obtener, obtener_sin_usuario,
           listar_programadas, actualizar_estado, cancelar.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, time as time_type

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
_TABLE = "campanas_programadas"

_COLUMNAS_PROG = frozenset({
    "nombre", "usuario_id", "template_id", "bloque_id", "estado",
    "tipo", "contact_ids", "dias_semana", "hora_envio", "fecha_envio", "ultima_ejecucion",
})
_COLUMNAS_JSONB = frozenset({"contact_ids", "dias_semana"})
_COLUMNAS_UUID = frozenset({"template_id", "bloque_id", "usuario_id"})
_COLUMNAS_TIMESTAMPS = frozenset({"fecha_envio", "ultima_ejecucion"})


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
        elif key in _COLUMNAS_JSONB:
            if isinstance(val, str):
                try:
                    row[key] = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    row[key] = []
            elif val is None:
                row[key] = []
    return row


def _coerce_timestamp(col: str, val):
    """Si col es timestamp y val es string ISO, convertirlo a datetime."""
    if col in _COLUMNAS_TIMESTAMPS and isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return val
    return val


async def crear(usuario_id: str, datos: dict) -> dict:
    """Inserta una campana programada nueva."""
    try:
        merged = {**datos, "usuario_id": usuario_id}
        filtered = {k: v for k, v in merged.items() if k in _COLUMNAS_PROG}
        cols, placeholders, vals = [], [], []
        for i, (col, val) in enumerate(filtered.items(), 1):
            cols.append(col)
            placeholders.append(f"${i}")
            if col in _COLUMNAS_UUID and isinstance(val, str) and val:
                val = uuid.UUID(val)
            elif col in _COLUMNAS_JSONB and not isinstance(val, str):
                val = json.dumps(val)
            val = _coerce_timestamp(col, val)
            if col == "hora_envio" and isinstance(val, str):
                h, m = val.split(":")
                val = time_type(int(h), int(m))
            vals.append(val)
        query = (
            f"INSERT INTO {_TABLE} ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Campana programada creada: %s", datos.get("nombre"))
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error creando campana programada: %s", exc)
        raise AppError("Error al crear campana programada", "DB_CAMPANA_PROG_CREATE", 500) from exc


async def listar(usuario_id: str) -> list[dict]:
    """Devuelve las campanas programadas del usuario, desc por creacion."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM {_TABLE} WHERE usuario_id = $1 ORDER BY created_at DESC",
                uuid.UUID(usuario_id),
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando campanas programadas: %s", exc)
        raise AppError("Error al listar campanas programadas", "DB_CAMPANA_PROG_LIST", 500) from exc


async def obtener(campana_id: str, usuario_id: str) -> dict:
    """Obtiene una campana por ID validando que pertenezca al usuario."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {_TABLE} WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(campana_id),
                uuid.UUID(usuario_id),
            )
        if not row:
            raise AppError("Campana programada no encontrada", "CAMPANA_PROG_NOT_FOUND", 404)
        return _record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo campana programada %s: %s", campana_id, exc)
        raise AppError("Error al obtener campana programada", "DB_CAMPANA_PROG_GET", 500) from exc


async def obtener_sin_usuario(campana_id: str) -> dict:
    """Obtiene una campana por ID sin filtro de usuario (uso interno del scheduler)."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {_TABLE} WHERE id = $1 LIMIT 1",
                uuid.UUID(campana_id),
            )
        if not row:
            raise AppError("Campana programada no encontrada", "CAMPANA_PROG_NOT_FOUND", 404)
        return _record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Error al obtener campana programada", "DB_CAMPANA_PROG_GET", 500) from exc


async def listar_programadas() -> list[dict]:
    """Lista todas las campanas con estado 'programada' (para el scheduler al arrancar)."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM {_TABLE} WHERE estado = 'programada'"
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando campanas activas: %s", exc)
        raise AppError("Error al listar campanas activas", "DB_CAMPANA_PROG_ACTIVAS", 500) from exc


async def actualizar_estado(
    campana_id: str, estado: str, ultima_ejecucion: str | None = None
) -> None:
    """Actualiza estado y opcionalmente ultima_ejecucion de una campana."""
    try:
        if ultima_ejecucion:
            ue = _coerce_timestamp("ultima_ejecucion", ultima_ejecucion)
            async with get_pool().acquire() as conn:
                await conn.execute(
                    f"UPDATE {_TABLE} SET estado = $1, ultima_ejecucion = $2 WHERE id = $3",
                    estado,
                    ue,
                    uuid.UUID(campana_id),
                )
        else:
            async with get_pool().acquire() as conn:
                await conn.execute(
                    f"UPDATE {_TABLE} SET estado = $1 WHERE id = $2",
                    estado,
                    uuid.UUID(campana_id),
                )
    except Exception as exc:
        log.error("Error actualizando estado campana %s: %s", campana_id, exc)
        raise AppError("Error al actualizar estado", "DB_CAMPANA_PROG_UPDATE", 500) from exc


async def cancelar(campana_id: str, usuario_id: str) -> None:
    """Cancela una campana programada verificando propiedad y estado."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                f"UPDATE {_TABLE} SET estado = 'cancelada' "
                "WHERE id = $1 AND usuario_id = $2 AND estado = 'programada'",
                uuid.UUID(campana_id),
                uuid.UUID(usuario_id),
            )
        if not (result.startswith("UPDATE ") and int(result.split()[1]) > 0):
            raise AppError(
                "Campana no encontrada o ya no esta programada",
                "CAMPANA_PROG_NOT_FOUND", 404,
            )
    except AppError:
        raise
    except Exception as exc:
        log.error("Error cancelando campana %s: %s", campana_id, exc)
        raise AppError("Error al cancelar campana", "DB_CAMPANA_PROG_CANCEL", 500) from exc
