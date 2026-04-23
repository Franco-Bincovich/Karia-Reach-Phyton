"""
Controller de Apify — thin layer que delega al servicio de enriquecimiento.
"""
from __future__ import annotations

from middleware.error_handler import AppError
from repositories import integrations_repository
from services import apify_service

_SERVICIO = "apify"


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


async def enriquecer_contacto(contacto_id: str, usuario_id: str = None) -> dict:
    """Enriquece un contacto existente con el pipeline de Apify."""
    return await apify_service.enriquecer_contacto(contacto_id, usuario_id)


async def buscar(rubro: str, ubicacion: str, pais: str, cantidad: int) -> dict:
    """Busca negocios en Google Maps via Apify."""
    return await apify_service.buscar(rubro, ubicacion, pais, cantidad)


async def buscar_instagram(handles: list, max_por_perfil: int, usuario_id: str) -> dict:
    """Busca contactos de Instagram desde perfiles de competencia."""
    return await apify_service.buscar_instagram(handles, max_por_perfil, usuario_id)
