"""
Funciones de envío via Gmail API — construcción de mensajes y envío bulk.
Stateless: todas las funciones reciben un dict `credenciales` como primer argumento.
Usa run_in_executor para no bloquear el event loop.
"""
from __future__ import annotations

import asyncio
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_SCOPES = ["https://mail.google.com/"]
_SEND_TIMEOUT = 30


def _construir_servicio(credenciales: dict):
    """Construye el servicio Gmail API a partir de un dict de credenciales."""
    source = credenciales.get("source", "user")
    try:
        if source == "user":
            creds = Credentials(
                token=credenciales["access_token"],
                refresh_token=credenciales.get("refresh_token"),
                token_uri=_TOKEN_URI,
                scopes=_SCOPES,
            )
        else:  # global_fallback
            creds = Credentials(
                token=None,
                refresh_token=credenciales["refresh_token"],
                client_id=credenciales["client_id"],
                client_secret=credenciales["client_secret"],
                token_uri=_TOKEN_URI,
                scopes=_SCOPES,
            )
            if not creds.valid:
                creds.refresh(Request())
        return build("gmail", "v1", credentials=creds)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error construyendo servicio Gmail: %s", exc)
        raise AppError("No se pudo autenticar con Gmail", "GMAIL_AUTH_ERROR", 502) from exc


_PIXEL = '<img src="{url}" width="1" height="1" style="display:none" alt="">'


def _inyectar_pixel(cuerpo: str, tracking_url: str) -> str:
    """Agrega pixel de tracking. 3 casos: texto plano, HTML con/sin </body>."""
    pixel = _PIXEL.format(url=tracking_url)
    if "<html" not in cuerpo.lower():
        cuerpo = "<html><body>" + cuerpo + "</body></html>"
    if "</body>" in cuerpo.lower():
        idx = cuerpo.lower().rfind("</body>")
        return cuerpo[:idx] + pixel + cuerpo[idx:]
    return cuerpo + pixel


def _construir_mensaje(credenciales: dict, destinatario: str, asunto: str, cuerpo: str) -> dict:
    """Construye un mensaje MIME codificado en base64 para Gmail API."""
    msg = MIMEMultipart("alternative")
    msg["To"] = destinatario
    msg["From"] = credenciales["email"]
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "html", "utf-8"))
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")}


def _enviar_sync(
    credenciales: dict, destinatario: str, asunto: str, cuerpo: str,
    tracking_url: Optional[str],
) -> dict:
    """Envio sincrono — ejecutado via run_in_executor."""
    if tracking_url:
        cuerpo = _inyectar_pixel(cuerpo, tracking_url)
    mensaje = _construir_mensaje(credenciales, destinatario, asunto, cuerpo)
    svc = _construir_servicio(credenciales)
    resultado = svc.users().messages().send(userId="me", body=mensaje).execute()
    gmail_id = resultado["id"]
    msg = svc.users().messages().get(
        userId="me", id=gmail_id, format="metadata", metadataHeaders=["Message-ID"]
    ).execute()
    hdrs = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    rfc822_id = hdrs.get("message-id", gmail_id)
    return {"message_id": rfc822_id, "destinatario": destinatario}


async def enviar_email(
    credenciales: dict,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    tracking_url: Optional[str] = None,
) -> dict:
    """Envia un email individual sin bloquear el event loop (timeout 30s)."""
    try:
        loop = asyncio.get_event_loop()
        resultado = await asyncio.wait_for(
            loop.run_in_executor(
                None, _enviar_sync, credenciales, destinatario, asunto, cuerpo, tracking_url
            ),
            timeout=_SEND_TIMEOUT,
        )
        log.info("Email enviado a %s — id: %s", destinatario, resultado["message_id"])
        return resultado
    except asyncio.TimeoutError:
        log.error("Timeout enviando email a %s (%ds)", destinatario, _SEND_TIMEOUT)
        raise AppError("Timeout al enviar email", "GMAIL_TIMEOUT", 504)
    except AppError:
        raise
    except Exception as exc:
        error_str = str(exc).lower()
        if "invalid_grant" in error_str or "token has been expired" in error_str or "token_expired" in error_str:
            log.error("Gmail OAuth token expirado o revocado: %s", exc)
            raise AppError(
                "Token de Gmail expirado. Reconectá tu cuenta en Configuración → Gmail.",
                "GMAIL_TOKEN_EXPIRED",
                401,
            ) from exc
        log.error("Error enviando email a %s: %s", destinatario, exc)
        raise AppError("Error al enviar email", "GMAIL_SEND_ERROR", 502) from exc


async def enviar_bulk(credenciales: dict, emails: list[dict]) -> list[dict]:
    """Envia multiples emails async; un fallo individual no detiene el lote."""
    resultados = []
    for email in emails:
        dest = email.get("destinatario", "desconocido")
        try:
            resultado = await enviar_email(
                credenciales,
                email["destinatario"],
                email["asunto"],
                email["cuerpo"],
                tracking_url=email.get("tracking_url"),
            )
            resultados.append({**resultado, "ok": True})
        except (AppError, Exception) as exc:
            log.warning("Fallo envio a %s: %s", dest, exc)
            error_msg = exc.message if isinstance(exc, AppError) else "Error al enviar email"
            resultados.append({"destinatario": dest, "error": error_msg, "ok": False})
    ok = sum(1 for r in resultados if r["ok"])
    log.info("Bulk completado: %d/%d enviados", ok, len(emails))
    return resultados
