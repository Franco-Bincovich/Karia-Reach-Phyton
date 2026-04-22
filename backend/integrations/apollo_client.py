"""
Cliente async de Apollo.io API. Busqueda de contactos y enriquecimiento
de datos empresariales via la API REST de Apollo.
"""

from __future__ import annotations

import httpx

from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_BASE = "https://api.apollo.io"
_TIMEOUT = 30
# Rate limits de Apollo API (plan Free): 5 req/min para search,
# 100 req/hora para enrich. Plan pago: limites mayores segun tier.
# Ver: https://docs.apollo.io/reference/rate-limits


def _headers(api_key: str) -> dict:
    """Headers de autenticacion para Apollo API."""
    return {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}


def _mapear_persona(p: dict) -> dict:
    """Mapea un resultado de Apollo a nuestro schema de contacto."""
    first = p.get("first_name", "") or ""
    last = p.get("last_name", "") or ""
    nombre = f"{first} {last}".strip() or p.get("name", "") or "Sin nombre"
    phones = p.get("phone_numbers", []) or []
    tel_empresa = phones[0].get("raw_number") if phones else None
    return {
        "apollo_id": p.get("id"),
        "nombre": nombre,
        "empresa": (p.get("organization") or {}).get("name", ""),
        "cargo": p.get("title", ""),
        "email_empresarial": p.get("email"),
        "email_personal": None,
        "telefono_empresa": tel_empresa,
        "telefono_personal": None,
        "linkedin_url": p.get("linkedin_url"),
        "confianza": 0.9,
        "origen": "apollo",
    }


async def _enriquecer_post_busqueda(
    contactos: list[dict], api_key: str,
) -> list[dict]:
    """
    Enriquece contactos con bulk_match despues de la busqueda.

    Usa apollo_id de cada contacto mapeado para armar el request y
    mergear los resultados. Maximo 5 por llamada.

    Args:
        contactos: lista de contactos ya mapeados (con apollo_id).
        api_key: API key de Apollo.

    Returns:
        Lista de contactos con datos enriquecidos donde fue posible.
    """
    # Seleccionar los primeros 5 contactos que tengan apollo_id
    enriquecibles = [c for c in contactos if c.get("apollo_id")][:5]
    if not enriquecibles:
        return contactos
    details = [{"id": c["apollo_id"]} for c in enriquecibles]
    try:
        log.info("Iniciando enriquecimiento de %d contactos", len(details))
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/api/v1/people/bulk_match",
                headers=_headers(api_key),
                json={
                    "reveal_personal_emails": True,
                    "details": details,
                },
            )
            log.info("bulk_match response status: %d", resp.status_code)
            if resp.status_code != 200:
                log.error("bulk_match error status %d", resp.status_code)
            resp.raise_for_status()
            matches = resp.json().get("matches", [])
    except Exception as exc:
        log.warning("Error en enriquecimiento post-busqueda: %s", exc)
        return contactos
    # Indexar contactos por apollo_id para mergear resultados
    por_id = {c.get("apollo_id"): c for c in contactos}
    enriquecidos = 0
    for match in matches:
        if not match:
            continue
        person = match if "id" in match else match.get("person", {})
        if not person:
            continue
        original = por_id.get(person.get("id"))
        if not original:
            continue
        actualizado = False
        nombre = person.get("name")
        if nombre:
            original["nombre"] = nombre
            actualizado = True
        linkedin = person.get("linkedin_url")
        if linkedin and not original.get("linkedin_url"):
            original["linkedin_url"] = linkedin
            actualizado = True
        email = person.get("email")
        if email and not original.get("email_empresarial"):
            original["email_empresarial"] = email
        personal_emails = person.get("personal_emails") or []
        if personal_emails and not original.get("email_personal"):
            original["email_personal"] = personal_emails[0]
        if actualizado:
            enriquecidos += 1
    log.info("Enriquecimiento post-busqueda: %d/%d contactos", enriquecidos, len(details))
    return contactos


_TAMANO_RANGES: dict = {
    "micro": ["1,10"],
    "pequena": ["11,50"],
    "mediana": ["51,200", "201,500"],
    "grande": ["501,1000", "1001,5000"],
    "enterprise": ["5001,10000", "10001,"],
}


