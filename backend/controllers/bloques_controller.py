"""
Controller de bloques — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import bloques_service


async def listar(usuario_id: str = None) -> dict:
    """Devuelve todos los bloques."""
    bloques = await bloques_service.listar(usuario_id)
    return {"data": bloques, "total": len(bloques)}


async def crear(nombre: str, usuario_id: str = None) -> dict:
    """Crea un bloque nuevo."""
    bloque = await bloques_service.crear(nombre, usuario_id)
    return {"data": bloque}


async def eliminar(bloque_id: str) -> dict:
    """Elimina un bloque por id."""
    await bloques_service.eliminar(bloque_id)
    return {"deleted": True}


async def actualizar(bloque_id: str, nombre: str) -> dict:
    """Actualiza el nombre de un bloque."""
    await bloques_service.actualizar(bloque_id, nombre)
    return {"updated": True}


async def eliminar_contacto(bloque_id: str, contacto_id: str) -> dict:
    """Elimina un contacto de un bloque."""
    await bloques_service.eliminar_contacto(bloque_id, contacto_id)
    return {"removed": True}


async def agregar_contactos(bloque_id: str, contacto_ids: list[str]) -> dict:
    """Agrega contactos a un bloque."""
    await bloques_service.agregar_contactos(bloque_id, contacto_ids)
    return {"added": len(contacto_ids)}


async def obtener_contactos(bloque_id: str) -> dict:
    """Devuelve los contactos de un bloque."""
    contactos = await bloques_service.obtener_contactos(bloque_id)
    return {"data": contactos, "total": len(contactos)}
