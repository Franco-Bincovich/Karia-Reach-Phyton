"""
Cliente async de Gmail API. Envio, tracking pixel y lectura de respuestas.
Usa run_in_executor para no bloquear el event loop.
"""
from __future__ import annotations

import asyncio
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
settings = get_settings()

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_SCOPES = ["https://mail.google.com/"]


def _crear_servicio():
    """Crea el servicio Gmail API autenticado con OAuth2 desde settings."""
    if not all([settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN]):
        raise AppError("Faltan credenciales de Gmail OAuth", "GMAIL_CONFIG_ERROR", 500)
    try:
        creds = Credentials(
            token=None, refresh_token=settings.GMAIL_REFRESH_TOKEN,
            client_id=settings.GMAIL_CLIENT_ID, client_secret=settings.GMAIL_CLIENT_SECRET,
            token_uri=_TOKEN_URI, scopes=_SCOPES,
        )
        return build("gmail", "v1", credentials=creds)
    except Exception as exc:
        log.error("Error creando servicio Gmail: %s", exc)
        raise AppError("No se pudo autenticar con Gmail", "GMAIL_AUTH_ERROR", 502) from exc

_servicio = None  # Lazy singleton: se inicializa en el primer uso


def get_gmail_service():
    """Devuelve el servicio Gmail, creandolo en el primer uso (lazy singleton)."""
    global _servicio
    if _servicio is None:
        _servicio = _crear_servicio()
    return _servicio
_PIXEL = '<img src="{url}" width="1" height="1" style="display:none" alt="">'


def _inyectar_pixel(cuerpo: str, tracking_url: str) -> str:
    """Agrega pixel de tracking. 3 casos: texto plano, HTML con/sin </body>."""
    pixel = _PIXEL.format(url=tracking_url)
    if "<html" not in cuerpo.lower():  # Caso 1: texto plano → envolver en HTML
        cuerpo = "<html><body>" + cuerpo + "</body></html>"
    if "</body>" in cuerpo.lower():  # Caso 2: insertar antes de </body>
        idx = cuerpo.lower().rfind("</body>")
        return cuerpo[:idx] + pixel + cuerpo[idx:]
    return cuerpo + pixel  # Caso 3: sin </body> → agregar al final


def _construir_mensaje(destinatario: str, asunto: str, cuerpo: str) -> dict:
    """Construye un mensaje MIME codificado en base64 para Gmail API."""
    msg = MIMEMultipart("alternative")
    msg["To"] = destinatario
    msg["From"] = settings.GMAIL_FROM_EMAIL
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "html", "utf-8"))
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")}


def _enviar_sync(destinatario: str, asunto: str, cuerpo: str, tracking_url: Optional[str]) -> dict:
    """Envio sincrono — ejecutado via run_in_executor."""
    if tracking_url:
        cuerpo = _inyectar_pixel(cuerpo, tracking_url)
    mensaje = _construir_mensaje(destinatario, asunto, cuerpo)
    svc = get_gmail_service()
    resultado = svc.users().messages().send(userId="me", body=mensaje).execute()
    # Obtener el Message-ID RFC822 real (necesario para buscar respuestas)
    gmail_id = resultado["id"]
    msg = svc.users().messages().get(userId="me", id=gmail_id, format="metadata",
                                     metadataHeaders=["Message-ID"]).execute()
    hdrs = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    rfc822_id = hdrs.get("message-id", gmail_id)
    return {"message_id": rfc822_id, "destinatario": destinatario}

_SEND_TIMEOUT = 30  # segundos


