"""
Servicio de respuestas — sincronizacion con Gmail, lectura y respuesta.
"""

from __future__ import annotations

from integrations import gmail_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import campaigns_repository, replies_repository
from services import gmail_oauth_service

log = get_logger(__name__)


async def sincronizar_respuestas_campana(
    campaign_id: str, usuario_id: str, rol: str
) -> list[dict]:
    """
    Sincroniza respuestas de Gmail para una campana.

    Obtiene message_ids de los resultados exitosos, busca respuestas
    en Gmail y guarda las nuevas evitando duplicados por message_id.
    """
    resultados = await campaigns_repository.listar_resultados(campaign_id)
    message_ids = [r["message_id"] for r in resultados if r.get("message_id")]
    if not message_ids:
        return []

    credenciales = await gmail_oauth_service.obtener_credenciales_validas(usuario_id, rol)
    respuestas_gmail = await gmail_client.leer_respuestas(credenciales, message_ids)

    resultado_por_mid = {r["message_id"]: r for r in resultados if r.get("message_id")}

    nuevas = []
    for resp in respuestas_gmail:
        existentes = await replies_repository.buscar_por_message_id(resp["message_id"])
        if existentes:
            continue

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


async def listar_respuestas(campaign_id: str, usuario_id: str = None) -> list[dict]:
    """Lista todas las respuestas de una campana.

    Args:
        campaign_id: UUID de la campana.
        usuario_id: UUID del usuario — si se provee, verifica que la campana le pertenezca.

    Raises:
        AppError: CAMPAIGN_NOT_FOUND (403) si la campana no pertenece al usuario.
    """
    if usuario_id:
        permitido = await replies_repository.verificar_campana_usuario(campaign_id, usuario_id)
        if not permitido:
            raise AppError("Acceso denegado a esta campana", "CAMPAIGN_NOT_FOUND", 403)
    return await replies_repository.listar_por_campana(campaign_id)


async def responder(reply_id: str, cuerpo: str, usuario_id: str, rol: str) -> dict:
    """
    Responde a una respuesta recibida.

    Envia un email con asunto "Re: {asunto_original}" al remitente
    original y marca la respuesta como respondida.
    """
    reply = await replies_repository.obtener_por_id(reply_id)
    asunto_original = reply.get("asunto", "")
    asunto = asunto_original if asunto_original.startswith("Re:") else f"Re: {asunto_original}"

    credenciales = await gmail_oauth_service.obtener_credenciales_validas(usuario_id, rol)
    resultado = await gmail_client.enviar_email(
        credenciales,
        destinatario=reply["de"],
        asunto=asunto,
        cuerpo=cuerpo,
    )

    await replies_repository.marcar_respondida(reply_id)
    await replies_repository.marcar_leida(reply_id)
    log.info("Respondido a %s — reply_id: %s", reply["de"], reply_id)
    return resultado


async def marcar_leida(reply_id: str, usuario_id: str = None) -> bool:
    """Marca una respuesta como leida.

    Args:
        reply_id: UUID de la respuesta.
        usuario_id: UUID del usuario — si se provee, verifica que el reply pertenezca a su campana.

    Raises:
        AppError: REPLY_NOT_FOUND (404) si el reply no existe.
        AppError: CAMPAIGN_NOT_FOUND (403) si el reply no pertenece al usuario.
    """
    if usuario_id:
        reply = await replies_repository.obtener_por_id(reply_id)
        permitido = await replies_repository.verificar_campana_usuario(reply["campaign_id"], usuario_id)
        if not permitido:
            raise AppError("Acceso denegado a esta respuesta", "CAMPAIGN_NOT_FOUND", 403)
    ok = await replies_repository.marcar_leida(reply_id)
    if not ok:
        raise AppError("Respuesta no encontrada", "REPLY_NOT_FOUND", 404)
    return True
