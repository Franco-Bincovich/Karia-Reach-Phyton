"""
Servicio de construcción de emails — personalización, validación y armado del payload.
"""
from __future__ import annotations

from html import escape

from config.settings import get_settings
from middleware.error_handler import AppError
from utils.security import generar_token_tracking

settings = get_settings()


def _validar_asunto(asunto: str) -> None:
    """Valida que el asunto no contenga caracteres de inyección de headers HTTP."""
    if "\n" in asunto or "\r" in asunto:
        raise AppError("El asunto contiene caracteres no permitidos", "EMAIL_HEADER_INJECTION", 400)


def _personalizar(texto: str, contacto: dict) -> str:
    """Sustituye {{nombre}}, {{empresa}}, {{cargo}} escapando HTML.

    Args:
        texto: template con variables a reemplazar.
        contacto: dict con campos nombre, empresa, cargo.

    Returns:
        Texto con variables reemplazadas por valores del contacto.
    """
    return (
        texto.replace("{{nombre}}", escape(contacto.get("nombre", "")))
        .replace("{{empresa}}", escape(contacto.get("empresa", "")))
        .replace("{{cargo}}", escape(contacto.get("cargo", "")))
    )


def preparar_emails(
    contactos: list[dict], template: dict, campaign_id: str
) -> tuple[list[dict], dict]:
    """Construye emails personalizados con pixel de tracking para cada contacto.

    Args:
        contactos: lista de contactos con email_empresarial/email_personal.
        template: dict con campos asunto y cuerpo.
        campaign_id: UUID de la campaña para generar el token HMAC de tracking.

    Returns:
        Tupla (emails, contacto_por_email):
          emails: lista de payloads listos para enviar (destinatario, asunto, cuerpo, tracking_url).
          contacto_por_email: dict {email -> contacto} para lookup posterior de contact_id.
    """
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
