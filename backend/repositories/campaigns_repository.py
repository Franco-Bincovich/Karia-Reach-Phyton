"""
Repositorio de campanas — acceso a `campaigns` y `campaign_results`.
Respondidos se calculan via email_replies (todavia en Supabase — se migra en paso 2.5).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from integrations.postgres_client import get_pool
from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

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


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


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
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando campanas: %s", exc)
        raise AppError("Error al listar campanas", "DB_CAMPAIGNS_LIST", 500) from exc


async def contar(usuario_id: str = None) -> int:
    """Cuenta total de campanas (query liviana)."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM campaigns WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
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
                result = await conn.fetchval(
                    "SELECT COALESCE(SUM(sent_count), 0) FROM campaigns"
                )
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
            if col == "status":
                placeholders.append(f"${i}::campaign_status")
            else:
                placeholders.append(f"${i}")
            if col in ("usuario_id", "template_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            val = _coerce_timestamp(col, val)
            vals.append(val)
        query = (
            f"INSERT INTO campaigns ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Campana creada: %s", campana.get("nombre"))
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error creando campana: %s", exc)
        raise AppError("Error al crear campana", "DB_CAMPAIGNS_CREATE", 500) from exc


async def actualizar_metricas(id: str, metricas: dict) -> dict:
    """Actualiza metricas de una campana."""
    try:
        datos = {k: v for k, v in metricas.items() if k in _COLUMNAS_CAMPAIGNS}
        if not datos:
            async with get_pool().acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM campaigns WHERE id = $1 LIMIT 1",
                    uuid.UUID(id),
                )
            if not row:
                raise AppError("Campana no encontrada", "DB_CAMPAIGNS_NOT_FOUND", 404)
            log.info("actualizar_metricas %s: dict vacio o invalido, nada que actualizar", id)
            return _record_to_dict(row)
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(datos.items(), 1):
            if col == "status":
                set_clauses.append(f"{col} = ${i}::campaign_status")
            else:
                set_clauses.append(f"{col} = ${i}")
            if col in ("usuario_id", "template_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            val = _coerce_timestamp(col, val)
            vals.append(val)
        vals.append(uuid.UUID(id))
        query = (
            f"UPDATE campaigns SET {', '.join(set_clauses)} "
            f"WHERE id = ${len(vals)} RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        if not row:
            raise AppError("Campana no encontrada", "DB_CAMPAIGNS_NOT_FOUND", 404)
        log.info("Metricas actualizadas para campana %s", id)
        return _record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error actualizando metricas de campana %s: %s", id, exc)
        raise AppError("Error al actualizar metricas", "DB_CAMPAIGNS_UPDATE", 500) from exc


async def crear_resultado(resultado: dict) -> dict:
    """Registra resultado de envio en campaign_results."""
    try:
        datos = {k: v for k, v in resultado.items() if k in _COLUMNAS_RESULTS}
        cols, placeholders, vals = [], [], []
        for i, (col, val) in enumerate(datos.items(), 1):
            cols.append(col)
            placeholders.append(f"${i}")
            if col in ("campaign_id", "contact_id") and isinstance(val, str) and val:
                val = uuid.UUID(val)
            val = _coerce_timestamp(col, val)
            vals.append(val)
        query = (
            f"INSERT INTO campaign_results ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error creando resultado de campana: %s", exc)
        raise AppError("Error al registrar resultado", "DB_RESULTS_CREATE", 500) from exc


async def listar_resultados(campana_id: str) -> list[dict]:
    """Lista resultados de envio de una campana."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM campaign_results WHERE campaign_id = $1 ORDER BY enviado_at DESC",
                uuid.UUID(campana_id),
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando resultados de campana %s: %s", campana_id, exc)
        raise AppError("Error al listar resultados", "DB_RESULTS_LIST", 500) from exc


async def obtener_estadisticas_campana(campaign_id: str) -> dict:
    """Estadisticas detalladas: metricas + resultados individuales."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM campaigns WHERE id = $1 LIMIT 1",
                uuid.UUID(campaign_id),
            )
        if not row:
            raise AppError("Campana no encontrada", "CAMPAIGN_NOT_FOUND", 404)
        c = _record_to_dict(row)
        resultados = await listar_resultados(campaign_id)

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        total = len(resultados)

        # email_replies todavia en Supabase — se migra en paso 2.5
        loop = asyncio.get_event_loop()
        replies = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table("email_replies").select("id")
            .eq("campaign_id", campaign_id).execute()
        ))
        respondidos = len(replies.data)

        return {
            "campana": {k: c.get(k) for k in ("nombre", "status", "created_at", "scheduled_at")},
            "total_enviados": enviados,
            "total_fallidos": fallidos,
            "total_abiertos": abiertos,
            "total_sin_abrir": enviados - abiertos,
            "total_respondidos": respondidos,
            "tasa_apertura": round(abiertos / total * 100, 1) if total > 0 else None,
            "tasa_fallo": round(fallidos / total * 100, 1) if total > 0 else None,
            "resultados": [
                {k: r.get(k) for k in
                 ("email_destinatario", "asunto", "exitoso", "enviado_at", "opened_at", "error")}
                for r in resultados
            ],
        }
    except AppError:
        raise
    except Exception as exc:
        log.error("Error estadisticas campana %s: %s", campaign_id, exc)
        raise AppError("Error al obtener estadisticas", "DB_CAMPAIGN_STATS", 500) from exc


async def obtener_estadisticas_globales() -> dict:
    """Estadisticas agregadas globales."""
    try:
        campanas = await listar()
        async with get_pool().acquire() as conn:
            rows = await conn.fetch("SELECT * FROM campaign_results")
        resultados = [_record_to_dict(r) for r in rows]

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        base = enviados

        # email_replies todavia en Supabase — se migra en paso 2.5
        loop = asyncio.get_event_loop()
        all_replies = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table("email_replies").select("id").execute()
        ))
        respondidos = len(all_replies.data)

        return {
            "total_campanas": len(campanas),
            "total_emails_enviados": enviados,
            "total_emails_fallidos": fallidos,
            "total_aperturas": abiertos,
            "total_respondidos": respondidos,
            "tasa_apertura_global": round(abiertos / base * 100, 1) if base > 0 else None,
        }
    except Exception as exc:
        log.error("Error obteniendo estadisticas globales: %s", exc)
        raise AppError("Error al obtener estadisticas globales", "DB_GLOBAL_STATS", 500) from exc
