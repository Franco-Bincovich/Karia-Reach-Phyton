"""
Controller de Perplexity — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import perplexity_service


async def status(usuario_id: str = None) -> dict:
    """Devuelve si Perplexity esta configurado."""
    configurado = await perplexity_service.esta_configurado(usuario_id)
    return {"data": {"configurado": configurado}}


async def guardar_config(api_key: str, usuario_id: str = None) -> dict:
    """Guarda la API key de Perplexity."""
    resultado = await perplexity_service.guardar_key(api_key, usuario_id)
    return {"data": resultado}


async def eliminar_config(usuario_id: str = None) -> dict:
    """Elimina la API key de Perplexity."""
    await perplexity_service.eliminar_key(usuario_id)
    return {"deleted": True}


async def buscar(
    rubro: str, ubicacion: str, cantidad: int,
    prompt_personalizado: str | None = None, usuario_id: str = None,
) -> dict:
    """Busca contactos via Perplexity."""
    contactos = await perplexity_service.buscar_contactos(
        rubro, ubicacion, cantidad, prompt_personalizado, usuario_id,
    )
    return {"data": contactos, "total": len(contactos)}
