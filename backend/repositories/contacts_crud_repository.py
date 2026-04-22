"""
Repositorio CRUD de contactos — inserción, lectura y eliminación en `contacts`.
"""
from __future__ import annotations

import uuid

import asyncpg

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict
from ._contacts_base import (
    _normalizar_contacto, _confianza_to_db, _build_insert_parts,
)

log = get_logger(__name__)


async def listar_emails(usuario_id: str = None) -> set[str]:
    """Devuelve un set con todos los emails existentes (empresarial + personal)."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                rows = await conn.fetch(
                    "SELECT email_empresarial, email_personal FROM contacts WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
                )
            else:
                rows = await conn.fetch("SELECT email_empresarial, email_personal FROM contacts")
        emails: set[str] = set()
        for row in rows:
            if row["email_empresarial"]:
                emails.add(row["email_empresarial"].lower())
            if row["email_personal"]:
                emails.add(row["email_personal"].lower())
        return emails
    except Exception as exc:
        log.error("Error listando emails: %s", exc)
        return set()


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los contactos ordenados por fecha de creacion desc."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                rows = await conn.fetch(
                    "SELECT * FROM contacts WHERE usuario_id = $1 ORDER BY created_at DESC",
                    uuid.UUID(usuario_id),
                )
            else:
                rows = await conn.fetch("SELECT * FROM contacts ORDER BY created_at DESC")
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando contactos: %s", exc)
        raise AppError("Error al listar contactos", "DB_CONTACTS_LIST", 500) from exc


async def contar(usuario_id: str = None) -> int:
    """Devuelve el total de contactos (query liviana, solo cuenta)."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM contacts WHERE usuario_id = $1", uuid.UUID(usuario_id),
                )
            else:
                result = await conn.fetchval("SELECT COUNT(*) FROM contacts")
        return int(result or 0)
    except Exception as exc:
        log.error("Error contando contactos: %s", exc)
        raise AppError("Error al contar contactos", "DB_CONTACTS_COUNT", 500) from exc


async def listar_por_ids(ids: list[str], usuario_id: str) -> list[dict]:
    """Devuelve contactos por lista de IDs, filtrados por usuario_id."""
    if not ids:
        return []
    try:
        uuid_ids = [uuid.UUID(i) for i in ids]
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM contacts WHERE id = ANY($1) AND usuario_id = $2",
                uuid_ids, uuid.UUID(usuario_id),
            )
        return [_record_to_dict(r) for r in rows]
    except Exception as exc:
        log.error("Error listando contactos por IDs: %s", exc)
        raise AppError("Error al listar contactos", "DB_CONTACTS_BY_IDS", 500) from exc


async def crear(contacto: dict) -> dict:
    """Inserta un contacto nuevo."""
    try:
        _normalizar_contacto(contacto)
        if contacto.get("confianza") is not None:
            contacto["confianza"] = _confianza_to_db(contacto["confianza"])
        cols, placeholders, vals = _build_insert_parts(contacto)
        query = f"INSERT INTO contacts ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING *"
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Contacto creado: %s", contacto.get("email_empresarial") or contacto.get("email_personal"))
        return _record_to_dict(row)
    except Exception as exc:
        log.error("Error creando contacto: %s", exc)
        raise AppError("Error al crear contacto", "DB_CONTACTS_CREATE", 500) from exc


async def crear_bulk(contactos: list[dict]) -> list[dict]:
    """Inserta multiples contactos ignorando duplicados por email."""
    existentes = await listar_emails()
    nuevos = [
        c for c in contactos
        if not ((c.get("email_empresarial") or "").lower() in existentes
                or (c.get("email_personal") or "").lower() in existentes)
    ]
    if not nuevos:
        log.info("crear_bulk: todos los contactos ya existen, nada que insertar")
        return []
    for c in nuevos:
        _normalizar_contacto(c)
        if c.get("confianza") is not None:
            c["confianza"] = _confianza_to_db(c["confianza"])
    log.info("Emails existentes en DB: %d encontrados", len(existentes))
    log.info("Contactos a insertar: %d", len(nuevos))
    insertados = []
    async with get_pool().acquire() as conn:
        for c in nuevos:
            try:
                cols, placeholders, vals = _build_insert_parts(c)
                query = f"INSERT INTO contacts ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING *"
                row = await conn.fetchrow(query, *vals)
                insertados.append(_record_to_dict(row))
            except asyncpg.UniqueViolationError:
                log.info("Duplicado ignorado: %s", c.get("email_empresarial"))
            except Exception as exc:
                log.error("Error insertando contacto en bulk: %s", exc)
    log.info("Bulk insert: %d/%d contactos creados", len(insertados), len(contactos))
    return insertados


async def eliminar(id: str, usuario_id: str = None) -> bool:
    """Elimina un contacto por id, restringido al usuario si se proporciona usuario_id."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                row = await conn.fetchrow(
                    "DELETE FROM contacts WHERE id = $1 AND usuario_id = $2 RETURNING id",
                    uuid.UUID(id), uuid.UUID(usuario_id),
                )
            else:
                row = await conn.fetchrow(
                    "DELETE FROM contacts WHERE id = $1 RETURNING id", uuid.UUID(id),
                )
        eliminado = row is not None
        if eliminado:
            log.info("Contacto eliminado: %s", id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando contacto %s: %s", id, exc)
        raise AppError("Error al eliminar contacto", "DB_CONTACTS_DELETE", 500) from exc


async def listar_emails_con_ids(usuario_id: str = None) -> dict:
    """Devuelve dict email.lower() -> contact_id para deteccion de duplicados con ID."""
    try:
        async with get_pool().acquire() as conn:
            if usuario_id:
                rows = await conn.fetch(
                    "SELECT id, email_empresarial, email_personal FROM contacts WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
                )
            else:
                rows = await conn.fetch("SELECT id, email_empresarial, email_personal FROM contacts")
        mapping: dict = {}
        for row in rows:
            contact_id = str(row["id"])
            if row["email_empresarial"]:
                mapping[row["email_empresarial"].lower()] = contact_id
            if row["email_personal"]:
                mapping[row["email_personal"].lower()] = contact_id
        return mapping
    except Exception as exc:
        log.error("Error listando emails con IDs: %s", exc)
        return {}
