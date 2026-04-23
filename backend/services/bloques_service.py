"""
Servicio de bloques — logica de negocio para gestion
de bloques de contactos.
"""

from __future__ import annotations

from logger import get_logger
from middleware.error_handler import AppError
from repositories import bloques_repository
from utils.helpers import require_uid

log = get_logger(__name__)


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los bloques con cantidad de contactos."""
    require_uid(usuario_id)
    return await bloques_repository.listar(usuario_id)


async def crear(nombre: str, usuario_id: str = None) -> dict:
    """
    Crea un bloque nuevo.

    Args:
        nombre: nombre del bloque.
        usuario_id: ID del usuario propietario.

    Returns:
        Dict del bloque creado.
    """
    require_uid(usuario_id)
    return await bloques_repository.crear(nombre, usuario_id)


async def eliminar(bloque_id: str, usuario_id: str = None) -> None:
    uid = require_uid(usuario_id)
    eliminado = await bloques_repository.eliminar(bloque_id, uid)
    if not eliminado:
        raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)


async def actualizar(bloque_id: str, nombre: str, usuario_id: str = None) -> None:
    uid = require_uid(usuario_id)
    actualizado = await bloques_repository.actualizar(bloque_id, nombre, uid)
    if not actualizado:
        raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)


async def eliminar_contacto(bloque_id: str, contacto_id: str, usuario_id: str = None) -> None:
    uid = require_uid(usuario_id)
    eliminado = await bloques_repository.eliminar_contacto(bloque_id, contacto_id, uid)
    if not eliminado:
        raise AppError("Contacto no encontrado en el bloque", "BLOQUE_CONTACT_NOT_FOUND", 404)


async def agregar_contactos(bloque_id: str, contacto_ids: list[str], usuario_id: str = None) -> None:
    uid = require_uid(usuario_id)
    if not contacto_ids:
        raise AppError("Debe enviar al menos un contacto", "BLOQUES_EMPTY", 400)
    await bloques_repository.agregar_contactos(bloque_id, contacto_ids, uid)


async def obtener_contactos(bloque_id: str, usuario_id: str = None) -> list[dict]:
    uid = require_uid(usuario_id)
    return await bloques_repository.obtener_contactos(bloque_id, uid)
