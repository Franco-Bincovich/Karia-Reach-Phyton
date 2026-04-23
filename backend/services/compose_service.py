"""
Servicio de composicion — logica de negocio para generacion
de emails con IA y gestion de templates.
"""

from __future__ import annotations

from integrations import claude_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import templates_repository
from utils.helpers import require_uid

log = get_logger(__name__)


async def generar_variantes(
    descripcion: str, tono: str, objetivo: str,
    variantes: int = 3, instruccion_adicional: str | None = None,
) -> list[dict]:
    """
    Genera variantes de email via IA.

    Args:
        descripcion: producto o servicio a promocionar.
        tono: tono del email.
        objetivo: objetivo del email.
        variantes: cantidad de variantes (1-5).
        instruccion_adicional: instruccion libre del usuario (opcional).

    Returns:
        Lista de dicts con 'asunto' y 'cuerpo'.
    """
    resultados = await claude_client.generar_emails(
        descripcion, tono, objetivo, variantes, instruccion_adicional,
    )
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


async def formatear_manual(asunto: str, cuerpo_natural: str) -> dict:
    """
    Formatea texto natural a HTML de email via IA.

    Args:
        asunto: asunto del email.
        cuerpo_natural: texto en lenguaje natural.

    Returns:
        Dict con 'asunto' y 'cuerpo_html'.
    """
    resultado = await claude_client.formatear_manual(asunto, cuerpo_natural)
    log.info("Formateado email manual: %s", asunto[:50])
    return resultado


async def listar_templates(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los templates guardados."""
    require_uid(usuario_id)
    return await templates_repository.listar(usuario_id)


async def guardar_template(template: dict, usuario_id: str = None) -> dict:
    """
    Guarda un template nuevo.

    Args:
        template: dict con nombre, asunto, cuerpo, tono, objetivo.

    Returns:
        Template creado con id y timestamps.
    """
    require_uid(usuario_id)
    template["usuario_id"] = usuario_id
    return await templates_repository.crear(template)


async def eliminar_template(id: str, usuario_id: str = None) -> bool:
    uid = require_uid(usuario_id)
    eliminado = await templates_repository.eliminar(id, uid)
    if not eliminado:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)
    return True
