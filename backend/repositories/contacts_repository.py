"""
Repositorio de contactos — unico punto de acceso a la tabla `contacts`.

Campos: id, nombre, empresa, cargo, email_empresarial, email_personal,
telefono_empresa, telefono_personal, linkedin_url, confianza (smallint 0-100),
origen (contact_source enum), enrichment_sources (JSONB), created_at, updated_at.
Usa asyncpg directamente contra el pool de Postgres local.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

import asyncpg

from integrations.postgres_client import get_pool
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

_COLUMNAS_CONTACTS = frozenset({
    "nombre", "empresa", "email_empresarial", "email_personal", "cargo", "confianza",
    "origen", "telefono_empresa", "telefono_personal", "linkedin_url", "rubro",
    "instagram_username", "facebook_url", "whatsapp", "twitter_url", "tiktok_username",
    "website", "direccion", "ciudad", "pais", "usuario_id",
    "enrichment_sources", "last_enriched_at",
})


def _normalizar_contacto(contacto: dict) -> dict:
    """Prepara un contacto antes de insertar en DB: vacios a None, confianza normalizada, campos extra fuera."""
    for campo in _CAMPOS_STR_NO_NULL:
        contacto[campo] = contacto.get(campo) or None
    val = contacto.get("confianza")
    if val is not None:
        val = float(val)
        if val > 1.0:
            val = val / 100.0
        contacto["confianza"] = max(0.0, min(1.0, val))
    contacto.pop("apollo_id", None)
    return contacto


def _record_to_dict(record) -> dict:
    """Convierte un Record de asyncpg a dict con tipos Python normalizados."""
    row = dict(record)
    for key, val in list(row.items()):
        if isinstance(val, uuid.UUID):
            row[key] = str(val)
        elif isinstance(val, datetime):
            row[key] = val.isoformat()
        elif key == "enrichment_sources":
            if isinstance(val, str):
                try:
                    row[key] = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    row[key] = []
            elif val is None:
                row[key] = []
    return row


def _confianza_to_db(val: float) -> int:
    """Convierte confianza float 0-1 a smallint 0-100 para Postgres."""
    return int(round(val * 100))


def _build_insert_parts(datos: dict) -> tuple[list[str], list[str], list]:
    """
    Arma listas de columnas, placeholders y valores para un INSERT dinamico.

    Maneja columnas especiales: origen usa cast ::contact_source,
    enrichment_sources se serializa con json.dumps, usuario_id se convierte a UUID.

    Returns:
        Tupla (cols, placeholders, vals).
    """
    datos_filtrados = {k: v for k, v in datos.items() if k in _COLUMNAS_CONTACTS}
    cols, placeholders, vals = [], [], []
    for i, (col, val) in enumerate(datos_filtrados.items(), 1):
        cols.append(col)
        if col == "origen":
            placeholders.append(f"${i}::contact_source")
        else:
            placeholders.append(f"${i}")
        if col == "enrichment_sources" and val is not None:
            val = json.dumps(val)
        elif col == "usuario_id" and isinstance(val, str):
            val = uuid.UUID(val)
        vals.append(val)
    return cols, placeholders, vals


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
                rows = await conn.fetch(
                    "SELECT email_empresarial, email_personal FROM contacts"
                )
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
                    "SELECT COUNT(*) FROM contacts WHERE usuario_id = $1",
                    uuid.UUID(usuario_id),
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
                uuid_ids,
                uuid.UUID(usuario_id),
            )
        return [_record_to_dict(r) for r in rows]
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
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE email_empresarial = $1 LIMIT 1", email
            )
            if row is None:
                row = await conn.fetchrow(
                    "SELECT * FROM contacts WHERE email_personal = $1 LIMIT 1", email
                )
        return _record_to_dict(row) if row else None
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
        if contacto.get("confianza") is not None:
            contacto["confianza"] = _confianza_to_db(contacto["confianza"])
        cols, placeholders, vals = _build_insert_parts(contacto)
        query = (
            f"INSERT INTO contacts ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING *"
        )
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, *vals)
        log.info("Contacto creado: %s", contacto.get("email_empresarial") or contacto.get("email_personal"))
        return _record_to_dict(row)
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
        if c.get("confianza") is not None:
            c["confianza"] = _confianza_to_db(c["confianza"])

    log.info("Emails existentes en DB: %d encontrados", len(existentes))
    log.info("Contactos a insertar: %d", len(nuevos))

    insertados = []
    async with get_pool().acquire() as conn:
        for c in nuevos:
            try:
                cols, placeholders, vals = _build_insert_parts(c)
                query = (
                    f"INSERT INTO contacts ({', '.join(cols)}) "
                    f"VALUES ({', '.join(placeholders)}) RETURNING *"
                )
                row = await conn.fetchrow(query, *vals)
                insertados.append(_record_to_dict(row))
            except asyncpg.UniqueViolationError:
                log.info("Duplicado ignorado: %s", c.get("email_empresarial"))
            except Exception as exc:
                log.error("Error insertando contacto en bulk: %s", exc)

    log.info("Bulk insert: %d/%d contactos creados", len(insertados), len(contactos))
    return insertados


async def eliminar(id: str) -> bool:
    """
    Elimina un contacto por id.

    Args:
        id: UUID del contacto.

    Returns:
        True si se elimino, False si no existia.
    """
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM contacts WHERE id = $1 RETURNING id",
                uuid.UUID(id),
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
                rows = await conn.fetch(
                    "SELECT id, email_empresarial, email_personal FROM contacts"
                )
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
            async with get_pool().acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM contacts "
                    "WHERE usuario_id = $1 AND nombre ILIKE $2 AND empresa ILIKE $3 "
                    "LIMIT 1",
                    uuid.UUID(usuario_id),
                    f"%{nombre}%",
                    f"%{empresa}%",
                )
            return _record_to_dict(row) if row else None
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
    _normalizar_contacto(nuevos_datos)
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(contact_id),
                uuid.UUID(usuario_id),
            )
            if not row:
                raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
            actual = _record_to_dict(row)

            campos_a_actualizar: dict = {}
            for campo in _CAMPOS_MERGE:
                valor_nuevo = nuevos_datos.get(campo)
                valor_actual = actual.get(campo)
                if valor_nuevo and not valor_actual:
                    campos_a_actualizar[campo] = valor_nuevo

            if "confianza" in campos_a_actualizar and campos_a_actualizar["confianza"] is not None:
                campos_a_actualizar["confianza"] = _confianza_to_db(campos_a_actualizar["confianza"])

            sources_actuales = actual.get("enrichment_sources") or []
            if isinstance(sources_actuales, str):
                sources_actuales = json.loads(sources_actuales)
            if source not in sources_actuales:
                sources_actuales = list(sources_actuales) + [source]
                campos_a_actualizar["enrichment_sources"] = sources_actuales

            if not campos_a_actualizar:
                log.info("merge_contact %s: nada nuevo para mergear", contact_id)
                return actual

            campos_validos = {k: v for k, v in campos_a_actualizar.items() if k in _COLUMNAS_CONTACTS}
            set_clauses, vals = [], []
            for i, (col, val) in enumerate(campos_validos.items(), 1):
                if col == "origen":
                    set_clauses.append(f"{col} = ${i}::contact_source")
                else:
                    set_clauses.append(f"{col} = ${i}")
                if col == "enrichment_sources" and val is not None:
                    val = json.dumps(val)
                vals.append(val)

            vals.append(uuid.UUID(contact_id))
            query = (
                f"UPDATE contacts SET {', '.join(set_clauses)} "
                f"WHERE id = ${len(vals)} RETURNING *"
            )
            updated_row = await conn.fetchrow(query, *vals)

        log.info("merge_contact %s: campos actualizados %s", contact_id, list(campos_validos.keys()))
        return _record_to_dict(updated_row) if updated_row else actual

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
        async with get_pool().acquire() as conn:
            await conn.execute(
                "INSERT INTO contact_enrichments (contact_id, usuario_id, source, fields_added) "
                "VALUES ($1, $2, $3, $4)",
                uuid.UUID(contact_id),
                uuid.UUID(usuario_id),
                source,
                json.dumps(fields_added),
            )
    except Exception as exc:
        log.warning("save_enrichment_log: no se pudo guardar (%s)", exc)
