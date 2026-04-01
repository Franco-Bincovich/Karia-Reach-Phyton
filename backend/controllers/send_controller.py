"""
Controller de envio — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from typing import Optional

from services import send_service


async def enviar_campana(
    nombre: str, template_id: str, contact_ids: list[str],
    scheduled_at: Optional[str], usuario_id: str = None,
) -> dict:
    """Crea y ejecuta una campana de email."""
    campana = await send_service.enviar_campana(nombre, template_id, contact_ids, scheduled_at, usuario_id)
    return {"data": campana}


async def listar_campanas(usuario_id: str = None) -> dict:
    """Devuelve todas las campanas."""
    campanas = await send_service.listar_campanas(usuario_id)
    return {"data": campanas, "total": len(campanas)}


async def obtener_dashboard(usuario_id: str = None) -> dict:
    """Devuelve el dashboard con totales del sistema."""
    dashboard = await send_service.obtener_dashboard(usuario_id)
    return {"data": dashboard}


async def estadisticas_campana(campaign_id: str) -> dict:
    """Estadisticas detalladas de una campana."""
    stats = await send_service.obtener_estadisticas_campana(campaign_id)
    return {"data": stats}


async def estadisticas_globales() -> dict:
    """Estadisticas agregadas de todas las campanas."""
    stats = await send_service.obtener_estadisticas_globales()
    return {"data": stats}
