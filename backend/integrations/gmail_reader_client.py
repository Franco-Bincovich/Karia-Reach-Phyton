"""
Funciones de lectura de respuestas via Gmail API.
Stateless: recibe un dict `credenciales` como primer argumento.
"""
from __future__ import annotations

import asyncio
import base64

from logger import get_logger
from .gmail_send_client import _construir_servicio

log = get_logger(__name__)


def _extraer_texto(payload: dict) -> str:
    """Extrae cuerpo texto plano de un payload MIME de Gmail (recursivo)."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        texto = _extraer_texto(part)
        if texto:
            return texto
    return ""


def _leer_respuestas_sync(credenciales: dict, message_ids: list[str]) -> list[dict]:
    """Lectura sincrona — busca replies via threads de Gmail."""
    svc = _construir_servicio(credenciales)
    from_email = credenciales["email"]
    respuestas = []
    for mid in message_ids:
        try:
            clean = mid.strip("<>")
            res = svc.users().messages().list(
                userId="me", q=f"rfc822msgid:{clean}", maxResults=1
            ).execute()
            if not res.get("messages"):
                continue
            thread_id = res["messages"][0]["threadId"]
            thread = svc.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            for msg in thread.get("messages", []):
                hdrs = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
                if from_email in hdrs.get("from", ""):
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


async def leer_respuestas(credenciales: dict, message_ids: list[str]) -> list[dict]:
    """Busca respuestas en Gmail sin bloquear el event loop."""
    loop = asyncio.get_running_loop()
    respuestas = await loop.run_in_executor(
        None, _leer_respuestas_sync, credenciales, message_ids
    )
    log.info("Encontradas %d respuestas para %d message_ids", len(respuestas), len(message_ids))
    return respuestas
