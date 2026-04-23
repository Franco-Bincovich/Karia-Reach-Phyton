"""
Repositorio de búsqueda y enriquecimiento de contactos — busqueda por email,
similitud y merge no-destructivo de campos.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from utils.db import record_to_dict
from ._contacts_base import (
    _normalizar_contacto, _confianza_to_db,
    _CAMPOS_MERGE, _COLUMNAS_CONTACTS,
)

log = get_logger(__name__)


async def buscar_por_email(email: str) -> Optional[dict]:
    """Busca un contacto por email empresarial o personal."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE email_empresarial = $1 LIMIT 1", email
            )
            if row is None:
                row = await conn.fetchrow(
                    "SELECT * FROM contacts WHERE email_personal = $1 LIMIT 1", email
                )
        return record_to_dict(row) if row else None
    except Exception as exc:
        log.error("Error buscando contacto por email %s: %s", email, exc)
        raise AppError("Error al buscar contacto", "DB_CONTACTS_SEARCH", 500) from exc


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
                    "WHERE usuario_id = $1 AND nombre ILIKE $2 AND empresa ILIKE $3 LIMIT 1",
                    uuid.UUID(usuario_id), f"%{nombre}%", f"%{empresa}%",
                )
            return record_to_dict(row) if row else None
        except Exception as exc:
            log.error("Error en find_similar nombre/empresa: %s", exc)
    return None


async def merge_contact(contact_id: str, nuevos_datos: dict, source: str, usuario_id: str) -> dict:
    """Actualiza un contacto solo en los campos que estan vacios/nulos."""
    _normalizar_contacto(nuevos_datos)
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(contact_id), uuid.UUID(usuario_id),
            )
            if not row:
                raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
            actual = record_to_dict(row)

            campos_a_actualizar: dict = {
                campo: nuevos_datos.get(campo)
                for campo in _CAMPOS_MERGE
                if nuevos_datos.get(campo) and not actual.get(campo)
            }
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
                set_clauses.append(f"{col} = ${i}::contact_source" if col == "origen" else f"{col} = ${i}")
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
        return record_to_dict(updated_row) if updated_row else actual

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
                uuid.UUID(contact_id), uuid.UUID(usuario_id), source, json.dumps(fields_added),
            )
    except Exception as exc:
        log.warning("save_enrichment_log: no se pudo guardar (%s)", exc)
