"""
Controller de Apify — thin layer que delega al servicio de enriquecimiento.
"""

from __future__ import annotations

import asyncio

from config.settings import get_settings
from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import integrations_repository
from services import apify_enriquecimiento_service

log = get_logger(__name__)
settings = get_settings()

_SERVICIO = "apify"


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
        contacto_id: UUID del contacto en Supabase.

    Returns:
        Dict con el contacto actualizado.
    """
    # Obtener contacto actual
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, lambda: (
        get_supabase_client().table("contacts")
        .select("*").eq("id", contacto_id).limit(1).execute()
    ))
    if not resp.data:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)

    contacto = resp.data[0]

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

    # Normalizar confianza de float a int para DB
    if "confianza" in update_data:
        val = update_data["confianza"]
        if isinstance(val, float) and val <= 1.0:
            update_data["confianza"] = int(round(val * 100))

    # Remover emails que ya existen en otro contacto para evitar duplicados
    for email_field in ("email_empresarial", "email_personal"):
        email_val = update_data.get(email_field)
        if email_val:
            existing = await loop.run_in_executor(None, lambda ev=email_val, ef=email_field: (
                get_supabase_client().table("contacts")
                .select("id").eq(ef, ev).neq("id", contacto_id).limit(1).execute()
            ))
            if existing.data:
                del update_data[email_field]
                log.warning("Email %s ya existe en otro contacto, no se actualiza", email_val)

    if update_data:
        update_data["origen"] = "apify"
        await loop.run_in_executor(None, lambda: (
            get_supabase_client().table("contacts")
            .update(update_data).eq("id", contacto_id).execute()
        ))
        log.info("Contacto %s enriquecido con %d campos", contacto_id, len(update_data))

    # Retornar contacto actualizado
    resp = await loop.run_in_executor(None, lambda: (
        get_supabase_client().table("contacts")
        .select("*").eq("id", contacto_id).limit(1).execute()
    ))
    return {"data": resp.data[0], "enriquecido": bool(update_data)}


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
