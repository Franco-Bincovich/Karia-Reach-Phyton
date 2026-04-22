"""
Repositorio Apify — queries SQL para enriquecimiento de contactos.
"""
from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict

log = get_logger(__name__)

_EMAIL_FIELDS = frozenset({"email_empresarial", "email_personal"})


async def obtener_contacto(contacto_id: str) -> dict:
    """
    Obtiene un contacto por UUID.

    Args:
        contacto_id: UUID del contacto.

    Returns:
        Dict con los datos del contacto.

    Raises:
        AppError: CONTACT_NOT_FOUND (404) si no existe.
        AppError: DB_CONTACTS_GET (500) si falla la consulta.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE id = $1 LIMIT 1",
                uuid.UUID(contacto_id),
            )
    except Exception as exc:
        raise AppError("Error al obtener contacto", "DB_CONTACTS_GET", 500) from exc
    if not row:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
    return _record_to_dict(row)


async def verificar_email_duplicado(email_field: str, email_val: str, exclude_id: str) -> bool:
    """
    Verifica si un email ya existe en otro contacto.

    Args:
        email_field: columna a verificar — 'email_empresarial' o 'email_personal'.
        email_val: valor del email a comprobar.
        exclude_id: UUID del contacto a excluir (el que se esta enriqueciendo).

    Returns:
        True si el email ya existe en otro contacto.

    Raises:
        ValueError: si email_field no es un campo permitido.
        AppError: DB_CONTACTS_EMAIL_CHECK (500) si falla la consulta.
    """
    if email_field not in _EMAIL_FIELDS:
        raise ValueError(f"Campo de email no permitido: {email_field}")
    try:
        async with get_pool().acquire() as conn:
            existing = await conn.fetchrow(
                f"SELECT id FROM contacts WHERE {email_field} = $1 AND id != $2 LIMIT 1",
                email_val,
                uuid.UUID(exclude_id),
            )
        return existing is not None
    except Exception as exc:
        raise AppError("Error al verificar email", "DB_CONTACTS_EMAIL_CHECK", 500) from exc


async def actualizar_contacto(contacto_id: str, update_data: dict) -> dict:
    """
    Actualiza campos de un contacto en la DB.

    Args:
        contacto_id: UUID del contacto a actualizar.
        update_data: dict con los campos y valores. confianza debe ser int 0-100.

    Returns:
        Dict con los datos del contacto actualizado.

    Raises:
        AppError: DB_CONTACTS_UPDATE (500) si falla la operacion.
    """
    try:
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(update_data.items(), 1):
            if col == "origen":
                set_clauses.append(f"{col} = ${i}::contact_source")
            else:
                set_clauses.append(f"{col} = ${i}")
            vals.append(val)
        vals.append(uuid.UUID(contacto_id))
        query = (
            f"UPDATE contacts SET {', '.join(set_clauses)} "
            f"WHERE id = ${len(vals)} RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error actualizando contacto %s: %s", contacto_id, exc)
        raise AppError("Error al actualizar contacto", "DB_CONTACTS_UPDATE", 500) from exc
