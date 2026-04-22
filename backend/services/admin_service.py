"""
Servicio de administración — lógica de negocio para gestión de usuarios.

Solo accesible para superadmins.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
    return row


async def listar_usuarios() -> list[dict]:
    """Lista todos los usuarios con estadísticas de contactos y campañas."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id, u.nombre, u.email, u.rol, u.created_at,
                       COUNT(DISTINCT c.id)    AS total_contactos,
                       COUNT(DISTINCT camp.id) AS total_campanas,
                       COALESCE(SUM(camp.sent_count), 0) AS total_emails_enviados
                FROM usuarios_reach u
                LEFT JOIN contacts   c    ON c.usuario_id    = u.id
                LEFT JOIN campaigns  camp ON camp.usuario_id = u.id
                GROUP BY u.id, u.nombre, u.email, u.rol, u.created_at
                ORDER BY u.created_at DESC
                """
            )
        result = []
        for r in rows:
            d = _record_to_dict(r)
            d["total_contactos"] = int(d.get("total_contactos", 0))
            d["total_campanas"] = int(d.get("total_campanas", 0))
            d["total_emails_enviados"] = int(d.get("total_emails_enviados", 0))
            result.append(d)
        log.info("Admin: listados %d usuarios", len(result))
        return result
    except Exception as exc:
        log.error("Error listando usuarios: %s", exc)
        raise AppError("Error al listar usuarios", "DB_ADMIN_USERS_LIST", 500) from exc


async def obtener_usuario(id: str) -> dict:
    """Obtiene detalle de un usuario con sus últimos contactos y campañas."""
    try:
        uid = uuid.UUID(id)
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM usuarios_reach WHERE id = $1 LIMIT 1", uid
            )
            if not row:
                raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
            usuario = _record_to_dict(row)

            contactos_rows = await conn.fetch(
                "SELECT * FROM contacts WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT 20",
                uid,
            )
            campanas_rows = await conn.fetch(
                "SELECT * FROM campaigns WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT 10",
                uid,
            )
            total_contactos = await conn.fetchval(
                "SELECT COUNT(*) FROM contacts WHERE usuario_id = $1", uid
            )
            total_emails = await conn.fetchval(
                "SELECT COALESCE(SUM(sent_count), 0) FROM campaigns WHERE usuario_id = $1", uid
            )

            try:
                integ_rows = await conn.fetch(
                    "SELECT servicio FROM integraciones WHERE activo = true AND usuario_id = $1",
                    uid,
                )
                servicios = [r["servicio"] for r in integ_rows]
                if usuario.get("rol") == "superadmin":
                    from config.settings import get_settings
                    if get_settings().GMAIL_FROM_EMAIL:
                        servicios.append("gmail")
                usuario["integraciones"] = servicios
            except Exception:
                usuario["integraciones"] = []

        campanas_list = [_record_to_dict(r) for r in campanas_rows]
        usuario["contactos"] = [_record_to_dict(r) for r in contactos_rows]
        usuario["campanas"] = campanas_list
        usuario["total_contactos"] = int(total_contactos or 0)
        usuario["total_campanas"] = len(campanas_list)
        usuario["total_emails_enviados"] = int(total_emails or 0)
        return usuario
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo usuario %s: %s", id, exc)
        raise AppError("Error al obtener usuario", "DB_ADMIN_USER_GET", 500) from exc


async def editar_usuario(id: str, datos: dict) -> dict:
    """Edita nombre, email o rol de un usuario."""
    campos = {k: v for k, v in datos.items() if k in ("nombre", "email", "rol") and v}
    if not campos:
        raise AppError("No hay campos para actualizar", "NO_UPDATE_FIELDS", 400)
    if "rol" in campos and campos["rol"] not in ("user", "superadmin"):
        raise AppError("Rol inválido", "INVALID_ROLE", 400)
    try:
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(campos.items(), 1):
            set_clauses.append(f"{col} = ${i}")
            vals.append(val)
        vals.append(uuid.UUID(id))
        query = (
            f"UPDATE usuarios_reach SET {', '.join(set_clauses)} "
            f"WHERE id = ${len(vals)} RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        if not row:
            raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
        log.info("Admin: usuario %s editado — campos: %s", id, list(campos.keys()))
        return _record_to_dict(row)
    except AppError:
        raise
    except Exception as exc:
        log.error("Error editando usuario %s: %s", id, exc)
        raise AppError("Error al editar usuario", "DB_ADMIN_USER_EDIT", 500) from exc


async def eliminar_usuario(id: str, mi_id: str) -> bool:
    """Elimina un usuario y todos sus datos en cascada."""
    if id == mi_id:
        raise AppError("No podés eliminarte a vos mismo", "CANNOT_DELETE_SELF", 400)
    try:
        uid = uuid.UUID(id)
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM usuarios_reach WHERE id = $1 LIMIT 1", uid
            )
            if not row:
                raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
            async with conn.transaction():
                # email_replies y campaign_results no tienen usuario_id — se borran via campaigns
                await conn.execute(
                    "DELETE FROM email_replies WHERE campaign_id IN "
                    "(SELECT id FROM campaigns WHERE usuario_id = $1)",
                    uid,
                )
                await conn.execute(
                    "DELETE FROM campaign_results WHERE campaign_id IN "
                    "(SELECT id FROM campaigns WHERE usuario_id = $1)",
                    uid,
                )
                # bloques CASCADE → bloques_contactos; no hace falta borrarla explícitamente
                for tabla in ("campaigns", "bloques", "contacts", "integraciones"):
                    await conn.execute(
                        f"DELETE FROM {tabla} WHERE usuario_id = $1", uid
                    )
                await conn.execute(
                    "DELETE FROM usuarios_reach WHERE id = $1", uid
                )
        log.info("Admin: usuario %s eliminado con cascada", id)
        return True
    except AppError:
        raise
    except Exception as exc:
        log.error("Error eliminando usuario %s: %s", id, exc)
        raise AppError("Error al eliminar usuario", "DB_ADMIN_USER_DEL", 500) from exc
