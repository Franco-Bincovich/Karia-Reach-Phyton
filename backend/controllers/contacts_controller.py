"""
Controller de contactos — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import contacts_service


async def listar(usuario_id: str = None) -> dict:
    """Devuelve todos los contactos."""
    contactos = await contacts_service.listar(usuario_id)
    return {"data": contactos, "total": len(contactos)}


async def buscar_con_ia(
    rubro: str, ubicacion: str, cantidad: int,
    prompt_personalizado: str | None = None,
    usuario_id: str = None,
) -> dict:
    """Busca contactos via IA y devuelve resultados con IDs temporales."""
    contactos = await contacts_service.buscar_con_ia(rubro, ubicacion, cantidad, prompt_personalizado, usuario_id)
    return {"data": contactos, "total": len(contactos)}


async def guardar_seleccion(contactos: list[dict], usuario_id: str = None) -> dict:
    """Guarda contactos seleccionados por el usuario."""
    guardados = await contacts_service.guardar_seleccion(contactos, usuario_id)
    return {"data": guardados, "guardados": len(guardados)}


async def agregar_manual(contacto: dict, usuario_id: str = None) -> dict:
    """Agrega un contacto manual."""
    creado = await contacts_service.agregar_manual(contacto, usuario_id)
    return {"data": creado}


async def eliminar(id: str) -> dict:
    """Elimina un contacto por id."""
    await contacts_service.eliminar(id)
    return {"deleted": True}
