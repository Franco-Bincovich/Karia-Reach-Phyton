"""
Repositorio de integraciones Gmail por usuario — acceso a `integraciones_gmail`.

Almacena tokens OAuth cifrados. El cifrado/descifrado se realiza en la capa
de servicio (gmail_oauth_service); este repositorio opera con strings opacos.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "integraciones_gmail"


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


async def guardar_credenciales(
    usuario_id: str,
    email: str,
    refresh_token_cifrado: str,
    access_token_cifrado: Optional[str],
    access_token_expira: Optional[datetime],
    scopes: str,
) -> dict:
    """Inserta o actualiza las credenciales Gmail del usuario (UPSERT por usuario_id)."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integraciones_gmail
                    (usuario_id, email, refresh_token_cifrado, access_token_cifrado,
                     access_token_expira, scopes, conectado_at, activo, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, now(), true, now())
                ON CONFLICT (usuario_id) DO UPDATE SET
                    email                 = EXCLUDED.email,
                    refresh_token_cifrado = EXCLUDED.refresh_token_cifrado,
                    access_token_cifrado  = EXCLUDED.access_token_cifrado,
                    access_token_expira   = EXCLUDED.access_token_expira,
                    scopes                = EXCLUDED.scopes,
                    conectado_at          = now(),
                    activo                = true,
                    updated_at            = now()
                RETURNING *
                """,
                uuid.UUID(usuario_id),
                email,
                refresh_token_cifrado,
                access_token_cifrado,
                access_token_expira,
                scopes,
            )
        log.info("Credenciales Gmail guardadas para usuario %s (%s)", usuario_id, email)
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error guardando credenciales Gmail de %s: %s", usuario_id, exc)
        raise AppError("Error al guardar credenciales Gmail", "DB_GMAIL_SAVE", 500) from exc


async def obtener_por_usuario(usuario_id: str) -> Optional[dict]:
    """Retorna las credenciales activas del usuario o None si no existen."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {_TABLE} WHERE usuario_id = $1 AND activo = true LIMIT 1",
                uuid.UUID(usuario_id),
            )
        return _record_to_dict(row) if row else None
    except Exception as exc:
        log.error("Error obteniendo credenciales Gmail de %s: %s", usuario_id, exc)
        raise AppError("Error al obtener credenciales Gmail", "DB_GMAIL_GET", 500) from exc


async def actualizar_access_token(
    usuario_id: str,
    access_token_cifrado: str,
    expira: Optional[datetime],
) -> None:
    """Actualiza el access_token y su fecha de expiración tras un refresco."""
    try:
        async with get_pool().acquire() as conn:
            await conn.execute(
                f"""
                UPDATE {_TABLE}
                SET access_token_cifrado = $1,
                    access_token_expira  = $2,
                    updated_at           = now()
                WHERE usuario_id = $3
                """,
                access_token_cifrado,
                expira,
                uuid.UUID(usuario_id),
            )
    except Exception as exc:
        log.error("Error actualizando access_token Gmail de %s: %s", usuario_id, exc)
        raise AppError("Error al actualizar access token", "DB_GMAIL_UPDATE_TOKEN", 500) from exc


async def registrar_uso(usuario_id: str) -> None:
    """Actualiza ultimo_uso=now(). Fire-and-forget: falla silenciosamente."""
    try:
        async with get_pool().acquire() as conn:
            await conn.execute(
                f"UPDATE {_TABLE} SET ultimo_uso = now() WHERE usuario_id = $1",
                uuid.UUID(usuario_id),
            )
    except Exception as exc:
        log.warning("No se pudo registrar uso Gmail de %s: %s", usuario_id, exc)


async def desconectar(usuario_id: str) -> bool:
    """Desactiva la integración Gmail del usuario. Retorna True si había una activa."""
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE {_TABLE}
                SET activo = false, updated_at = now()
                WHERE usuario_id = $1 AND activo = true
                """,
                uuid.UUID(usuario_id),
            )
        desconectado = result.startswith("UPDATE ") and int(result.split()[1]) > 0
        if desconectado:
            log.info("Gmail desconectado para usuario %s", usuario_id)
        return desconectado
    except Exception as exc:
        log.error("Error desconectando Gmail de %s: %s", usuario_id, exc)
        raise AppError("Error al desconectar Gmail", "DB_GMAIL_DISCONNECT", 500) from exc
