"""
Servicio de Apollo.io — logica de negocio para busqueda
y enriquecimiento de contactos via Apollo API.
"""

from __future__ import annotations

from integrations import apollo_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import integrations_repository
from services.contacts_service import filtrar_duplicados

log = get_logger(__name__)

_SERVICIO = "apollo"


async def esta_configurado(usuario_id: str = None) -> bool:
    """Verifica si hay una API key de Apollo activa."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    return key is not None


async def guardar_key(api_key: str, usuario_id: str = None) -> dict:
    """Guarda la API key de Apollo."""
    return await integrations_repository.guardar_api_key(_SERVICIO, api_key, usuario_id)


async def eliminar_key(usuario_id: str = None) -> bool:
    """Elimina (desactiva) la API key de Apollo."""
    eliminado = await integrations_repository.eliminar_api_key(_SERVICIO, usuario_id)
    if not eliminado:
        raise AppError("No hay API key de Apollo configurada", "APOLLO_NOT_CONFIGURED", 404)
    return True


async def _obtener_key(usuario_id: str = None) -> str:
    """Obtiene la API key o lanza error si no esta configurada."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    if not key:
        raise AppError(
            "Apollo no esta configurado. Guarda tu API key primero.",
            "APOLLO_NOT_CONFIGURED", 400,
        )
    return key


async def buscar_contactos(
    rubro: str,
    ubicacion: str,
    cantidad: int = 10,
    usuario_id: str = None,
    cargo: str | None = None,
    tamano_empresa: str | None = None,
    solo_email_verificado: bool = False,
) -> list[dict]:
    """
    Busca contactos via Apollo API.

    Args:
        rubro: titulo o rol a buscar.
        ubicacion: zona geografica.
        cantidad: cantidad de resultados.
        cargo: titulo especifico adicional (opcional).
        tamano_empresa: filtro de tamaño de empresa (opcional).
        solo_email_verificado: si True filtra solo emails verificados.

    Returns:
        Lista de contactos mapeados, filtrados por duplicados, anotados con ya_existe.
    """
    from services.contacts_service import anotar_existencia
    key = await _obtener_key(usuario_id)
    resultados = await apollo_client.buscar_personas(
        rubro, ubicacion, cantidad, key, cargo, tamano_empresa, solo_email_verificado,
    )
    resultados = await filtrar_duplicados(resultados, usuario_id)
    return await anotar_existencia(resultados, usuario_id)


async def enriquecer_contactos(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """
    Enriquece contactos existentes con datos de Apollo.

    Args:
        contactos: lista de dicts con al menos 'nombre' y 'empresa'.

    Returns:
        Lista de contactos enriquecidos.
    """
    key = await _obtener_key(usuario_id)
    if len(contactos) == 1:
        c = contactos[0]
        return [await apollo_client.enriquecer_contacto(c.get("nombre", ""), c.get("empresa", ""), key)]
    return await apollo_client.enriquecer_bulk(contactos, key)
