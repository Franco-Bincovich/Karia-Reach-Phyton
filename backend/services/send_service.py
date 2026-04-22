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
from services import gmail_oauth_service
from utils.security import generar_token_tracking

settings = get_settings()
log = get_logger(__name__)


def _require_uid(usuario_id: str | None) -> str:
    """Valida que usuario_id esté presente."""
    if not usuario_id:
        raise AppError("Token inválido o expirado", "AUTH_REQUIRED", 401)
    return usuario_id


def _validar_asunto(asunto: str) -> None:
    if "\n" in asunto or "\r" in asunto:
        raise AppError("El asunto contiene caracteres no permitidos", "EMAIL_HEADER_INJECTION", 400)

def _personalizar(texto: str, contacto: dict) -> str:
    return (
        texto.replace("{{nombre}}", escape(contacto.get("nombre", "")))
        .replace("{{empresa}}", escape(contacto.get("empresa", "")))
        .replace("{{cargo}}", escape(contacto.get("cargo", "")))
    )


def _preparar_emails(
    contactos: list[dict], template: dict, campaign_id: str
) -> tuple[list[dict], dict]:
    """Arma emails personalizados con pixel de tracking HMAC."""
    base = settings.BASE_URL.rstrip("/")
    emails = []
    contacto_por_email = {}
    for contacto in contactos:
        dest = contacto.get("email_empresarial") or contacto.get("email_personal") or ""
        if not dest:
            continue
        token = generar_token_tracking(campaign_id, contacto["id"])
        asunto = _personalizar(template["asunto"], contacto)
        _validar_asunto(asunto)
        emails.append({
            "destinatario": dest,
            "asunto": asunto,
            "cuerpo": _personalizar(template["cuerpo"], contacto),
            "tracking_url": f"{base}/track/open/{campaign_id}/{contacto['id']}?token={token}",
        })
        contacto_por_email[dest] = contacto
    return emails, contacto_por_email


async def _registrar_resultados(
    campaign_id: str, emails: list[dict], contacto_por_email: dict,
    resultados_gmail: list[dict],
) -> dict:
    """Registra resultados de envio y devuelve contadores."""
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
        scheduled_at: ISO datetime de envío programado (opcional, no usado en envío inmediato).
        usuario_id: UUID del usuario propietario.
        rol: rol del usuario ('user' o 'superadmin') para resolver credenciales Gmail.

    Returns:
        Dict con todos los campos de la campaña creada, incluyendo sent_count,
        failed_count, status='completed' y sent_at.

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
        AppError: TEMPLATE_NOT_FOUND (404) si template_id no existe o no pertenece al usuario.
        AppError: CONTACTS_NOT_FOUND (404) si ningún contact_id existe.
        AppError: CONTACTS_FORBIDDEN (403) si algún contact_id no pertenece al usuario.
        AppError: GMAIL_NOT_CONFIGURED (400) si no hay credenciales OAuth válidas.
    """
    log.info("AUDIT enviar_campana usuario=%s contactos=%d template=%s", usuario_id, len(contact_ids), template_id)
    _require_uid(usuario_id)
    templates = await templates_repository.listar(usuario_id)
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)

    contactos = await contacts_repository.listar_por_ids(contact_ids, usuario_id)
    if not contactos:
        raise AppError("No se encontraron contactos validos", "CONTACTS_NOT_FOUND", 404)
    # BUG-004: verificar que todos los contact_ids solicitados pertenecen al usuario
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
    emails, contacto_por_email = _preparar_emails(contactos, template, campana["id"])
    resultados_gmail = await gmail_client.enviar_bulk(credenciales, emails)
    metricas = await _registrar_resultados(campana["id"], emails, contacto_por_email, resultados_gmail)
    campana = await campaigns_repository.actualizar_metricas(
        campana["id"], {**metricas, "status": "completed"},
    )
    log.info("Campana '%s': %d enviados, %d fallidos", nombre, metricas["sent_count"], metricas["failed_count"])
    return campana


async def listar_campanas(usuario_id: str = None) -> list[dict]:
    """Devuelve todas las campañas del usuario.

    Args:
        usuario_id: UUID del usuario propietario.

    Returns:
        Lista de dicts con todos los campos de cada campaña, ordenadas por created_at DESC.

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
    """
    _require_uid(usuario_id)
    return await campaigns_repository.listar(usuario_id)


async def obtener_dashboard(usuario_id: str = None) -> dict:
    """Devuelve resumen de métricas del usuario para el dashboard.

    Args:
        usuario_id: UUID del usuario propietario.

    Returns:
        Dict con contactos, templates, campanas y emails_enviados (todos int).

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
    """
    _require_uid(usuario_id)
    return {"contactos": await contacts_repository.contar(usuario_id),
            "templates": await templates_repository.contar(usuario_id),
            "campanas": await campaigns_repository.contar(usuario_id),
            "emails_enviados": await campaigns_repository.sumar_enviados(usuario_id)}

async def obtener_estadisticas_campana(campaign_id: str, usuario_id: str = None) -> dict:
    """Devuelve estadísticas detalladas de una campaña específica.

    Args:
        campaign_id: UUID de la campaña.
        usuario_id: UUID del usuario propietario (solo para validar auth).

    Returns:
        Dict con campana, total_enviados, total_fallidos, total_abiertos,
        total_sin_abrir, total_respondidos, tasa_apertura, tasa_fallo y resultados.

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
        AppError: CAMPAIGN_NOT_FOUND (404) si campaign_id no existe.
    """
    _require_uid(usuario_id)
    return await campaigns_repository.obtener_estadisticas_campana(campaign_id)

async def obtener_estadisticas_globales(usuario_id: str = None) -> dict:
    """Devuelve estadísticas agregadas de todas las campañas del sistema.

    Args:
        usuario_id: UUID del usuario (solo para validar auth).

    Returns:
        Dict con total_campanas, total_emails_enviados, total_emails_fallidos,
        total_aperturas, total_respondidos y tasa_apertura_global.

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
    """
    _require_uid(usuario_id)
    return await campaigns_repository.obtener_estadisticas_globales()
