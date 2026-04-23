"""
Gestión de credenciales Gmail — refresco de tokens y obtención de credenciales válidas.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import gmail_repository
from repositories.integrations_repository import _cifrar, _descifrar

log = get_logger(__name__)
settings = get_settings()


def _make_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Asegura que un datetime sea timezone-aware (UTC) si no lo es."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


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
