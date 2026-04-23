"""
Repositorio de estadísticas de campanas — resultados individuales y agregados.
"""
from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict
from .campaigns_crud_repository import (
    _coerce_timestamp, _COLUMNAS_RESULTS, listar,
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
        return record_to_dict(row)
    except Exception as exc:
        log.error("Error creando resultado de campana: %s", exc)
        raise AppError("Error al registrar resultado", "DB_RESULTS_CREATE", 500) from exc


async def listar_resultados(campana_id: str, usuario_id: str) -> list[dict]:
    """Lista resultados de envio de una campana, filtrados por propiedad del usuario."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                """SELECT cr.* FROM campaign_results cr
                   JOIN campaigns c ON c.id = cr.campaign_id
                   WHERE cr.campaign_id = $1 AND c.usuario_id = $2
                   ORDER BY cr.enviado_at DESC""",
                uuid.UUID(campana_id), uuid.UUID(usuario_id),
            )
        return [record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando resultados de campana %s: %s", campana_id, exc)
        raise AppError("Error al listar resultados", "DB_RESULTS_LIST", 500) from exc


async def obtener_estadisticas_campana(campaign_id: str, usuario_id: str) -> dict:
    """Estadisticas detalladas: metricas + resultados individuales."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM campaigns WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(campaign_id), uuid.UUID(usuario_id),
            )
        if not row:
            raise AppError("Acceso denegado a esta campana", "CAMPAIGN_NOT_FOUND", 403)
        c = record_to_dict(row)
        resultados = await listar_resultados(campaign_id, usuario_id)

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


async def obtener_estadisticas_globales(usuario_id: str) -> dict:
    """Estadisticas agregadas del usuario."""
    try:
        campanas = await listar(usuario_id)
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                """SELECT cr.* FROM campaign_results cr
                   JOIN campaigns c ON c.id = cr.campaign_id
                   WHERE c.usuario_id = $1""",
                uuid.UUID(usuario_id),
            )
        resultados = [record_to_dict(r) for r in rows]

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        base = enviados

        async with get_pool().acquire() as conn:
            respondidos = await conn.fetchval(
                """SELECT COUNT(*) FROM email_replies er
                   JOIN campaigns c ON c.id = er.campaign_id
                   WHERE c.usuario_id = $1""",
                uuid.UUID(usuario_id),
            )
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
