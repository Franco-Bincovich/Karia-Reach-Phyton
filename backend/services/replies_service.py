"""
Servicio de respuestas — sincronizacion con Gmail, lectura y respuesta.
"""

from __future__ import annotations

from integrations import gmail_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import campaigns_repository, replies_repository

log = get_logger(__name__)


async def sincronizar_respuestas_campana(campaign_id: str) -> list[dict]:
    """
    Sincroniza respuestas de Gmail para una campana.

    Obtiene message_ids de los resultados exitosos, busca respuestas
    en Gmail y guarda las nuevas evitando duplicados por message_id.

    Args:
        campaign_id: UUID de la campana.

    Returns:
        Lista de respuestas nuevas encontradas y guardadas.
    """
    resultados = await campaigns_repository.listar_resultados(campaign_id)
    # Solo los que tienen message_id (enviados exitosamente)
    message_ids = [r["message_id"] for r in resultados if r.get("message_id")]
    if not message_ids:
        return []

    # Buscar respuestas en Gmail
    respuestas_gmail = await gmail_client.leer_respuestas(message_ids)

    # Mapeo message_id → resultado: cuando Gmail devuelve una respuesta con
    # in_reply_to=X, buscamos X en este dict para encontrar el contact_id
    # original al que pertenece la respuesta.
    resultado_por_mid = {r["message_id"]: r for r in resultados if r.get("message_id")}

    nuevas = []
    for resp in respuestas_gmail:
        # Evitar duplicados por message_id
        existentes = await replies_repository.buscar_por_message_id(resp["message_id"])
        if existentes:
            continue

        # Encontrar el resultado original al que responde
        resultado_orig = resultado_por_mid.get(resp.get("in_reply_to", ""), {})
        reply = await replies_repository.guardar_respuesta({
            "campaign_id": campaign_id,
            "contact_id": resultado_orig.get("contact_id"),
            "message_id": resp["message_id"],
            "in_reply_to": resp.get("in_reply_to"),
            "de": resp["de"],
            "asunto": resp.get("asunto", ""),
            "cuerpo": resp.get("cuerpo", ""),
        })
        nuevas.append(reply)

    log.info("Sincronizacion campana %s: %d nuevas respuestas", campaign_id, len(nuevas))
    return nuevas


async def listar_respuestas(campaign_id: str) -> list[dict]:
    """Lista todas las respuestas de una campana."""
    return await replies_repository.listar_por_campana(campaign_id)


async def responder(reply_id: str, cuerpo: str) -> dict:
    """
    Responde a una respuesta recibida.

    Envia un email con asunto "Re: {asunto_original}" al remitente
    original y marca la respuesta como respondida.

    Args:
        reply_id: UUID de la respuesta a contestar.
        cuerpo: cuerpo HTML de la respuesta.

    Returns:
        Dict con datos del email enviado.
    """
    reply = await replies_repository.obtener_por_id(reply_id)
    asunto_original = reply.get("asunto", "")
    # Agregar "Re:" solo si no lo tiene ya
    asunto = asunto_original if asunto_original.startswith("Re:") else f"Re: {asunto_original}"

    resultado = await gmail_client.enviar_email(
        destinatario=reply["de"],
        asunto=asunto,
        cuerpo=cuerpo,
    )

    await replies_repository.marcar_respondida(reply_id)
    await replies_repository.marcar_leida(reply_id)
    log.info("Respondido a %s — reply_id: %s", reply["de"], reply_id)
    return resultado


async def marcar_leida(reply_id: str) -> bool:
    """Marca una respuesta como leida."""
    ok = await replies_repository.marcar_leida(reply_id)
    if not ok:
        raise AppError("Respuesta no encontrada", "REPLY_NOT_FOUND", 404)
    return True
