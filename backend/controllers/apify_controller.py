"""
Controller de Apify — thin layer que delega al servicio de enriquecimiento.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from config.settings import get_settings
from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from repositories import integrations_repository
from services import apify_enriquecimiento_service

log = get_logger(__name__)
settings = get_settings()

_SERVICIO = "apify"


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


async def _obtener_key(usuario_id: str = None) -> str:
    """Obtiene API key de DB o .env."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    return key or settings.APIFY_API_KEY


async def status(usuario_id: str = None) -> dict:
    """Verifica si Apify esta configurado en DB para este usuario."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    return {"data": {"configurado": bool(key)}}


async def guardar_config(api_key: str, usuario_id: str = None) -> dict:
    """Guarda la API key de Apify en DB."""
    await integrations_repository.guardar_api_key(_SERVICIO, api_key, usuario_id)
    return {"data": {"guardado": True}}


async def eliminar_config(usuario_id: str = None) -> dict:
    """Elimina la API key de Apify de DB."""
    eliminado = await integrations_repository.eliminar_api_key(_SERVICIO, usuario_id)
    if not eliminado:
        raise AppError("No hay API key de Apify configurada", "APIFY_NOT_CONFIGURED", 404)
    return {"deleted": True}


async def enriquecer_contacto(contacto_id: str) -> dict:
    """
    Enriquece un contacto existente con el pipeline de Apify.

    Args:
        contacto_id: UUID del contacto en la base de datos.

    Returns:
        Dict con el contacto actualizado.
    """
    # Obtener contacto actual
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM contacts WHERE id = $1 LIMIT 1",
            uuid.UUID(contacto_id),
        )
    if not row:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)

    contacto = _record_to_dict(row)

    # Ejecutar pipeline
    datos = await apify_enriquecimiento_service.enriquecer_contacto(contacto)
    if not datos:
        return {"data": contacto, "enriquecido": False}

    # Filtrar solo campos con valor y que existen como columna
    campos_validos = {
        "nombre", "empresa", "cargo", "email_empresarial", "email_personal",
        "telefono_empresa", "telefono_personal", "linkedin_url", "confianza",
        "instagram_username", "facebook_url", "whatsapp", "twitter_url",
        "tiktok_username", "website", "direccion", "ciudad", "pais",
    }
    update_data = {}
    for k, v in datos.items():
        if k in campos_validos and v:
            # No sobreescribir campos que ya tienen valor
            if not contacto.get(k):
                update_data[k] = v

    # Normalizar confianza a float 0-1 (se convierte a smallint 0-100 al guardar)
    if "confianza" in update_data:
        val = float(update_data["confianza"])
        update_data["confianza"] = max(0.0, min(1.0, val if val <= 1.0 else val / 100.0))

    # Remover emails que ya existen en otro contacto para evitar duplicados
    for email_field in ("email_empresarial", "email_personal"):
        email_val = update_data.get(email_field)
        if email_val:
            try:
                async with get_pool().acquire() as conn:
                    existing = await conn.fetchrow(
                        f"SELECT id FROM contacts WHERE {email_field} = $1 AND id != $2 LIMIT 1",
                        email_val,
                        uuid.UUID(contacto_id),
                    )
                if existing:
                    del update_data[email_field]
                    log.warning("Email %s ya existe en otro contacto, no se actualiza", email_val)
            except Exception as exc:
                log.error("Error verificando email duplicado %s: %s", email_field, exc)
                continue

    if update_data:
        update_data["origen"] = "apify"
        set_clauses, vals = [], []
        for i, (col, val) in enumerate(update_data.items(), 1):
            if col == "origen":
                set_clauses.append(f"{col} = ${i}::contact_source")
            else:
                set_clauses.append(f"{col} = ${i}")
            if col == "confianza":
                val = int(round(float(val) * 100))  # float 0-1 → smallint 0-100
            vals.append(val)
        vals.append(uuid.UUID(contacto_id))
        query = (
            f"UPDATE contacts SET {', '.join(set_clauses)} "
            f"WHERE id = ${len(vals)} RETURNING *"
        )
        async with get_pool().acquire() as conn:
            updated_row = await conn.fetchrow(query, *vals)
        log.info("Contacto %s enriquecido con %d campos", contacto_id, len(update_data))
        return {"data": _record_to_dict(updated_row), "enriquecido": True}

    return {"data": contacto, "enriquecido": False}


async def buscar(rubro: str, ubicacion: str, pais: str, cantidad: int) -> dict:
    """
    Busca negocios en Google Maps via Apify.

    Args:
        rubro: tipo de negocio.
        ubicacion: ciudad o zona.
        pais: pais de la busqueda.
        cantidad: max resultados.

    Returns:
        Dict con lista de contactos encontrados.
    """
    contactos = await apify_enriquecimiento_service.buscar_por_maps(rubro, ubicacion, pais, cantidad)
    return {"data": contactos, "total": len(contactos)}
