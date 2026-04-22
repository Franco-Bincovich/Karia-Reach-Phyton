"""
Repositorio de estadísticas de campanas — resultados individuales y agregados.
"""
from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from .campaigns_crud_repository import (
    _record_to_dict, _coerce_timestamp, _COLUMNAS_RESULTS, listar,
)

log = get_logger(__name__)


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
            vals.append(_coerce_timestamp(col, val))
        query = f"INSERT INTO campaign_results ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING *"
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
                "SELECT * FROM campaigns WHERE id = $1 LIMIT 1", uuid.UUID(campaign_id),
            )
        if not row:
            raise AppError("Campana no encontrada", "CAMPAIGN_NOT_FOUND", 404)
        c = _record_to_dict(row)
        resultados = await listar_resultados(campaign_id)

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        total = len(resultados)

        async with get_pool().acquire() as conn:
            respondidos = await conn.fetchval(
                "SELECT COUNT(*) FROM email_replies WHERE campaign_id = $1", uuid.UUID(campaign_id),
            )
        respondidos = int(respondidos or 0)

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

        async with get_pool().acquire() as conn:
            respondidos = await conn.fetchval("SELECT COUNT(*) FROM email_replies")
        respondidos = int(respondidos or 0)

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
