"""
Admin CRUD repository — queries SQL para crear, editar y eliminar usuarios.
"""
from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)


async def buscar_por_email(email: str) -> bool:
    """Verifica si un email ya esta registrado en usuarios_reach.

    Args:
        email: direccion de email a verificar.

    Returns:
        True si el email ya existe.
    """
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM usuarios_reach WHERE email = $1 LIMIT 1", email
        )
    return row is not None


async def insertar_usuario(email: str, password_hash: str, nombre: str, rol: str) -> dict:
    """Inserta un usuario nuevo. Asume que el email fue validado como unico.

    Args:
        email: email del usuario.
        password_hash: hash bcrypt de la contrasena.
        nombre: nombre visible.
        rol: 'user' o 'superadmin'.

    Returns:
        Dict con id, email, nombre, rol, activo, created_at, updated_at.

    Raises:
        AppError: DB_ADMIN_USER_CREATE (500) si falla la insercion.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO usuarios_reach (email, password_hash, nombre, rol, activo)
                VALUES ($1, $2, $3, $4, true)
                RETURNING id, email, nombre, rol, activo, created_at, updated_at
                """,
                email, password_hash, nombre, rol,
            )
        return record_to_dict(row)
    except Exception as exc:
        log.error("Error insertando usuario: %s", exc)
        raise AppError("Error al crear usuario", "DB_ADMIN_USER_CREATE", 500) from exc


async def editar_usuario(usuario_id: str, campos: dict) -> dict | None:
    """Actualiza campos de un usuario via UPDATE dinamico.

    Args:
        usuario_id: UUID del usuario.
        campos: dict con los campos a actualizar (ya validados por el service).

    Returns:
        Dict con el usuario actualizado, o None si no existe.

    Raises:
        AppError: DB_ADMIN_USER_EDIT (500) si falla la operacion.
    """
    try:
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(campos.items(), 1):
            set_clauses.append(f"{col} = ${i}")
            vals.append(val)
        vals.append(uuid.UUID(usuario_id))
        query = (
            f"UPDATE usuarios_reach SET {', '.join(set_clauses)} "
            f"WHERE id = ${len(vals)} RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        return record_to_dict(row) if row else None
    except Exception as exc:
        log.error("Error editando usuario %s: %s", usuario_id, exc)
        raise AppError("Error al editar usuario", "DB_ADMIN_USER_EDIT", 500) from exc


async def eliminar_usuario_cascade(usuario_id: str) -> bool:
    """Verifica existencia y borra usuario con toda su data en una transaccion.

    Args:
        usuario_id: UUID del usuario a eliminar.

    Returns:
        True si se elimino, False si el usuario no existia.

    Raises:
        AppError: DB_ADMIN_USER_DEL (500) si falla la transaccion.
    """
    try:
        uid = uuid.UUID(usuario_id)
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM usuarios_reach WHERE id = $1 LIMIT 1", uid
            )
            if not row:
                return False
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM email_replies WHERE campaign_id IN "
                    "(SELECT id FROM campaigns WHERE usuario_id = $1)", uid,
                )
                await conn.execute(
                    "DELETE FROM campaign_results WHERE campaign_id IN "
                    "(SELECT id FROM campaigns WHERE usuario_id = $1)", uid,
                )
                for tabla in ("campaigns", "bloques", "contacts", "integraciones"):
                    await conn.execute(f"DELETE FROM {tabla} WHERE usuario_id = $1", uid)
                await conn.execute("DELETE FROM usuarios_reach WHERE id = $1", uid)
        return True
    except Exception as exc:
        log.error("Error eliminando usuario %s: %s", usuario_id, exc)
        raise AppError("Error al eliminar usuario", "DB_ADMIN_USER_DEL", 500) from exc
