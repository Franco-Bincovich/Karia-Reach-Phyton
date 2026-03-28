"""
Servicio de Apollo.io — logica de negocio para busqueda
y enriquecimiento de contactos via Apollo API.
"""

from __future__ import annotations

from integrations import apollo_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import integrations_repository

log = get_logger(__name__)

_SERVICIO = "apollo"


async def esta_configurado() -> bool:
    """Verifica si hay una API key de Apollo activa."""
    key = await integrations_repository.obtener_api_key(_SERVICIO)
    return key is not None


async def guardar_key(api_key: str) -> dict:
    """Guarda la API key de Apollo."""
    return await integrations_repository.guardar_api_key(_SERVICIO, api_key)


async def eliminar_key() -> bool:
    """Elimina (desactiva) la API key de Apollo."""
    eliminado = await integrations_repository.eliminar_api_key(_SERVICIO)
    if not eliminado:
        raise AppError("No hay API key de Apollo configurada", "APOLLO_NOT_CONFIGURED", 404)
    return True


async def _obtener_key() -> str:
    """Obtiene la API key o lanza error si no esta configurada."""
    key = await integrations_repository.obtener_api_key(_SERVICIO)
    if not key:
        raise AppError(
            "Apollo no esta configurado. Guarda tu API key primero.",
            "APOLLO_NOT_CONFIGURED", 400,
        )
    return key


async def buscar_contactos(rubro: str, ubicacion: str, cantidad: int = 10) -> list[dict]:
    """
    Busca contactos via Apollo API.

    Args:
        rubro: titulo o rol a buscar.
        ubicacion: zona geografica.
        cantidad: cantidad de resultados.

    Returns:
        Lista de contactos mapeados a nuestro schema.
    """
    key = await _obtener_key()
    return await apollo_client.buscar_personas(rubro, ubicacion, cantidad, key)


async def enriquecer_contactos(contactos: list[dict]) -> list[dict]:
    """
    Enriquece contactos existentes con datos de Apollo.

    Args:
        contactos: lista de dicts con al menos 'nombre' y 'empresa'.

    Returns:
        Lista de contactos enriquecidos.
    """
    key = await _obtener_key()
    if len(contactos) == 1:
        c = contactos[0]
        return [await apollo_client.enriquecer_contacto(c.get("nombre", ""), c.get("empresa", ""), key)]
    return await apollo_client.enriquecer_bulk(contactos, key)
