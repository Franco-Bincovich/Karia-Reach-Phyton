"""
Controller de respuestas — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import replies_service


async def listar_respuestas(campaign_id: str) -> dict:
    """Lista todas las respuestas de una campana."""
    respuestas = await replies_service.listar_respuestas(campaign_id)
    return {"data": respuestas, "total": len(respuestas)}


async def sincronizar(campaign_id: str) -> dict:
    """Sincroniza respuestas nuevas desde Gmail."""
    nuevas = await replies_service.sincronizar_respuestas_campana(campaign_id)
    return {"data": nuevas, "nuevas": len(nuevas)}


async def responder(reply_id: str, cuerpo: str) -> dict:
    """Responde a una respuesta recibida."""
    resultado = await replies_service.responder(reply_id, cuerpo)
    return {"data": resultado}


async def marcar_leida(reply_id: str) -> dict:
    """Marca una respuesta como leida."""
    await replies_service.marcar_leida(reply_id)
    return {"updated": True}
