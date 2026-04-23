"""
Servicio de envio — orquestacion de campanas de email:
creacion, envio via Gmail, registro de resultados y estadisticas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from integrations import gmail_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import campaigns_repository, contacts_repository, templates_repository
from services import email_builder_service, gmail_oauth_service
from utils.helpers import require_uid

log = get_logger(__name__)


async def _registrar_resultados(
    campaign_id: str, emails: list[dict], contacto_por_email: dict,
    resultados_gmail: list[dict],
) -> dict:
    """Registra en DB los resultados de envio y devuelve sent_count, failed_count, sent_at."""
    ahora = datetime.now(timezone.utc).isoformat()
    sent, failed = 0, 0
    for resultado in resultados_gmail:
        contacto = contacto_por_email.get(resultado["destinatario"], {})
        exitoso = resultado["ok"]
        email_enviado = next((e for e in emails if e["destinatario"] == resultado["destinatario"]), {})
        await campaigns_repository.crear_resultado({
            "campaign_id": campaign_id,
            "contact_id": contacto.get("id"),
            "email_destinatario": resultado["destinatario"],
            "asunto": email_enviado.get("asunto", ""),
            "message_id": resultado.get("message_id"),
            "exitoso": exitoso,
            "error": resultado.get("error"),
            "enviado_at": ahora,
        })
        sent += 1 if exitoso else 0
        failed += 0 if exitoso else 1
    return {"sent_count": sent, "failed_count": failed, "sent_at": ahora}


async def enviar_campana(
    nombre: str, template_id: str, contact_ids: list[str],
    scheduled_at: Optional[str] = None, usuario_id: str = None, rol: str = "user",
) -> dict:
    """Crea y ejecuta una campaña de email via Gmail OAuth.

    Args:
        nombre: nombre descriptivo de la campaña.
        template_id: UUID del template a usar.
        contact_ids: lista de UUIDs de contactos destinatarios.
        scheduled_at: ISO datetime de envío programado (no usado en envío inmediato).
        usuario_id: UUID del usuario propietario.
        rol: rol del usuario para resolver credenciales Gmail.

    Returns:
        Dict con todos los campos de la campaña creada, incluyendo métricas de envío.

    Raises:
        AppError: TEMPLATE_NOT_FOUND (404) si el template no existe o no pertenece al usuario.
        AppError: CONTACTS_NOT_FOUND (404) si ningún contact_id existe.
        AppError: CONTACTS_FORBIDDEN (403) si algún contact_id no pertenece al usuario.
    """
    log.info("AUDIT enviar_campana usuario=%s contactos=%d template=%s", usuario_id, len(contact_ids), template_id)
    require_uid(usuario_id)
    templates = await templates_repository.listar(usuario_id)
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)

    contactos = await contacts_repository.listar_por_ids(contact_ids, usuario_id)
    if not contactos:
        raise AppError("No se encontraron contactos validos", "CONTACTS_NOT_FOUND", 404)
    if len(contactos) != len(contact_ids):
        raise AppError("No tenés acceso a algunos contactos seleccionados", "CONTACTS_FORBIDDEN", 403)

    credenciales = await gmail_oauth_service.obtener_credenciales_validas(usuario_id, rol)

    camp_data = {
        "nombre": nombre, "template_id": template_id, "contacts_count": len(contactos),
        "status": "sending", "sent_count": 0, "failed_count": 0, "scheduled_at": scheduled_at,
    }
    if usuario_id:
        camp_data["usuario_id"] = usuario_id
    campana = await campaigns_repository.crear(camp_data)
    emails, contacto_por_email = email_builder_service.preparar_emails(contactos, template, campana["id"])
    resultados_gmail = await gmail_client.enviar_bulk(credenciales, emails)
    metricas = await _registrar_resultados(campana["id"], emails, contacto_por_email, resultados_gmail)
    campana = await campaigns_repository.actualizar_metricas(
        campana["id"], {**metricas, "status": "completed"},
    )
    log.info("Campana '%s': %d enviados, %d fallidos", nombre, metricas["sent_count"], metricas["failed_count"])
    return campana


async def listar_campanas(usuario_id: str = None) -> list[dict]:
    """Devuelve todas las campañas del usuario ordenadas por created_at DESC."""
    require_uid(usuario_id)
    return await campaigns_repository.listar(usuario_id)


async def obtener_dashboard(usuario_id: str = None) -> dict:
    """Devuelve totales del usuario: contactos, templates, campanas, emails_enviados."""
    require_uid(usuario_id)
    return {"contactos": await contacts_repository.contar(usuario_id),
            "templates": await templates_repository.contar(usuario_id),
            "campanas": await campaigns_repository.contar(usuario_id),
            "emails_enviados": await campaigns_repository.sumar_enviados(usuario_id)}


async def obtener_estadisticas_campana(campaign_id: str, usuario_id: str = None) -> dict:
    """Estadísticas detalladas de una campaña: totales, tasas y resultados individuales."""
    require_uid(usuario_id)
    return await campaigns_repository.obtener_estadisticas_campana(campaign_id, usuario_id)


async def obtener_estadisticas_globales(usuario_id: str = None) -> dict:
    """Estadísticas agregadas de todas las campañas del sistema."""
    require_uid(usuario_id)
    return await campaigns_repository.obtener_estadisticas_globales(usuario_id)
