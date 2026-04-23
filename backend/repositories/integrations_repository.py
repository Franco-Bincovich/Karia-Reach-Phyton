"""
Repositorio de integraciones — acceso a tabla `integraciones`.

Almacena API keys de servicios externos (Apollo, etc.).
Las keys se cifran con Fernet (AES-128-CBC) antes de persistir para que
no queden en texto plano en la base de datos ni en backups.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import uuid
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from config.settings import get_settings
from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

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


async def guardar_api_key(servicio: str, api_key: str, usuario_id: str = None) -> dict:
    """
    Guarda o actualiza la API key cifrada de un servicio.

    Usa INSERT ... ON CONFLICT DO UPDATE para insertar o actualizar.
    """
    try:
        cifrada = _cifrar(api_key)
        uid = uuid.UUID(usuario_id) if usuario_id else None
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integraciones (servicio, api_key, activo, usuario_id)
                VALUES ($1, $2, true, $3)
                ON CONFLICT (servicio, usuario_id)
                DO UPDATE SET
                    api_key = EXCLUDED.api_key,
                    activo = EXCLUDED.activo,
                    updated_at = NOW()
                RETURNING *
                """,
                servicio,
                cifrada,
                uid,
            )
        log.info("API key guardada para %s (usuario=%s)", servicio, usuario_id)
        return record_to_dict(row)
    except Exception as exc:
        log.error("Error guardando API key de %s: %s", servicio, exc)
        raise AppError("Error al guardar API key", "DB_INTEGRATIONS_SAVE", 500) from exc


async def obtener_api_key(servicio: str, usuario_id: str = None) -> Optional[str]:
    """Obtiene y descifra la API key activa de un servicio."""
    try:
        uid = uuid.UUID(usuario_id) if usuario_id else None
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT api_key FROM integraciones "
                "WHERE servicio = $1 AND activo = true "
                "AND ($2::uuid IS NULL OR usuario_id = $2) "
                "LIMIT 1",
                servicio,
                uid,
            )
        if not row:
            return None
        return _descifrar(row["api_key"])
    except Exception as exc:
        log.error("Error obteniendo API key de %s: %s", servicio, exc)
        raise AppError("Error al obtener API key", "DB_INTEGRATIONS_GET", 500) from exc


async def eliminar_api_key(servicio: str, usuario_id: str = None) -> bool:
    """Desactiva la API key de un servicio."""
    try:
        uid = uuid.UUID(usuario_id) if usuario_id else None
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE integraciones SET activo = false, updated_at = NOW() "
                "WHERE servicio = $1 AND ($2::uuid IS NULL OR usuario_id = $2)",
                servicio,
                uid,
            )
        eliminado = result.startswith("UPDATE ") and int(result.split()[1]) > 0
        if eliminado:
            log.info("API key desactivada para %s (usuario=%s)", servicio, usuario_id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando API key de %s: %s", servicio, exc)
        raise AppError("Error al eliminar API key", "DB_INTEGRATIONS_DEL", 500) from exc
