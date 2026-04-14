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


_CAMPOS_STR_NO_NULL = (
    "email_empresarial", "email_personal", "telefono_empresa", "telefono_personal",
    "linkedin_url", "instagram_username", "facebook_url", "whatsapp",
    "website", "direccion", "ciudad", "pais",
)

_CAMPOS_MERGE = (
    "cargo", "email_empresarial", "email_personal", "telefono_empresa", "telefono_personal",
    "linkedin_url", "instagram_username", "facebook_url", "whatsapp",
    "website", "direccion", "ciudad", "pais", "confianza",
)


def _normalizar_contacto(contacto: dict) -> dict:
    """Prepara un contacto antes de insertar en DB: vacios a None, confianza normalizada, campos extra fuera."""
    for campo in _CAMPOS_STR_NO_NULL:
        contacto[campo] = contacto.get(campo) or None
    val = contacto.get("confianza")
    if val is not None:
        val = float(val)
        # Si viene como int 0-100 (legacy), convertir a float 0-1
        if val > 1.0:
            val = val / 100.0
        contacto["confianza"] = max(0.0, min(1.0, val))
    contacto.pop("apollo_id", None)
    return contacto


async def listar_emails(usuario_id: str = None) -> set[str]:
    """Devuelve un set con todos los emails existentes (empresarial + personal)."""
    try:
        loop = asyncio.get_event_loop()
        def _q():
            q = get_supabase_client().table(_TABLE).select("email_empresarial, email_personal")
            if usuario_id:
                q = q.eq("usuario_id", usuario_id)
            return q.execute()
        resp = await loop.run_in_executor(None, _q)
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


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los contactos ordenados por fecha de creacion desc."""
    try:
        loop = asyncio.get_event_loop()
        def _q():
            q = get_supabase_client().table(_TABLE).select("*").order("created_at", desc=True)
            if usuario_id:
                q = q.eq("usuario_id", usuario_id)
            return q.execute()
        resp = await loop.run_in_executor(None, _q)
        return resp.data
    except Exception as exc:
        log.error("Error listando contactos: %s", exc)
        raise AppError("Error al listar contactos", "DB_CONTACTS_LIST", 500) from exc


async def contar(usuario_id: str = None) -> int:
    """Devuelve el total de contactos (query liviana, solo cuenta)."""
    try:
        loop = asyncio.get_event_loop()
        def _q():
            q = get_supabase_client().table(_TABLE).select("id", count="exact")
            if usuario_id:
                q = q.eq("usuario_id", usuario_id)
            return q.execute()
        resp = await loop.run_in_executor(None, _q)
        return resp.count or 0
    except Exception as exc:
        log.error("Error contando contactos: %s", exc)
        raise AppError("Error al contar contactos", "DB_CONTACTS_COUNT", 500) from exc


async def listar_por_ids(ids: list[str], usuario_id: str) -> list[dict]:
    """Devuelve contactos por lista de IDs, filtrados por usuario_id."""
    if not ids:
        return []
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .in_("id", ids).eq("usuario_id", usuario_id).execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando contactos por IDs: %s", exc)
        raise AppError("Error al listar contactos", "DB_CONTACTS_BY_IDS", 500) from exc


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
    log.info("Emails existentes en DB: %d encontrados", len(existentes))
    log.info("Contactos a insertar: %d", len(nuevos))
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


async def listar_emails_con_ids(usuario_id: str = None) -> dict:
    """Devuelve dict email.lower() -> contact_id para deteccion de duplicados con ID."""
    try:
        loop = asyncio.get_event_loop()
        def _q():
            q = get_supabase_client().table(_TABLE).select("id, email_empresarial, email_personal")
            if usuario_id:
                q = q.eq("usuario_id", usuario_id)
            return q.execute()
        resp = await loop.run_in_executor(None, _q)
        mapping = {}
        for row in resp.data:
            if row.get("email_empresarial"):
                mapping[row["email_empresarial"].lower()] = row["id"]
            if row.get("email_personal"):
                mapping[row["email_personal"].lower()] = row["id"]
        return mapping
    except Exception as exc:
        log.error("Error listando emails con IDs: %s", exc)
        return {}


async def find_similar(
    usuario_id: str,
    nombre: str = None,
    empresa: str = None,
    email: str = None,
) -> Optional[dict]:
    """Busca un contacto existente por email o por nombre+empresa (coincidencia parcial)."""
    if email:
        try:
            encontrado = await buscar_por_email(email)
            if encontrado and encontrado.get("usuario_id") == usuario_id:
                return encontrado
        except Exception:
            pass
    if nombre and empresa:
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: (
                get_supabase_client().table(_TABLE).select("*")
                .eq("usuario_id", usuario_id)
                .ilike("nombre", f"%{nombre}%")
                .ilike("empresa", f"%{empresa}%")
                .limit(1).execute()
            ))
            return resp.data[0] if resp.data else None
        except Exception as exc:
            log.error("Error en find_similar nombre/empresa: %s", exc)
    return None


async def merge_contact(contact_id: str, nuevos_datos: dict, source: str, usuario_id: str) -> dict:
    """
    Actualiza un contacto solo en los campos que estan vacios/nulos.

    Args:
        contact_id: UUID del contacto a actualizar.
        nuevos_datos: dict con los datos nuevos a mergear.
        source: nombre del origen del enriquecimiento (ej: 'claude', 'apollo').
        usuario_id: ID del usuario propietario.

    Returns:
        Dict del contacto actualizado.
    """
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("id", contact_id).eq("usuario_id", usuario_id).limit(1).execute()
        ))
        if not resp.data:
            raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
        actual = resp.data[0]
        campos_a_actualizar: dict = {}
        for campo in _CAMPOS_MERGE:
            valor_nuevo = nuevos_datos.get(campo)
            valor_actual = actual.get(campo)
            if valor_nuevo and not valor_actual:
                campos_a_actualizar[campo] = valor_nuevo
        # Acumular enrichment_sources
        sources_actuales = actual.get("enrichment_sources") or []
        if source not in sources_actuales:
            sources_actuales = list(sources_actuales) + [source]
            campos_a_actualizar["enrichment_sources"] = sources_actuales
        if not campos_a_actualizar:
            log.info("merge_contact %s: nada nuevo para mergear", contact_id)
            return actual
        resp_update = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).update(campos_a_actualizar)
            .eq("id", contact_id).execute()
        ))
        log.info("merge_contact %s: campos actualizados %s", contact_id, list(campos_a_actualizar.keys()))
        return resp_update.data[0] if resp_update.data else actual
    except AppError:
        raise
    except Exception as exc:
        log.error("Error en merge_contact %s: %s", contact_id, exc)
        raise AppError("Error al actualizar contacto", "DB_CONTACTS_MERGE", 500) from exc


async def save_enrichment_log(
    contact_id: str, usuario_id: str, source: str, fields_added: list,
) -> None:
    """Guarda un registro de enriquecimiento. Falla silenciosamente si la tabla no existe."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: (
            get_supabase_client().table("enrichment_logs").insert({
                "contact_id": contact_id,
                "usuario_id": usuario_id,
                "source": source,
                "fields_added": fields_added,
            }).execute()
        ))
    except Exception as exc:
        log.warning("save_enrichment_log: no se pudo guardar (%s)", exc)