async def enviar_email(
    destinatario: str, asunto: str, cuerpo: str, tracking_url: Optional[str] = None
) -> dict:
    """Envia un email individual sin bloquear el event loop (timeout 30s)."""
    try:
        loop = asyncio.get_event_loop()
        resultado = await asyncio.wait_for(
            loop.run_in_executor(None, _enviar_sync, destinatario, asunto, cuerpo, tracking_url),
            timeout=_SEND_TIMEOUT,
        )
        log.info("Email enviado a %s — id: %s", destinatario, resultado["message_id"])
        return resultado
    except asyncio.TimeoutError:
        log.error("Timeout enviando email a %s (%ds)", destinatario, _SEND_TIMEOUT)
        raise AppError(f"Timeout al enviar email a {destinatario}", "GMAIL_TIMEOUT", 504)
    except AppError:
        raise
    except Exception as exc:
        error_str = str(exc).lower()
        if "invalid_grant" in error_str or "token has been expired" in error_str or "token_expired" in error_str:
            log.error("Gmail OAuth token expirado o revocado: %s", exc)
            raise AppError(
                "Token de Gmail expirado. Regenerá el refresh token en Google Cloud Console y actualizá GMAIL_REFRESH_TOKEN en el .env.",
                "GMAIL_TOKEN_EXPIRED",
                401
            ) from exc
        log.error("Error enviando email a %s: %s", destinatario, exc)
        raise AppError(f"Error al enviar email a {destinatario}", "GMAIL_SEND_ERROR", 502) from exc

async def enviar_bulk(emails: list[dict]) -> list[dict]:
    """Envia multiples emails async; un fallo individual no detiene el lote."""
    resultados = []
    for email in emails:
        dest = email.get("destinatario", "desconocido")
        try:
            resultado = await enviar_email(
                email["destinatario"], email["asunto"], email["cuerpo"],
                tracking_url=email.get("tracking_url"),
            )
            resultados.append({**resultado, "ok": True})
        except (AppError, Exception) as exc:
            log.warning("Fallo envio a %s: %s", dest, exc)
            resultados.append({"destinatario": dest, "error": str(exc), "ok": False})
    ok = sum(1 for r in resultados if r["ok"])
    log.info("Bulk completado: %d/%d enviados", ok, len(emails))
    return resultados


def _extraer_texto(payload: dict) -> str:
    """Extrae cuerpo texto plano de un payload MIME de Gmail (recursivo)."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        texto = _extraer_texto(part)
        if texto:
            return texto
    return ""

def _leer_respuestas_sync(message_ids: list[str]) -> list[dict]:
    """Lectura sincrona — busca replies via threads de Gmail."""
    svc = get_gmail_service()
    respuestas = []
    for mid in message_ids:
        try:
            # 1. Buscar el mensaje original por su Message-ID RFC822
            clean = mid.strip("<>")
            res = svc.users().messages().list(
                userId="me", q=f"rfc822msgid:{clean}", maxResults=1
            ).execute()
            if not res.get("messages"):
                continue
            # 2. Obtener el threadId del mensaje original
            thread_id = res["messages"][0]["threadId"]
            # 3. Traer todos los mensajes del thread
            thread = svc.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            # 4. Filtrar: solo mensajes que NO son nuestros (esas son las respuestas)
            for msg in thread.get("messages", []):
                hdrs = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                if settings.GMAIL_FROM_EMAIL in hdrs.get("from", ""):
                    continue
                respuestas.append({
                    "de": hdrs.get("from", ""),
                    "asunto": hdrs.get("subject", ""),
                    "cuerpo": _extraer_texto(msg["payload"]),
                    "fecha": hdrs.get("date", ""),
                    "message_id": hdrs.get("message-id", msg["id"]),
                    "in_reply_to": mid,
                })
        except Exception as exc:
            log.warning("Error buscando respuestas para %s: %s", mid, exc)
    return respuestas

async def leer_respuestas(message_ids: list[str]) -> list[dict]:
    """Busca respuestas en Gmail sin bloquear el event loop."""
    loop = asyncio.get_event_loop()
    respuestas = await loop.run_in_executor(None, _leer_respuestas_sync, message_ids)
    log.info("Encontradas %d respuestas para %d message_ids", len(respuestas), len(message_ids))
    return respuestas
