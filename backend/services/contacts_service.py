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


def _require_uid(usuario_id: str | None) -> str:
    """Valida que usuario_id esté presente."""
    if not usuario_id:
        raise AppError("Token inválido o expirado", "AUTH_REQUIRED", 401)
    return usuario_id


async def filtrar_duplicados(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """Filtra contactos cuyos emails ya existen en la base de datos. Reutilizable por otros services."""
    emails_existentes = await contacts_repository.listar_emails(usuario_id)
    if not emails_existentes:
        return contactos
    nuevos = []
    for c in contactos:
        emp = (c.get("email_empresarial") or "").lower()
        per = (c.get("email_personal") or "").lower()
        # Si no tiene ningún email, no podemos saber si es duplicado
        if not emp and not per:
            nuevos.append(c)
            continue
        if (emp and emp in emails_existentes) or (per and per in emails_existentes):
            continue
        nuevos.append(c)
    filtrados = len(contactos) - len(nuevos)
    if filtrados:
        log.info("Filtrados %d contactos duplicados de %d", filtrados, len(contactos))
    return nuevos


async def buscar_con_ia(
    rubro: str, ubicacion: str, cantidad: int = 10,
    prompt_personalizado: str | None = None,
    usuario_id: str = None,
) -> list[dict]:
    """
    Busca contactos via IA y les asigna IDs temporales.

    Args:
        rubro: industria o sector a buscar.
        ubicacion: zona geografica.
        cantidad: contactos a buscar (default 10).
        prompt_personalizado: filtro adicional del usuario (opcional).

    Returns:
        Lista de contactos con id temporal ai-{timestamp}-{index}.
    """
    _require_uid(usuario_id)
    resultados = await claude_client.buscar_contactos(rubro, ubicacion, cantidad, prompt_personalizado)
    resultados = await filtrar_duplicados(resultados, usuario_id)
    # IDs temporales para que el frontend pueda referenciar cada contacto
    # antes de persistirlo. Se limpian en guardar_seleccion() con c.pop("id")
    # cuando el usuario confirma la seleccion y se insertan en DB con UUID real.
    ts = int(time.time())
    for i, contacto in enumerate(resultados):
        contacto["id"] = f"ai-{ts}-{i}"
        contacto["origen"] = "ai"
    log.info("Busqueda IA: %d contactos encontrados para %s en %s", len(resultados), rubro, ubicacion)
    return resultados


async def guardar_seleccion(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """Guarda una seleccion de contactos en la base de datos."""
    _require_uid(usuario_id)
    if len(contactos) > _MAX_SELECCION:
        raise AppError(
            f"Maximo {_MAX_SELECCION} contactos por seleccion",
            "CONTACTS_LIMIT_EXCEEDED", 400,
        )
    # Limpiar IDs temporales antes de persistir
    for c in contactos:
        c.pop("id", None)
        c.setdefault("origen", "ai")
        if usuario_id:
            c["usuario_id"] = usuario_id
    return await contacts_repository.crear_bulk(contactos)


async def agregar_manual(contacto: dict, usuario_id: str = None) -> dict:
    """
    Agrega un contacto ingresado manualmente.

    Args:
        contacto: dict con datos del contacto.

    Returns:
        Contacto creado con id y timestamps.
    """
    _require_uid(usuario_id)
    contacto["confianza"] = 1.0
    contacto["origen"] = "manual"
    if usuario_id:
        contacto["usuario_id"] = usuario_id
    return await contacts_repository.crear(contacto)


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los contactos."""
    _require_uid(usuario_id)
    return await contacts_repository.listar(usuario_id)


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
