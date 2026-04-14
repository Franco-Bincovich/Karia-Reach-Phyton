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


async def anotar_existencia(contactos: list[dict], usuario_id: str) -> list[dict]:
    """
    Marca cada contacto con ya_existe y contact_id_existente comparando contra la DB.
    No filtra — solo anota. El frontend usa esto para mostrar el badge 'Ya en KarIA'.
    """
    email_a_id = await contacts_repository.listar_emails_con_ids(usuario_id)
    if not email_a_id:
        for c in contactos:
            c["ya_existe"] = False
            c["contact_id_existente"] = None
        return contactos
    for c in contactos:
        emp = (c.get("email_empresarial") or "").lower()
        per = (c.get("email_personal") or "").lower()
        cid = email_a_id.get(emp) or email_a_id.get(per)
        c["ya_existe"] = bool(cid)
        c["contact_id_existente"] = cid
    return contactos


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
    # IDs temporales para que el frontend pueda referenciar cada contacto
    # antes de persistirlo. Se limpian en guardar_seleccion() cuando se confirma.
    ts = int(time.time())
    for i, contacto in enumerate(resultados):
        contacto["id"] = f"ai-{ts}-{i}"
        contacto["origen"] = "ai"
    resultados = await anotar_existencia(resultados, usuario_id)
    log.info("Busqueda IA: %d contactos encontrados para %s en %s", len(resultados), rubro, ubicacion)
    return resultados


async def guardar_seleccion(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """
    Guarda una seleccion de contactos. Si el contacto ya existe (por email),
    hace merge de los campos vacios en lugar de crear un duplicado.
    """
    _require_uid(usuario_id)
    if len(contactos) > _MAX_SELECCION:
        raise AppError(
            f"Maximo {_MAX_SELECCION} contactos por seleccion",
            "CONTACTS_LIMIT_EXCEEDED", 400,
        )
    guardados = []
    nuevos = []
    for c in contactos:
        # Limpiar campos de anotacion del frontend
        c.pop("ya_existe", None)
        c.pop("contact_id_existente", None)
        c.pop("id", None)
        c.setdefault("origen", "ai")
        if usuario_id:
            c["usuario_id"] = usuario_id
        # Verificar si ya existe por email
        email = c.get("email_empresarial") or c.get("email_personal")
        existente = None
        if email:
            try:
                existente = await contacts_repository.buscar_por_email(email)
            except Exception:
                pass
        if existente and existente.get("usuario_id") == usuario_id:
            origen = c.get("origen", "ai")
            actualizado = await contacts_repository.merge_contact(existente["id"], c, origen, usuario_id)
            guardados.append(actualizado)
        else:
            nuevos.append(c)
    if nuevos:
        insertados = await contacts_repository.crear_bulk(nuevos)
        guardados.extend(insertados)
    return guardados


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


async def enriquecer_contacto(contact_id: str, metodo: str, usuario_id: str) -> dict:
    """
    Enriquece un contacto existente via el metodo especificado.

    Args:
        contact_id: UUID del contacto a enriquecer.
        metodo: 'claude' | 'perplexity' | 'apollo'.
        usuario_id: ID del propietario.

    Returns:
        Contacto actualizado con los nuevos campos.
    """
    _require_uid(usuario_id)
    # Importes locales para evitar circular imports (apollo_service importa contacts_service)
    from repositories import integrations_repository
    from integrations import perplexity_client as _perplexity_client
    from integrations import apollo_client as _apollo_client

    contactos = await contacts_repository.listar_por_ids([contact_id], usuario_id)
    if not contactos:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
    contacto = contactos[0]
    nombre = contacto.get("nombre", "")
    empresa = contacto.get("empresa", "")

    nuevos_datos: dict = {}
    if metodo == "apollo":
        key = await integrations_repository.obtener_api_key("apollo", usuario_id)
        if not key:
            raise AppError("Apollo no configurado. Guarda tu API key primero.", "APOLLO_NOT_CONFIGURED", 400)
        mapeado = await _apollo_client.enriquecer_contacto(nombre, empresa, key)
        nuevos_datos = mapeado
    elif metodo == "perplexity":
        key = await integrations_repository.obtener_api_key("perplexity", usuario_id)
        if not key:
            raise AppError("Perplexity no configurado. Guarda tu API key primero.", "PERPLEXITY_NOT_CONFIGURED", 400)
        resultados = await _perplexity_client.buscar_contactos(
            empresa, "", 1,
            f"Buscar datos completos de contacto: {nombre}, empresa: {empresa}",
            key,
        )
        nuevos_datos = resultados[0] if resultados else {}
    else:  # claude (default)
        resultados = await claude_client.buscar_contactos(
            empresa, "", 1,
            f"Buscar datos completos de contacto: {nombre}, empresa: {empresa}",
        )
        nuevos_datos = resultados[0] if resultados else {}

    actualizado = await contacts_repository.merge_contact(contact_id, nuevos_datos, metodo, usuario_id)
    fields_added = [
        k for k in contacts_repository._CAMPOS_MERGE
        if nuevos_datos.get(k) and not contacto.get(k)
    ]
    await contacts_repository.save_enrichment_log(contact_id, usuario_id, metodo, fields_added)
    log.info("enriquecer_contacto %s via %s: %d campos nuevos", contact_id, metodo, len(fields_added))
    return actualizado


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
