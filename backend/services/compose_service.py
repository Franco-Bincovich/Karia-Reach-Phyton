"""
Servicio de composicion — logica de negocio para generacion
de emails con IA y gestion de templates.
"""

from __future__ import annotations

from integrations import claude_client
from logger import get_logger
from repositories import templates_repository

log = get_logger(__name__)


async def generar_variantes(
    descripcion: str, tono: str, objetivo: str, variantes: int = 3
) -> list[dict]:
    """
    Genera variantes de email via IA.

    Args:
        descripcion: producto o servicio a promocionar.
        tono: tono del email.
        objetivo: objetivo del email.
        variantes: cantidad de variantes (1-5).

    Returns:
        Lista de dicts con 'asunto' y 'cuerpo'.
    """
    resultados = await claude_client.generar_emails(descripcion, tono, objetivo, variantes)
    log.info("Generadas %d variantes de email", len(resultados))
    return resultados


async def componer_desde_contactos(
    contactos: list[dict], producto: str, modo: str = "formal"
) -> list[dict]:
    """
    Compone emails personalizados para una lista de contactos.

    Args:
        contactos: lista de contactos con nombre, empresa, cargo.
        producto: producto o servicio a ofrecer.
        modo: estilo de escritura.

    Returns:
        Lista de dicts con destinatario, asunto, cuerpo.
    """
    resultados = await claude_client.componer_desde_contactos(contactos, producto, modo)
    log.info("Compuestos %d emails personalizados", len(resultados))
    return resultados


async def listar_templates() -> list[dict]:
    """Devuelve todos los templates guardados."""
    return await templates_repository.listar()


async def guardar_template(template: dict) -> dict:
    """
    Guarda un template nuevo.

    Args:
        template: dict con nombre, asunto, cuerpo, tono, objetivo.

    Returns:
        Template creado con id y timestamps.
    """
    return await templates_repository.crear(template)


async def eliminar_template(id: str) -> bool:
    """
    Elimina un template por id.

    Args:
        id: UUID del template.

    Returns:
        True si se elimino.
    """
    from middleware.error_handler import AppError

    eliminado = await templates_repository.eliminar(id)
    if not eliminado:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)
    return True
