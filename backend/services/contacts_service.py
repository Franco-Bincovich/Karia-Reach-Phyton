"""
Servicio de contactos — busqueda, creacion y gestion de contactos comerciales.
"""
from __future__ import annotations

import time

from integrations import claude_client
from logger import get_logger
from middleware.error_handler import AppError
from repositories import contacts_repository
from utils.helpers import require_uid

log = get_logger(__name__)

_MAX_SELECCION = 50


async def filtrar_duplicados(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """Filtra contactos cuyos emails ya existen en la DB; incluye los que no tienen email."""
    emails_existentes = await contacts_repository.listar_emails(usuario_id)
    if not emails_existentes:
        return contactos
    nuevos = []
    for c in contactos:
        emp = (c.get("email_empresarial") or "").lower()
        per = (c.get("email_personal") or "").lower()
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
    """Anota ya_existe y contact_id_existente en cada contacto sin filtrar."""
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
    """Busca contactos via Claude AI; asigna IDs temporales y anota existencia."""
    require_uid(usuario_id)
    resultados = await claude_client.buscar_contactos(rubro, ubicacion, cantidad, prompt_personalizado)
    # IDs temporales para que el frontend referencie cada contacto antes de persistirlo
    ts = int(time.time())
    for i, contacto in enumerate(resultados):
        contacto["id"] = f"ai-{ts}-{i}"
        contacto["origen"] = "ai"
    resultados = await anotar_existencia(resultados, usuario_id)
    log.info("Busqueda IA: %d contactos encontrados para %s en %s", len(resultados), rubro, ubicacion)
    return resultados


async def guardar_seleccion(contactos: list[dict], usuario_id: str = None) -> list[dict]:
    """Guarda contactos seleccionados; hace merge si el email ya existe en la DB."""
    require_uid(usuario_id)
    if len(contactos) > _MAX_SELECCION:
        raise AppError(
            f"Maximo {_MAX_SELECCION} contactos por seleccion",
            "CONTACTS_LIMIT_EXCEEDED", 400,
        )
    guardados = []
    nuevos = []
    for c in contactos:
        c.pop("ya_existe", None)
        c.pop("contact_id_existente", None)
        c.pop("id", None)
        c.setdefault("origen", "ai")
        if usuario_id:
            c["usuario_id"] = usuario_id
        email = c.get("email_empresarial") or c.get("email_personal")
        existente = None
        if email:
            try:
                existente = await contacts_repository.buscar_por_email(email)
            except Exception as exc:
                log.warning("No se pudo verificar email existente %s: %s", email, exc)
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
    """Agrega un contacto manual con confianza 1.0 y origen 'manual'."""
    require_uid(usuario_id)
    contacto["confianza"] = 1.0
    contacto["origen"] = "manual"
    if usuario_id:
        contacto["usuario_id"] = usuario_id
    return await contacts_repository.crear(contacto)


async def listar(usuario_id: str = None) -> list[dict]:
    """Devuelve todos los contactos del usuario ordenados por created_at DESC."""
    require_uid(usuario_id)
    return await contacts_repository.listar(usuario_id)


async def enriquecer_contacto(contact_id: str, metodo: str, usuario_id: str) -> dict:
    """Delega el enriquecimiento multi-metodo a enrichment_service."""
    from services import enrichment_service
    return await enrichment_service.enriquecer_contacto(contact_id, metodo, usuario_id)


async def eliminar(id: str, usuario_id: str = None) -> bool:
    """Elimina un contacto; 404 si no existe o no pertenece al usuario."""
    eliminado = await contacts_repository.eliminar(id, usuario_id)
    if not eliminado:
        raise AppError("Contacto no encontrado", "CONTACT_NOT_FOUND", 404)
    return True
