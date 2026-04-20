"""
Controller de scraping — adapta HTTP a services.

Sin logica de negocio: traduce request a service call y normaliza la respuesta.
"""

from __future__ import annotations

from services import scraping_service


async def buscar(entradas: list[str], usuario_id: str) -> dict:
    """
    Ejecuta scraping sobre la lista de sitios y devuelve contactos encontrados.

    Args:
        entradas: URLs o nombres de sitios a scrapear.
        usuario_id: ID del usuario autenticado.

    Returns:
        Dict con data (lista de contactos) y total (int).
    """
    prefs = await scraping_service.obtener_preferencias(usuario_id)
    contactos = await scraping_service.buscar_por_scraping(entradas, usuario_id, prefs)
    return {"data": contactos, "total": len(contactos)}


async def get_preferencias(usuario_id: str) -> dict:
    """
    Devuelve las preferencias de scraping del usuario.

    Returns:
        Dict con data (preferencias).
    """
    prefs = await scraping_service.obtener_preferencias(usuario_id)
    return {"data": prefs}


async def post_preferencias(usuario_id: str, preferencias: dict) -> dict:
    """
    Guarda las preferencias de scraping del usuario.

    Returns:
        Dict confirmando el guardado.
    """
    await scraping_service.guardar_preferencias(usuario_id, preferencias)
    return {"data": {"guardado": True}}
