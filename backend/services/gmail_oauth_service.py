"""
Servicio OAuth de Gmail por usuario.

Gestiona el flujo Authorization Code: generación de URL, validación de state,
intercambio de code por tokens, refresco automático y fallback a credenciales
globales para superadmins.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import gmail_repository
from repositories.integrations_repository import _cifrar, _descifrar

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


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def generar_url_autorizacion(usuario_id: str) -> str:
    """
    Genera la URL de autorización de Google con un state JWT firmado.

    El state expira en _STATE_TTL_MINUTES minutos para mitigar CSRF.
    """
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
    """
    Verifica el JWT del state OAuth y retorna el usuario_id embebido.

    Raise AppError si el token es inválido o expiró.
    """
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        return str(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise AppError("State OAuth expirado", "OAUTH_STATE_EXPIRED", 400)
    except jwt.InvalidTokenError:
        raise AppError("State OAuth inválido", "OAUTH_STATE_INVALID", 400)


async def procesar_callback(code: str, usuario_id: str) -> dict:
    """
    Intercambia el authorization code por tokens, obtiene el email del usuario
    y persiste las credenciales cifradas en DB.

    Retorna {"email": str, "conectado": True}.
    """
    flow = _build_flow()

    # fetch_token es síncrono — ejecutar en executor para no bloquear el event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: flow.fetch_token(code=code))
    creds = flow.credentials

    # Obtener email desde userinfo de Google
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


async def obtener_credenciales_validas(usuario_id: str, rol: str) -> dict:
    """
    Retorna credenciales Gmail válidas para el usuario.

    Flujo:
    1. Si existe integración activa con access_token no expirado → retorna directamente.
    2. Si el access_token expiró → refresca con Google y actualiza en DB.
    3. Si no hay integración y el usuario es superadmin con fallback habilitado
       → retorna credenciales globales del .env (source="global_fallback").
    4. En cualquier otro caso → AppError GMAIL_NOT_CONFIGURED (409).
    """
    row = await gmail_repository.obtener_por_usuario(usuario_id)

    if row:
        now = datetime.now(timezone.utc)
        expira = _make_aware(
            datetime.fromisoformat(row["access_token_expira"])
            if isinstance(row.get("access_token_expira"), str)
            else row.get("access_token_expira")
        )
        access_cifrado: Optional[str] = row.get("access_token_cifrado")

        if expira and expira > now and access_cifrado:
            await gmail_repository.registrar_uso(usuario_id)
            return {
                "access_token": _descifrar(access_cifrado),
                "refresh_token": _descifrar(row["refresh_token_cifrado"]),
                "email": row["email"],
                "source": "user",
            }

        # Access token expirado — refrescar con Google
        creds = Credentials(
            token=_descifrar(access_cifrado) if access_cifrado else None,
            refresh_token=_descifrar(row["refresh_token_cifrado"]),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            scopes=row["scopes"].split(","),
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: creds.refresh(Request()))

        nuevo_expira = _make_aware(creds.expiry)
        await gmail_repository.actualizar_access_token(
            usuario_id=usuario_id,
            access_token_cifrado=_cifrar(creds.token),
            expira=nuevo_expira,
        )
        await gmail_repository.registrar_uso(usuario_id)
        log.info("Access token Gmail refrescado para usuario %s", usuario_id)
        return {
            "access_token": creds.token,
            "refresh_token": _descifrar(row["refresh_token_cifrado"]),
            "email": row["email"],
            "source": "user",
        }

    # Sin integración para este usuario
    if rol == "superadmin" and settings.gmail_superadmin_fallback:
        log.info("Gmail fallback global usado para superadmin %s", usuario_id)
        return {
            "access_token": None,
            "refresh_token": settings.GMAIL_REFRESH_TOKEN,
            "email": settings.GMAIL_FROM_EMAIL,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "source": "global_fallback",
        }

    raise AppError("Gmail no configurado para este usuario", "GMAIL_NOT_CONFIGURED", 409)
