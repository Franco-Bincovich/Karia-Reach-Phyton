"""
Repositorio de campanas — acceso a tablas `campaigns` y `campaign_results`.

campaigns: id, nombre, template_id, contacts_count, status, sent_count,
           failed_count, scheduled_at, sent_at, created_at.
campaign_results: id, campaign_id, contact_id, email_destinatario, asunto,
                  message_id, exitoso, error, enviado_at, opened_at.
"""

from __future__ import annotations

from integrations.supabase_client import supabase
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_CAMPAIGNS = "campaigns"
_RESULTS = "campaign_results"


async def listar() -> list[dict]:
    """Devuelve todas las campanas ordenadas por fecha de creacion desc."""
    try:
        resp = supabase.table(_CAMPAIGNS).select("*").order("created_at", desc=True).execute()
        return resp.data
    except Exception as exc:
        log.error("Error listando campanas: %s", exc)
        raise AppError("Error al listar campanas", "DB_CAMPAIGNS_LIST", 500) from exc


async def crear(campana: dict) -> dict:
    """Crea una campana nueva en la tabla campaigns."""
    try:
        resp = supabase.table(_CAMPAIGNS).insert(campana).execute()
        log.info("Campana creada: %s", campana.get("nombre"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando campana: %s", exc)
        raise AppError("Error al crear campana", "DB_CAMPAIGNS_CREATE", 500) from exc


async def actualizar_metricas(id: str, metricas: dict) -> dict:
    """Actualiza metricas de una campana (sent_count, failed_count, status)."""
    try:
        resp = supabase.table(_CAMPAIGNS).update(metricas).eq("id", id).execute()
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
    """Registra el resultado del envio de un email en campaign_results."""
    try:
        resp = supabase.table(_RESULTS).insert(resultado).execute()
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando resultado de campana: %s", exc)
        raise AppError("Error al registrar resultado", "DB_RESULTS_CREATE", 500) from exc


async def listar_resultados(campana_id: str) -> list[dict]:
    """Lista todos los resultados de envio de una campana."""
    try:
        resp = (
            supabase.table(_RESULTS).select("*")
            .eq("campaign_id", campana_id)
            .order("enviado_at", desc=True).execute()
        )
        return resp.data
    except Exception as exc:
        log.error("Error listando resultados de campana %s: %s", campana_id, exc)
        raise AppError("Error al listar resultados", "DB_RESULTS_LIST", 500) from exc


async def obtener_estadisticas_campana(campaign_id: str) -> dict:
    """Estadisticas detalladas de una campana: metricas agregadas + resultados."""
    try:
        resp = supabase.table(_CAMPAIGNS).select("*").eq("id", campaign_id).limit(1).execute()
        if not resp.data:
            raise AppError("Campana no encontrada", "CAMPAIGN_NOT_FOUND", 404)
        c = resp.data[0]
        resultados = await listar_resultados(campaign_id)

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        total = len(resultados) or 1  # or 1 evita division por cero si no hay resultados

        return {
            "campana": {k: c.get(k) for k in ("nombre", "status", "created_at", "scheduled_at")},
            "total_enviados": enviados,
            "total_fallidos": fallidos,
            "total_abiertos": abiertos,
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
    """Estadisticas agregadas de todas las campanas."""
    try:
        campanas = await listar()
        resultados = supabase.table(_RESULTS).select("*").execute().data

        enviados = sum(1 for r in resultados if r.get("exitoso"))
        fallidos = sum(1 for r in resultados if not r.get("exitoso"))
        abiertos = sum(1 for r in resultados if r.get("opened_at"))
        base = enviados or 1  # or 1 evita division por cero

        return {
            "total_campanas": len(campanas),
            "total_emails_enviados": enviados,
            "total_emails_fallidos": fallidos,
            "total_aperturas": abiertos,
            "tasa_apertura_global": round(abiertos / base * 100, 2),
        }
    except Exception as exc:
        log.error("Error obteniendo estadisticas globales: %s", exc)
        raise AppError("Error al obtener estadisticas globales", "DB_GLOBAL_STATS", 500) from exc
