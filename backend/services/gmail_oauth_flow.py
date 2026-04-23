"""
Flujo OAuth de Gmail — generación de URL, validación de state e intercambio de code por tokens.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from google_auth_oauthlib.flow import Flow

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import gmail_repository
from repositories.integrations_repository import _cifrar

log = get_logger(__name__)
settings = get_settings()

_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
_STATE_TTL_MINUTES = 10
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _build_flow() -> Flow:
    """Construye un Flow de OAuth2 a partir de las credenciales del .env."""
    client_config = {
        "web": {
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.gmail_oauth_redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=_SCOPES,
        redirect_uri=settings.gmail_oauth_redirect_uri,
    )


def _make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Asegura que un datetime sea timezone-aware (UTC) si no lo es."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def generar_url_autorizacion(usuario_id: str) -> str:
    """Genera la URL de autorización de Google con un state JWT firmado (TTL 10 min)."""
    state = jwt.encode(
        {
            "sub": usuario_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return auth_url


def validar_state(state: str) -> str:
    """Verifica el JWT del state OAuth y retorna el usuario_id embebido."""
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        return str(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise AppError("State OAuth expirado", "OAUTH_STATE_EXPIRED", 400)
    except jwt.InvalidTokenError:
        raise AppError("State OAuth inválido", "OAUTH_STATE_INVALID", 400)


async def procesar_callback(code: str, usuario_id: str) -> dict:
    """Intercambia el authorization code por tokens y persiste las credenciales cifradas en DB."""
    flow = _build_flow()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: flow.fetch_token(code=code))
    creds = flow.credentials

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {creds.token}"},
        )
    resp.raise_for_status()
    email = resp.json().get("email", "")

    expira = _make_aware(creds.expiry)
    await gmail_repository.guardar_credenciales(
        usuario_id=usuario_id,
        email=email,
        refresh_token_cifrado=_cifrar(creds.refresh_token or ""),
        access_token_cifrado=_cifrar(creds.token) if creds.token else None,
        access_token_expira=expira,
        scopes=",".join(_SCOPES),
    )
    log.info("Gmail OAuth completado para usuario %s (%s)", usuario_id, email)
    return {"email": email, "conectado": True}
