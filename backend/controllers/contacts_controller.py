"""
Controller de contactos — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import contacts_service


async def listar() -> dict:
    """Devuelve todos los contactos."""
    contactos = await contacts_service.listar()
    return {"data": contactos, "total": len(contactos)}


async def buscar_con_ia(
    rubro: str, ubicacion: str, cantidad: int,
    prompt_personalizado: str | None = None,
) -> dict:
    """Busca contactos via IA y devuelve resultados con IDs temporales."""
    contactos = await contacts_service.buscar_con_ia(rubro, ubicacion, cantidad, prompt_personalizado)
    return {"data": contactos, "total": len(contactos)}


async def guardar_seleccion(contactos: list[dict]) -> dict:
    """Guarda contactos seleccionados por el usuario."""
    guardados = await contacts_service.guardar_seleccion(contactos)
    return {"data": guardados, "guardados": len(guardados)}


async def agregar_manual(contacto: dict) -> dict:
    """Agrega un contacto manual."""
    creado = await contacts_service.agregar_manual(contacto)
    return {"data": creado}


async def eliminar(id: str) -> dict:
    """Elimina un contacto por id."""
    await contacts_service.eliminar(id)
    return {"deleted": True}
