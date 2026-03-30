"""
Repositorio de campanas — acceso a `campaigns` y `campaign_results`.
Respondidos se calculan via JOIN con `email_replies`.
"""

from __future__ import annotations

import asyncio

from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_CAMPAIGNS = "campaigns"
_RESULTS = "campaign_results"


async def listar() -> list[dict]:
    """Devuelve todas las campanas ordenadas por creacion desc."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).select("*")
            .order("created_at", desc=True).execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando campanas: %s", exc)
        raise AppError("Error al listar campanas", "DB_CAMPAIGNS_LIST", 500) from exc

async def contar() -> int:
    """Cuenta total de campanas (query liviana)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).select("id", count="exact").execute()
        ))
        return resp.count or 0
    except Exception as exc:
        log.error("Error contando campanas: %s", exc)
        raise AppError("Error al contar campanas", "DB_CAMPAIGNS_COUNT", 500) from exc

async def sumar_enviados() -> int:
    """Suma sent_count de todas las campanas."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).select("sent_count").execute()
        ))
        return sum(c.get("sent_count", 0) for c in resp.data)
    except Exception as exc:
        log.error("Error sumando enviados: %s", exc)
        raise AppError("Error al sumar enviados", "DB_CAMPAIGNS_SUM", 500) from exc

async def crear(campana: dict) -> dict:
    """Crea una campana nueva."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).insert(campana).execute()
        ))
        log.info("Campana creada: %s", campana.get("nombre"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando campana: %s", exc)
        raise AppError("Error al crear campana", "DB_CAMPAIGNS_CREATE", 500) from exc

async def actualizar_metricas(id: str, metricas: dict) -> dict:
    """Actualiza metricas de una campana."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).update(metricas).eq("id", id).execute()
        ))
        if not resp.data:
            raise AppError("Campana no encontrada", "DB_CAMPAIGNS_NOT_FOUND", 404)
        log.info("Metricas actualizadas para campana %s", id)
        return resp.data[0]
    except AppError:
        raise
    except Exception as exc:
        log.error("Error actualizando metricas de campana %s: %s", id, exc)
        raise AppError("Error al actualizar metricas", "DB_CAMPAIGNS_UPDATE", 500) from exc

async def crear_resultado(resultado: dict) -> dict:
    """Registra resultado de envio en campaign_results."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_RESULTS).insert(resultado).execute()
        ))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando resultado de campana: %s", exc)
        raise AppError("Error al registrar resultado", "DB_RESULTS_CREATE", 500) from exc

async def listar_resultados(campana_id: str) -> list[dict]:
    """Lista resultados de envio de una campana."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_RESULTS).select("*").eq(
                "campaign_id", campana_id).order("enviado_at", desc=True).execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando resultados de campana %s: %s", campana_id, exc)
        raise AppError("Error al listar resultados", "DB_RESULTS_LIST", 500) from exc

async def obtener_estadisticas_campana(campaign_id: str) -> dict:
    """Estadisticas detalladas: metricas + resultados individuales."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_CAMPAIGNS).select("*")
            .eq("id", campaign_id).limit(1).execute()
        ))
        if not resp.data:
            raise AppError("Campana no encontrada", "CAMPAIGN_NOT_FOUND", 404)
        c = resp.data[0]
        resultados = await listar_resultados(campaign_id)

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        total = len(resultados) or 1
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
            "tasa_apertura": round(abiertos / total * 100, 2),
            "tasa_fallo": round(fallidos / total * 100, 2),
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
        loop = asyncio.get_event_loop()
        campanas = await listar()
        resultados_resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_RESULTS).select("*").execute()
        ))
        resultados = resultados_resp.data

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        base = enviados or 1
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
            "tasa_apertura_global": round(abiertos / base * 100, 2),
        }
    except Exception as exc:
        log.error("Error obteniendo estadisticas globales: %s", exc)
        raise AppError("Error al obtener estadisticas globales", "DB_GLOBAL_STATS", 500) from exc
