"""
Servicio de contactos — logica de negocio sobre busqueda,
creacion y gestion de contactos comerciales.
"""

from __future__ import annotations

import time

from integrations import claude_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import contacts_repository

log = get_logger(__name__)

_MAX_SELECCION = 50


async def buscar_con_ia(rubro: str, ubicacion: str, cantidad: int = 10) -> list[dict]:
    """
    Busca contactos via IA y les asigna IDs temporales.

    Args:
        rubro: industria o sector a buscar.
        ubicacion: zona geografica.
        cantidad: contactos a buscar (default 10).

    Returns:
        Lista de contactos con id temporal ai-{timestamp}-{index}.
    """
    resultados = await claude_client.buscar_contactos(rubro, ubicacion, cantidad)
    # IDs temporales para que el frontend pueda referenciar cada contacto
    # antes de persistirlo. Se limpian en guardar_seleccion() con c.pop("id")
    # cuando el usuario confirma la seleccion y se insertan en DB con UUID real.
    ts = int(time.time())
    for i, contacto in enumerate(resultados):
        contacto["id"] = f"ai-{ts}-{i}"
        contacto["origen"] = "ai"
    log.info("Busqueda IA: %d contactos encontrados para %s en %s", len(resultados), rubro, ubicacion)
    return resultados


async def guardar_seleccion(contactos: list[dict]) -> list[dict]:
    """
    Guarda una seleccion de contactos en la base de datos.

    Args:
        contactos: lista de contactos seleccionados por el usuario.

    Returns:
        Lista de contactos efectivamente guardados.

    Raises:
        AppError: si se excede el maximo de 50 contactos.
    """
    if len(contactos) > _MAX_SELECCION:
        raise AppError(
            f"Maximo {_MAX_SELECCION} contactos por seleccion",
            "CONTACTS_LIMIT_EXCEEDED", 400,
        )
    # Limpiar IDs temporales antes de persistir
    for c in contactos:
        c.pop("id", None)
        c.setdefault("origen", "ai")
    return await contacts_repository.crear_bulk(contactos)


async def agregar_manual(contacto: dict) -> dict:
    """
    Agrega un contacto ingresado manualmente.

    Args:
        contacto: dict con datos del contacto.

    Returns:
        Contacto creado con id y timestamps.
    """
    contacto["confianza"] = 1.0
    contacto["origen"] = "manual"
    return await contacts_repository.crear(contacto)


async def listar() -> list[dict]:
    """Devuelve todos los contactos."""
    return await contacts_repository.listar()


async def eliminar(id: str) -> bool:
    """
    Elimina un contacto por id.

    Args:
        id: UUID del contacto.

    Returns:
        True si se elimino.

    Raises:
        AppError: si el contacto no existe.
    """
    eliminado = await contacts_repository.eliminar(id)
    if not eliminado:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
    return True