async def buscar_personas(
    rubro: str,
    ubicacion: str,
    cantidad: int,
    api_key: str,
    cargo: str | None = None,
    tamano_empresa: str | None = None,
    solo_email_verificado: bool = False,
) -> list[dict]:
    """Busca contactos en Apollo via mixed_people search con enriquecimiento posterior.

    Args:
        rubro: título o rol a buscar (ej. "CEO", "Director Comercial").
        ubicacion: ubicación geográfica (informativa; la búsqueda filtra por Argentina).
        cantidad: cantidad de resultados deseados (max 100).
        api_key: API key de Apollo del usuario.
        cargo: título adicional para ampliar la búsqueda (opcional).
        tamano_empresa: filtro por tamaño — 'micro' | 'pequena' | 'mediana' | 'grande' | 'enterprise' (opcional).
        solo_email_verificado: si True filtra solo contactos con email verificado por Apollo.

    Returns:
        Lista de dicts mapeados a nuestro schema de contacto, enriquecidos con bulk_match.

    Raises:
        AppError: APOLLO_SEARCH_ERROR (502) si Apollo responde con HTTP error.
        AppError: APOLLO_CONNECTION_ERROR (502) si no se puede conectar con Apollo.
    """
    titulos = [rubro]
    if cargo and cargo.strip() and cargo.strip().lower() != rubro.strip().lower():
        titulos.append(cargo.strip())
    payload: dict = {
        "person_titles": titulos,
        "person_locations": ["Argentina"],
        "organization_locations": ["Argentina"],
        "per_page": min(cantidad, 100),
    }
    if tamano_empresa and tamano_empresa.lower() in _TAMANO_RANGES:
        payload["organization_num_employees_ranges"] = _TAMANO_RANGES[tamano_empresa.lower()]
    if solo_email_verificado:
        payload["contact_email_status_cd"] = ["verified"]
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/api/v1/mixed_people/api_search",
                headers=_headers(api_key),
                json=payload,
            )
            resp.raise_for_status()
            personas = resp.json().get("people", [])
            log.info("Apollo busqueda: %d resultados para '%s' en '%s'", len(personas), rubro, ubicacion)
            contactos = [_mapear_persona(p) for p in personas]
            for c in contactos:
                c["rubro"] = rubro
            # Enriquecer los primeros 5 contactos con bulk_match para obtener email/telefono
            contactos = await _enriquecer_post_busqueda(contactos, api_key)
            return contactos
    except httpx.HTTPStatusError as exc:
        log.error("Apollo API error status %s", exc.response.status_code)
        raise AppError("Error en busqueda Apollo", "APOLLO_SEARCH_ERROR", 502) from exc
    except Exception as exc:
        log.error("Error en busqueda Apollo: %s", exc)
        raise AppError("Error al conectar con Apollo", "APOLLO_CONNECTION_ERROR", 502) from exc


async def enriquecer_contacto(nombre: str, empresa: str, api_key: str) -> dict:
    """Enriquece un contacto individual via Apollo people/match.

    Args:
        nombre: nombre completo del contacto.
        empresa: nombre de la empresa del contacto.
        api_key: API key de Apollo del usuario.

    Returns:
        Dict con datos del contacto mapeados a nuestro schema.
        Si Apollo no encuentra match, devuelve dict mínimo con confianza=0.0.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/api/v1/people/match",
                headers=_headers(api_key),
                json={"name": nombre, "organization_name": empresa},
            )
        resp.raise_for_status()
        persona = resp.json().get("person")
        if not persona:
            return {"nombre": nombre, "empresa": empresa, "confianza": 0.0, "origen": "apollo"}
        return _mapear_persona(persona)
    except Exception as exc:
        log.warning("Error enriqueciendo %s (%s): %s", nombre, empresa, exc)
        return {"nombre": nombre, "empresa": empresa, "confianza": 0.0, "origen": "apollo"}


async def enriquecer_bulk(contactos: list[dict], api_key: str) -> list[dict]:
    """Enriquece múltiples contactos via Apollo bulk_match.

    Args:
        contactos: lista de dicts con al menos nombre y empresa.
        api_key: API key de Apollo del usuario.

    Returns:
        Lista de dicts enriquecidos en el mismo orden que la entrada.
        Contactos sin match en Apollo se devuelven con confianza=0.0.
    """
    try:
        details = [{"name": c.get("nombre", ""), "organization_name": c.get("empresa", "")}
                    for c in contactos]
        async with httpx.AsyncClient(timeout=_TIMEOUT * 2) as client:
            resp = await client.post(
                f"{_BASE}/api/v1/people/bulk_match",
                headers=_headers(api_key),
                json={"details": details},
            )
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
        resultado = []
        for i, match in enumerate(matches):
            if match and match.get("person"):
                resultado.append(_mapear_persona(match["person"]))
            else:
                orig = contactos[i] if i < len(contactos) else {}
                resultado.append({**orig, "confianza": 0.0, "origen": "apollo"})
        enriquecidos = sum(1 for r in resultado if r.get("confianza", 0) > 0)
        log.info("Apollo bulk enrich: %d/%d enriquecidos", enriquecidos, len(contactos))
        return resultado
    except Exception as exc:
        log.error("Error en bulk enrich Apollo: %s", exc)
        return [{**c, "confianza": 0.0, "origen": "apollo"} for c in contactos]
