"""
Controller de composicion — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import compose_service


async def generar_variantes(
    descripcion: str, tono: str, objetivo: str, variantes: int
) -> dict:
    """Genera variantes de email via IA."""
    emails = await compose_service.generar_variantes(descripcion, tono, objetivo, variantes)
    return {"data": emails, "total": len(emails)}


async def componer_desde_contactos(
    contactos: list[dict], producto: str, modo: str
) -> dict:
    """Compone emails personalizados para contactos."""
    emails = await compose_service.componer_desde_contactos(contactos, producto, modo)
    return {"data": emails, "total": len(emails)}


async def listar_templates() -> dict:
    """Devuelve todos los templates."""
    templates = await compose_service.listar_templates()
    return {"data": templates, "total": len(templates)}


async def guardar_template(template: dict) -> dict:
    """Guarda un template nuevo."""
    creado = await compose_service.guardar_template(template)
    return {"data": creado}


async def eliminar_template(id: str) -> dict:
    """Elimina un template por id."""
    await compose_service.eliminar_template(id)
    return {"deleted": True}
