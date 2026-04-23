"""
Servicio de enriquecimiento de contactos — logica multi-metodo.
"""
from __future__ import annotations

from integrations import claude_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import contacts_repository

log = get_logger(__name__)


async def _enriquecer_con_claude(nombre: str, empresa: str) -> dict:
    """Busca datos del contacto via Claude AI.

    Args:
        nombre: nombre del contacto.
        empresa: empresa del contacto.

    Returns:
        Dict con los nuevos campos (vacío si no hay resultados).

    Raises:
        AppError: CLAUDE_API_ERROR (502) si la llamada a Claude falla.
    """
    resultados = await claude_client.buscar_contactos(
        empresa, "", 1,
        f"Buscar datos completos de contacto: {nombre}, empresa: {empresa}",
    )
    return resultados[0] if resultados else {}


async def _enriquecer_con_apollo(nombre: str, empresa: str, usuario_id: str) -> dict:
    """Busca datos del contacto via Apollo.io.

    Args:
        nombre: nombre del contacto.
        empresa: empresa del contacto.
        usuario_id: UUID del usuario para buscar su API key de Apollo.

    Returns:
        Dict con los nuevos campos encontrados.

    Raises:
        AppError: APOLLO_NOT_CONFIGURED (400) si no hay API key configurada.
    """
    from repositories import integrations_repository
    from integrations import apollo_client as _apollo_client

    key = await integrations_repository.obtener_api_key("apollo", usuario_id)
    if not key:
        raise AppError(
            "Apollo no configurado. Guarda tu API key primero.", "APOLLO_NOT_CONFIGURED", 400
        )
    return await _apollo_client.enriquecer_contacto(nombre, empresa, key)


async def _enriquecer_con_perplexity(nombre: str, empresa: str, usuario_id: str) -> dict:
    """Busca datos del contacto via Perplexity.

    Args:
        nombre: nombre del contacto.
        empresa: empresa del contacto.
        usuario_id: UUID del usuario para buscar su API key de Perplexity.

    Returns:
        Dict con los nuevos campos (vacío si no hay resultados).

    Raises:
        AppError: PERPLEXITY_NOT_CONFIGURED (400) si no hay API key configurada.
    """
    from repositories import integrations_repository
    from integrations import perplexity_client as _perplexity_client

    key = await integrations_repository.obtener_api_key("perplexity", usuario_id)
    if not key:
        raise AppError(
            "Perplexity no configurado. Guarda tu API key primero.",
            "PERPLEXITY_NOT_CONFIGURED", 400,
        )
    resultados = await _perplexity_client.buscar_contactos(
        empresa, "", 1,
        f"Buscar datos completos de contacto: {nombre}, empresa: {empresa}",
        key,
    )
    return resultados[0] if resultados else {}


async def enriquecer_contacto(contact_id: str, metodo: str, usuario_id: str) -> dict:
    """Enriquece un contacto existente via el metodo especificado.

    Args:
        contact_id: UUID del contacto a enriquecer.
        metodo: estrategia — 'claude' | 'perplexity' | 'apollo'.
        usuario_id: UUID del propietario del contacto.

    Returns:
        Contacto actualizado con los nuevos campos mergeados.

    Raises:
        AppError: AUTH_REQUIRED (401) si usuario_id es None.
        AppError: CONTACT_NOT_FOUND (404) si el contacto no pertenece al usuario.
        AppError: APOLLO_NOT_CONFIGURED (400) si metodo='apollo' sin API key.
        AppError: PERPLEXITY_NOT_CONFIGURED (400) si metodo='perplexity' sin API key.
        AppError: CLAUDE_API_ERROR (502) si la llamada a Claude falla.
    """
    if not usuario_id:
        raise AppError("Token inválido o expirado", "AUTH_REQUIRED", 401)

    contactos = await contacts_repository.listar_por_ids([contact_id], usuario_id)
    if not contactos:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
    contacto = contactos[0]
    nombre = contacto.get("nombre", "")
    empresa = contacto.get("empresa", "")

    if metodo == "apollo":
        nuevos_datos = await _enriquecer_con_apollo(nombre, empresa, usuario_id)
    elif metodo == "perplexity":
        nuevos_datos = await _enriquecer_con_perplexity(nombre, empresa, usuario_id)
    else:
        nuevos_datos = await _enriquecer_con_claude(nombre, empresa)

    actualizado = await contacts_repository.merge_contact(contact_id, nuevos_datos, metodo, usuario_id)
    fields_added = [
        k for k in contacts_repository._CAMPOS_MERGE
        if nuevos_datos.get(k) and not contacto.get(k)
    ]
    await contacts_repository.save_enrichment_log(contact_id, usuario_id, metodo, fields_added)
    log.info("enriquecer_contacto %s via %s: %d campos nuevos", contact_id, metodo, len(fields_added))
    return actualizado
