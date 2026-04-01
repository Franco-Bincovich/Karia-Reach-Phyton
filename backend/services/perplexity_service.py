"""
Servicio de Perplexity — logica de negocio para busqueda
de contactos via Perplexity API con modelo sonar.
"""

from __future__ import annotations

from integrations import perplexity_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import contacts_repository, integrations_repository

log = get_logger(__name__)

_SERVICIO = "perplexity"


async def esta_configurado(usuario_id: str = None) -> bool:
    """Verifica si hay una API key de Perplexity activa."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    return key is not None


async def guardar_key(api_key: str, usuario_id: str = None) -> dict:
    """Guarda la API key de Perplexity."""
    return await integrations_repository.guardar_api_key(_SERVICIO, api_key, usuario_id)


async def eliminar_key(usuario_id: str = None) -> bool:
    """Elimina (desactiva) la API key de Perplexity."""
    eliminado = await integrations_repository.eliminar_api_key(_SERVICIO, usuario_id)
    if not eliminado:
        raise AppError("No hay API key de Perplexity configurada", "PERPLEXITY_NOT_CONFIGURED", 404)
    return True


async def _obtener_key(usuario_id: str = None) -> str:
    """Obtiene la API key o lanza error si no esta configurada."""
    key = await integrations_repository.obtener_api_key(_SERVICIO, usuario_id)
    if not key:
        raise AppError(
            "Perplexity no esta configurado. Guarda tu API key primero.",
            "PERPLEXITY_NOT_CONFIGURED", 400,
        )
    return key


async def buscar_contactos(
    rubro: str, ubicacion: str, cantidad: int = 10,
    prompt_personalizado: str | None = None, usuario_id: str = None,
) -> list[dict]:
    """
    Busca contactos via Perplexity API.

    Args:
        rubro: titulo o rol a buscar.
        ubicacion: zona geografica.
        cantidad: cantidad de resultados.
        prompt_personalizado: instruccion libre (opcional).

    Returns:
        Lista de contactos mapeados, filtrados por duplicados.
    """
    key = await _obtener_key(usuario_id)
    resultados = await perplexity_client.buscar_contactos(
        rubro, ubicacion, cantidad, prompt_personalizado, key,
    )
    # Filtrar contactos que ya existen por email
    emails_existentes = await contacts_repository.listar_emails(usuario_id)
    if emails_existentes:
        nuevos = []
        for c in resultados:
            emp = (c.get("email_empresarial") or "").lower()
            per = (c.get("email_personal") or "").lower()
            if not emp and not per:
                nuevos.append(c)
                continue
            if (emp and emp in emails_existentes) or (per and per in emails_existentes):
                continue
            nuevos.append(c)
        filtrados = len(resultados) - len(nuevos)
        if filtrados:
            log.info("Perplexity: filtrados %d contactos duplicados de %d", filtrados, len(resultados))
        resultados = nuevos
    return resultados
