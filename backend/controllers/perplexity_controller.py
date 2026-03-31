"""
Controller de Perplexity — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import perplexity_service


async def status() -> dict:
    """Devuelve si Perplexity esta configurado."""
    configurado = await perplexity_service.esta_configurado()
    return {"data": {"configurado": configurado}}


async def guardar_config(api_key: str) -> dict:
    """Guarda la API key de Perplexity."""
    resultado = await perplexity_service.guardar_key(api_key)
    return {"data": resultado}


async def eliminar_config() -> dict:
    """Elimina la API key de Perplexity."""
    await perplexity_service.eliminar_key()
    return {"deleted": True}


async def buscar(
    rubro: str, ubicacion: str, cantidad: int,
    prompt_personalizado: str | None = None,
) -> dict:
    """Busca contactos via Perplexity."""
    contactos = await perplexity_service.buscar_contactos(
        rubro, ubicacion, cantidad, prompt_personalizado,
    )
    return {"data": contactos, "total": len(contactos)}
