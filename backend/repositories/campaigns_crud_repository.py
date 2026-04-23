"""
Repositorio CRUD de campanas — acceso a `campaigns` y escritura de resultados en `campaign_results`.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)

_CAMPAIGNS = "campaigns"
_RESULTS = "campaign_results"

_COLUMNAS_CAMPAIGNS = frozenset({
    "nombre", "template_id", "contacts_count", "sent_count", "failed_count",
    "status", "scheduled_at", "sent_at", "usuario_id",
})

_COLUMNAS_RESULTS = frozenset({
    "campaign_id", "contact_id", "email_destinatario", "asunto", "exitoso",
    "message_id", "error", "enviado_at", "opened_at", "respondido",
})

_COLUMNAS_TIMESTAMPS = frozenset({"enviado_at", "opened_at", "scheduled_at", "sent_at"})


def _coerce_timestamp(col: str, val):
    """Si col es timestamp y val es string ISO, convertirlo a datetime."""
    if col in _COLUMNAS_TIMESTAMPS and isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except ValueError:
            return val
    return val


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todas las campanas ordenadas por creacion desc."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                rows = await conn.fetch(
                    "SELECT * FROM campaigns WHERE usuario_id = $1 ORDER BY created_at DESC",
                    uuid.UUID(usuario_id),
                )
            else:
                rows = await conn.fetch("SELECT * FROM campaigns ORDER BY created_at DESC")
        return [record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando campanas: %s", exc)
        raise AppError("Error al listar campanas", "DB_CAMPAIGNS_LIST", 500) from exc


async def contar(usuario_id: str = None) -> int:
    """Cuenta total de campanas (query liviana)."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM campaigns WHERE usuario_id = $1", uuid.UUID(usuario_id),
                )
            else:
                result = await conn.fetchval("SELECT COUNT(*) FROM campaigns")
        return int(result or 0)
    except Exception as exc:
        log.error("Error contando campanas: %s", exc)
        raise AppError("Error al contar campanas", "DB_CAMPAIGNS_COUNT", 500) from exc


async def sumar_enviados(usuario_id: str = None) -> int:
    """Suma sent_count de todas las campanas."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                result = await conn.fetchval(
                    "SELECT COALESCE(SUM(sent_count), 0) FROM campaigns WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
                )
            else:
                result = await conn.fetchval("SELECT COALESCE(SUM(sent_count), 0) FROM campaigns")
        return int(result or 0)
    except Exception as exc:
        log.error("Error sumando enviados: %s", exc)
        raise AppError("Error al sumar enviados", "DB_CAMPAIGNS_SUM", 500) from exc


async def crear(campana: dict) -> dict:
    """Crea una campana nueva."""
    try:
        datos = {k: v for k, v in campana.items() if k in _COLUMNAS_CAMPAIGNS}
        cols, placeholders, vals = [], [], []
        for i, (col, val) in enumerate(datos.items(), 1):
            cols.append(col)
            placeholders.append(f"${i}::campaign_status" if col == "status" else f"${i}")
            if col in ("usuario_id", "template_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            vals.append(_coerce_timestamp(col, val))
        query = f"INSERT INTO campaigns ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING *"
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Campana creada: %s", campana.get("nombre"))
        return record_to_dict(row)
    except Exception as exc:
        log.error("Error creando campana: %s", exc)
        raise AppError("Error al crear campana", "DB_CAMPAIGNS_CREATE", 500) from exc


async def actualizar_metricas(id: str, metricas: dict) -> dict:
    """Actualiza metricas de una campana."""
    try:
        datos = {k: v for k, v in metricas.items() if k in _COLUMNAS_CAMPAIGNS}
        if not datos:
            async with get_pool().acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM campaigns WHERE id = $1 LIMIT 1", uuid.UUID(id))
            if not row:
                raise AppError("Campana no encontrada", "DB_CAMPAIGNS_NOT_FOUND", 404)
            log.info("actualizar_metricas %s: dict vacio, nada que actualizar", id)
            return record_to_dict(row)
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(datos.items(), 1):
            set_clauses.append(f"{col} = ${i}::campaign_status" if col == "status" else f"{col} = ${i}")
            if col in ("usuario_id", "template_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            vals.append(_coerce_timestamp(col, val))
        vals.append(uuid.UUID(id))
        query = f"UPDATE campaigns SET {', '.join(set_clauses)} WHERE id = ${len(vals)} RETURNING *"
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        if not row:
            raise AppError("Campana no encontrada", "DB_CAMPAIGNS_NOT_FOUND", 404)
        log.info("Metricas actualizadas para campana %s", id)
        return record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error actualizando metricas de campana %s: %s", id, exc)
        raise AppError("Error al actualizar metricas", "DB_CAMPAIGNS_UPDATE", 500) from exc
