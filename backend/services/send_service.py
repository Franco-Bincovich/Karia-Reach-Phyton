"""
Servicio de envio — logica de negocio para campanas de email:
creacion, envio via Gmail, registro de resultados y dashboard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Optional

from config.settings import get_settings
from integrations import gmail_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import campaigns_repository, contacts_repository, templates_repository
from utils.security import generar_token_tracking

settings = get_settings()
log = get_logger(__name__)


def _personalizar(texto: str, contacto: dict) -> str:
    """Reemplaza variables {{nombre}}, {{empresa}}, {{cargo}} con valores escapados."""
    return (
        texto.replace("{{nombre}}", escape(contacto.get("nombre", "")))
        .replace("{{empresa}}", escape(contacto.get("empresa", "")))
        .replace("{{cargo}}", escape(contacto.get("cargo", "")))
    )


def _preparar_emails(
    contactos: list[dict], template: dict, campaign_id: str
) -> tuple[list[dict], dict]:
    """
    Arma la lista de emails personalizados con pixel de tracking HMAC.

    Returns:
        Tupla (emails, contacto_por_email) para envio y registro posterior.
    """
    base = settings.BASE_URL.rstrip("/")
    emails = []
    contacto_por_email = {}
    for contacto in contactos:
        dest = contacto.get("email_empresarial") or contacto.get("email_personal") or ""
        if not dest:
            continue
        token = generar_token_tracking(campaign_id, contacto["id"])
        emails.append({
            "destinatario": dest,
            "asunto": _personalizar(template["asunto"], contacto),
            "cuerpo": _personalizar(template["cuerpo"], contacto),
            "tracking_url": f"{base}/track/open/{campaign_id}/{contacto['id']}?token={token}",
        })
        contacto_por_email[dest] = contacto
    return emails, contacto_por_email


async def _registrar_resultados(
    campaign_id: str, emails: list[dict], contacto_por_email: dict,
    resultados_gmail: list[dict],
) -> dict:
    """
    Registra cada resultado de envio en campaign_results y devuelve contadores.

    Returns:
        Dict con sent_count y failed_count.
    """
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
    nombre: str, template_id: str, contact_ids: list[str], scheduled_at: Optional[str] = None
) -> dict:
    """
    Crea y ejecuta una campana de email (orquestador).

    Flujo: valida template/contactos → crea campana → _preparar_emails
    → gmail bulk → _registrar_resultados → actualiza metricas.
    Sin rollback: si falla a mitad, status queda "sending".
    """
    templates = await templates_repository.listar()
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)

    todos = await contacts_repository.listar()
    contactos = [c for c in todos if c["id"] in contact_ids]
    if not contactos:
        raise AppError("No se encontraron contactos validos", "CONTACTS_NOT_FOUND", 404)

    campana = await campaigns_repository.crear({
        "nombre": nombre, "template_id": template_id, "contacts_count": len(contactos),
        "status": "sending", "sent_count": 0, "failed_count": 0, "scheduled_at": scheduled_at,
    })
    emails, contacto_por_email = _preparar_emails(contactos, template, campana["id"])
    resultados_gmail = await gmail_client.enviar_bulk(emails)
    metricas = await _registrar_resultados(campana["id"], emails, contacto_por_email, resultados_gmail)
    campana = await campaigns_repository.actualizar_metricas(
        campana["id"], {**metricas, "status": "completed"},
    )
    log.info("Campana '%s': %d enviados, %d fallidos", nombre, metricas["sent_count"], metricas["failed_count"])
    return campana


async def listar_campanas() -> list[dict]:
    """Devuelve todas las campanas."""
    return await campaigns_repository.listar()


async def obtener_dashboard() -> dict:
    """Genera un resumen general con queries COUNT (no trae todos los registros)."""
    return {
        "contactos": await contacts_repository.contar(),
        "templates": await templates_repository.contar(),
        "campanas": await campaigns_repository.contar(),
        "emails_enviados": await campaigns_repository.sumar_enviados(),
    }


async def obtener_estadisticas_campana(campaign_id: str) -> dict:
    """Estadisticas detalladas de una campana individual."""
    return await campaigns_repository.obtener_estadisticas_campana(campaign_id)


async def obtener_estadisticas_globales() -> dict:
    """Estadisticas agregadas de todas las campanas."""
    return await campaigns_repository.obtener_estadisticas_globales()
