"""
Repositorio de contactos — unico punto de acceso a la tabla `contacts`.

Campos: id, nombre, empresa, cargo, email_empresarial, email_personal,
telefono_empresa, telefono_personal, linkedin_url, confianza (float 0-1),
origen (ai/manual), created_at.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "contacts"


_CAMPOS_STR_NO_NULL = ("email_empresarial", "email_personal", "telefono_empresa", "telefono_personal", "linkedin_url")


def _normalizar_contacto(contacto: dict) -> dict:
    """Prepara un contacto antes de insertar en DB: vacios a None, confianza a int, campos extra fuera."""
    for campo in _CAMPOS_STR_NO_NULL:
        contacto[campo] = contacto.get(campo) or None
    val = contacto.get("confianza")
    if isinstance(val, float) and val <= 1.0:
        contacto["confianza"] = int(round(val * 100))
    # Eliminar campos internos que no existen como columna en Supabase
    contacto.pop("apollo_id", None)
    return contacto


async def listar_emails() -> set[str]:
    """Devuelve un set con todos los emails existentes (empresarial + personal)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .select("email_empresarial, email_personal").execute()
        ))
        emails = set()
        for row in resp.data:
            if row.get("email_empresarial"):
                emails.add(row["email_empresarial"].lower())
            if row.get("email_personal"):
                emails.add(row["email_personal"].lower())
        return emails
    except Exception as exc:
        log.error("Error listando emails: %s", exc)
        return set()


async def listar() -> list[dict]:
    """Devuelve todos los contactos ordenados por fecha de creacion desc."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*").order("created_at", desc=True).execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando contactos: %s", exc)
        raise AppError("Error al listar contactos", "DB_CONTACTS_LIST", 500) from exc


async def contar() -> int:
    """Devuelve el total de contactos (query liviana, solo cuenta)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("id", count="exact").execute()
        ))
        return resp.count or 0
    except Exception as exc:
        log.error("Error contando contactos: %s", exc)
        raise AppError("Error al contar contactos", "DB_CONTACTS_COUNT", 500) from exc


async def buscar_por_email(email: str) -> Optional[dict]:
    """
    Busca un contacto por email empresarial o personal.

    Primero busca en email_empresarial, si no encuentra busca en email_personal.

    Args:
        email: direccion de email a buscar.

    Returns:
        Dict del contacto o None si no existe.
    """
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("email_empresarial", email).limit(1).execute()
        ))
        if resp.data:
            return resp.data[0]
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("email_personal", email).limit(1).execute()
        ))
        return resp.data[0] if resp.data else None
    except Exception as exc:
        log.error("Error buscando contacto por email %s: %s", email, exc)
        raise AppError("Error al buscar contacto", "DB_CONTACTS_SEARCH", 500) from exc


async def crear(contacto: dict) -> dict:
    """
    Inserta un contacto nuevo.

    Args:
        contacto: dict con los campos del contacto.

    Returns:
        Dict del contacto creado con id y timestamps.
    """
    try:
        _normalizar_contacto(contacto)
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).insert(contacto).execute()
        ))
        log.info("Contacto creado: %s", contacto.get("email_empresarial") or contacto.get("email_personal"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando contacto: %s", exc)
        raise AppError("Error al crear contacto", "DB_CONTACTS_CREATE", 500) from exc


async def crear_bulk(contactos: list[dict]) -> list[dict]:
    """
    Inserta multiples contactos ignorando duplicados por email.

    Args:
        contactos: lista de dicts con campos de contacto.

    Returns:
        Lista de contactos efectivamente insertados.
    """
    # Filtrar emails que ya existen en una sola query
    existentes = await listar_emails()
    nuevos = []
    for c in contactos:
        emp = (c.get("email_empresarial") or "").lower()
        per = (c.get("email_personal") or "").lower()
        if (emp and emp in existentes) or (per and per in existentes):
            continue
        nuevos.append(c)

    if not nuevos:
        log.info("crear_bulk: todos los contactos ya existen, nada que insertar")
        return []

    for c in nuevos:
        _normalizar_contacto(c)
    log.info("Emails existentes en DB: %s", list(existentes)[:10])
    log.info("Emails a insertar: %s", [c.get("email_empresarial") for c in nuevos])
    log.info("Primer contacto antes del insert: linkedin=%s", nuevos[0].get("linkedin_url") if nuevos else "vacío")
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).insert(nuevos).execute()
        ))
        log.info("Bulk insert: %d/%d contactos creados", len(resp.data), len(contactos))
        return resp.data
    except Exception as exc:
        if hasattr(exc, 'code') and exc.code == '23505':
            log.warning("Duplicate key en bulk insert, insertando uno a uno")
            insertados = []
            for c in nuevos:
                try:
                    resp = await loop.run_in_executor(None, lambda c=c: (
                        get_supabase_client().table(_TABLE).insert(c).execute()
                    ))
                    insertados.extend(resp.data)
                except Exception as inner:
                    if hasattr(inner, 'code') and inner.code == '23505':
                        log.info("Duplicado ignorado: %s", c.get("email_empresarial"))
                    else:
                        log.error("Error insertando contacto: %s", inner)
            log.info("Insert uno a uno: %d/%d contactos creados", len(insertados), len(nuevos))
            return insertados
        log.error("Error en bulk insert de contactos: %s", exc)
        raise AppError("Error al crear contactos en bulk", "DB_CONTACTS_BULK", 500) from exc


async def eliminar(id: str) -> bool:
    """
    Elimina un contacto por id.

    Args:
        id: UUID del contacto.

    Returns:
        True si se elimino, False si no existia.
    """
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).delete().eq("id", id).execute()
        ))
        eliminado = len(resp.data) > 0
        if eliminado:
            log.info("Contacto eliminado: %s", id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando contacto %s: %s", id, exc)
        raise AppError("Error al eliminar contacto", "DB_CONTACTS_DELETE", 500) from exc
