"""
Servicio de bloques — logica de negocio para gestion
de bloques de contactos.
"""

from __future__ import annotations

from logger import get_logger
from middleware.error_handler import AppError
from repositories import bloques_repository

log = get_logger(__name__)


def _require_uid(usuario_id: str | None) -> str:
    """Valida que usuario_id esté presente."""
    if not usuario_id:
        raise AppError("Token inválido o expirado", "AUTH_REQUIRED", 401)
    return usuario_id


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los bloques con cantidad de contactos."""
    _require_uid(usuario_id)
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
    _require_uid(usuario_id)
    return await bloques_repository.crear(nombre, usuario_id)


async def eliminar(bloque_id: str) -> None:
    """
    Elimina un bloque por id.

    Args:
        bloque_id: UUID del bloque.

    Raises:
        AppError: si el bloque no existe.
    """
    eliminado = await bloques_repository.eliminar(bloque_id)
    if not eliminado:
        raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)


async def actualizar(bloque_id: str, nombre: str) -> None:
    """
    Actualiza el nombre de un bloque.

    Args:
        bloque_id: UUID del bloque.
        nombre: nuevo nombre.

    Raises:
        AppError: si el bloque no existe.
    """
    actualizado = await bloques_repository.actualizar(bloque_id, nombre)
    if not actualizado:
        raise AppError("Bloque no encontrado", "BLOQUE_NOT_FOUND", 404)


async def eliminar_contacto(bloque_id: str, contacto_id: str) -> None:
    """
    Elimina un contacto de un bloque.

    Args:
        bloque_id: UUID del bloque.
        contacto_id: UUID del contacto.

    Raises:
        AppError: si la relacion no existe.
    """
    eliminado = await bloques_repository.eliminar_contacto(bloque_id, contacto_id)
    if not eliminado:
        raise AppError("Contacto no encontrado en el bloque", "BLOQUE_CONTACT_NOT_FOUND", 404)


async def agregar_contactos(bloque_id: str, contacto_ids: list[str]) -> None:
    """
    Agrega contactos a un bloque.

    Args:
        bloque_id: UUID del bloque.
        contacto_ids: lista de UUIDs de contactos.
    """
    if not contacto_ids:
        raise AppError("Debe enviar al menos un contacto", "BLOQUES_EMPTY", 400)
    await bloques_repository.agregar_contactos(bloque_id, contacto_ids)


async def obtener_contactos(bloque_id: str) -> list[dict]:
    """
    Devuelve los contactos completos de un bloque.

    Args:
        bloque_id: UUID del bloque.

    Returns:
        Lista de contactos del bloque.
    """
    return await bloques_repository.obtener_contactos(bloque_id)
