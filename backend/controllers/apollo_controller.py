"""
Controller de Apollo — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import apollo_service


async def status() -> dict:
    """Devuelve si Apollo esta configurado."""
    configurado = await apollo_service.esta_configurado()
    return {"data": {"configurado": configurado}}


async def guardar_config(api_key: str) -> dict:
    """Guarda la API key de Apollo."""
    resultado = await apollo_service.guardar_key(api_key)
    return {"data": resultado}


async def eliminar_config() -> dict:
    """Elimina la API key de Apollo."""
    await apollo_service.eliminar_key()
    return {"deleted": True}


async def buscar(rubro: str, ubicacion: str, cantidad: int) -> dict:
    """Busca contactos via Apollo."""
    contactos = await apollo_service.buscar_contactos(rubro, ubicacion, cantidad)
    return {"data": contactos, "total": len(contactos)}


async def enriquecer(contactos: list[dict]) -> dict:
    """Enriquece contactos via Apollo."""
    enriquecidos = await apollo_service.enriquecer_contactos(contactos)
    return {"data": enriquecidos, "total": len(enriquecidos)}
