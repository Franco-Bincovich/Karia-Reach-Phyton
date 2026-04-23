"""
Servicio Apify — logica de enriquecimiento y busqueda por Maps.
"""
from __future__ import annotations

from logger import get_logger
from middleware.error_handler import AppError
from repositories import apify_repository
from services import apify_enriquecimiento_service
from utils.helpers import require_uid

log = get_logger(__name__)

_CAMPOS_VALIDOS = frozenset({
    "nombre", "empresa", "cargo", "email_empresarial", "email_personal",
    "telefono_empresa", "telefono_personal", "linkedin_url", "confianza",
    "instagram_username", "facebook_url", "whatsapp", "twitter_url",
    "tiktok_username", "website", "direccion", "ciudad", "pais",
})


async def enriquecer_contacto(contacto_id: str, usuario_id: str = None) -> dict:
    """
    Enriquece un contacto existente con el pipeline de Apify.

    Raises:
        AppError: CONTACT_NOT_FOUND (404) si el contacto no existe o no pertenece al usuario.
    """
    require_uid(usuario_id)
    contacto = await apify_repository.obtener_contacto(contacto_id, usuario_id)

    datos = await apify_enriquecimiento_service.enriquecer_contacto(contacto)
    if not datos:
        return {"data": contacto, "enriquecido": False}

    # Solo campos validos que no sobreescriban datos existentes
    update_data = {
        k: v for k, v in datos.items()
        if k in _CAMPOS_VALIDOS and v and not contacto.get(k)
    }

    # Normalizar confianza float 0-1 → int 0-100 (schema smallint)
    if "confianza" in update_data:
        val = float(update_data["confianza"])
        normalized = max(0.0, min(1.0, val if val <= 1.0 else val / 100.0))
        update_data["confianza"] = int(round(normalized * 100))

    # Remover emails que ya pertenecen a otro contacto
    for email_field in ("email_empresarial", "email_personal"):
        email_val = update_data.get(email_field)
        if email_val:
            try:
                if await apify_repository.verificar_email_duplicado(email_field, email_val, contacto_id):
                    del update_data[email_field]
                    log.warning("Email %s ya existe en otro contacto, no se actualiza", email_val)
            except Exception as exc:
                log.error("Error verificando email duplicado %s: %s", email_field, exc)
                update_data.pop(email_field, None)

    if not update_data:
        return {"data": contacto, "enriquecido": False}

    update_data["origen"] = "apify"
    actualizado = await apify_repository.actualizar_contacto(contacto_id, update_data)
    log.info("Contacto %s enriquecido con %d campos", contacto_id, len(update_data))
    return {"data": actualizado, "enriquecido": True}


async def buscar(rubro: str, ubicacion: str, pais: str, cantidad: int) -> dict:
    """
    Busca negocios en Google Maps via Apify.

    Args:
        rubro: tipo de negocio.
        ubicacion: ciudad o zona.
        pais: pais de la busqueda.
        cantidad: max resultados.

    Returns:
        Dict con 'data' (lista de contactos) y 'total'.
    """
    contactos = await apify_enriquecimiento_service.buscar_por_maps(rubro, ubicacion, pais, cantidad)
    return {"data": contactos, "total": len(contactos)}
