"""
Controller de Apollo — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import apollo_service


async def status(usuario_id: str = None) -> dict:
    """Devuelve si Apollo esta configurado."""
    configurado = await apollo_service.esta_configurado(usuario_id)
    return {"data": {"configurado": configurado}}


async def guardar_config(api_key: str, usuario_id: str = None) -> dict:
    """Guarda la API key de Apollo."""
    resultado = await apollo_service.guardar_key(api_key, usuario_id)
    return {"data": resultado}


async def eliminar_config(usuario_id: str = None) -> dict:
    """Elimina la API key de Apollo."""
    await apollo_service.eliminar_key(usuario_id)
    return {"deleted": True}


async def buscar(rubro: str, ubicacion: str, cantidad: int, usuario_id: str = None) -> dict:
    """Busca contactos via Apollo."""
    contactos = await apollo_service.buscar_contactos(rubro, ubicacion, cantidad, usuario_id)
    return {"data": contactos, "total": len(contactos)}


async def enriquecer(contactos: list[dict], usuario_id: str = None) -> dict:
    """Enriquece contactos via Apollo."""
    enriquecidos = await apollo_service.enriquecer_contactos(contactos, usuario_id)
    return {"data": enriquecidos, "total": len(enriquecidos)}
