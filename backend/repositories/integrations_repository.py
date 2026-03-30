"""
Repositorio de integraciones — acceso a tabla `integraciones`.

Almacena API keys de servicios externos (Apollo, etc.).
Las keys se cifran con Fernet (AES-128-CBC) antes de persistir para que
no queden en texto plano en la base de datos ni en backups.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from config.settings import get_settings
from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
settings = get_settings()

_TABLE = "integraciones"


def _get_fernet() -> Optional[Fernet]:
    """Devuelve instancia Fernet si ENCRYPTION_KEY esta configurada."""
    if not settings.ENCRYPTION_KEY:
        return None
    return Fernet(settings.ENCRYPTION_KEY.encode())


def _cifrar(valor: str) -> str:
    """Cifra un valor con Fernet. Si no hay key, devuelve sin cifrar."""
    f = _get_fernet()
    return f.encrypt(valor.encode()).decode() if f else valor


def _descifrar(valor: str) -> str:
    """Descifra un valor con Fernet. Si falla, devuelve el valor original."""
    f = _get_fernet()
    if not f:
        return valor
    try:
        return f.decrypt(valor.encode()).decode()
    except InvalidToken:
        # Fallo de descifrado: ocurre si (a) el valor se guardo antes de activar
        # cifrado (texto plano), o (b) ENCRYPTION_KEY cambio. En caso (b) las keys
        # guardadas con la key anterior necesitan re-guardarse con la nueva.
        log.warning("No se pudo descifrar valor, puede estar en texto plano")
        return valor


async def guardar_api_key(servicio: str, api_key: str) -> dict:
    """
    Guarda o actualiza la API key cifrada de un servicio.

    Usa upsert por servicio (UNIQUE constraint) para insertar o actualizar.
    """
    try:
        cifrada = _cifrar(api_key)
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).upsert(
                {"servicio": servicio, "api_key": cifrada, "activo": True},
                on_conflict="servicio",
            ).execute()
        ))
        log.info("API key guardada para %s", servicio)
        return resp.data[0]
    except Exception as exc:
        log.error("Error guardando API key de %s: %s", servicio, exc)
        raise AppError("Error al guardar API key", "DB_INTEGRATIONS_SAVE", 500) from exc


async def obtener_api_key(servicio: str) -> Optional[str]:
    """Obtiene y descifra la API key activa de un servicio."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("api_key")
            .eq("servicio", servicio).eq("activo", True)
            .limit(1).execute()
        ))
        if not resp.data:
            return None
        return _descifrar(resp.data[0]["api_key"])
    except Exception as exc:
        log.error("Error obteniendo API key de %s: %s", servicio, exc)
        raise AppError("Error al obtener API key", "DB_INTEGRATIONS_GET", 500) from exc


async def eliminar_api_key(servicio: str) -> bool:
    """Desactiva la API key de un servicio."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).update({"activo": False})
            .eq("servicio", servicio).execute()
        ))
        eliminado = len(resp.data) > 0
        if eliminado:
            log.info("API key desactivada para %s", servicio)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando API key de %s: %s", servicio, exc)
        raise AppError("Error al eliminar API key", "DB_INTEGRATIONS_DEL", 500) from exc
