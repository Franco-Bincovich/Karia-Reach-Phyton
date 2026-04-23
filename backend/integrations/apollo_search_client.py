"""
Funciones de búsqueda de Apollo.io — buscar_personas con enriquecimiento bulk.
Exporta también helpers compartidos (_BASE, _TIMEOUT, _headers, _mapear_persona).
"""
from __future__ import annotations

import httpx

from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_BASE = "https://api.apollo.io"
_TIMEOUT = 30


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


async def _enriquecer_post_busqueda(contactos: list[dict], api_key: str) -> list[dict]:
    """Enriquece contactos con bulk_match después de la búsqueda (max 5)."""
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
                json={"reveal_personal_emails": True, "details": details},
            )
            log.info("bulk_match response status: %d", resp.status_code)
            if resp.status_code != 200:
                log.error("bulk_match error status %d", resp.status_code)
            resp.raise_for_status()
            matches = resp.json().get("matches", [])
    except Exception as exc:
        log.warning("Error en enriquecimiento post-busqueda: %s", exc)
        return contactos
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
        rubro: título o rol a buscar.
        ubicacion: ubicación geográfica (informativa).
        cantidad: cantidad de resultados deseados (max 100).
        api_key: API key de Apollo del usuario.
        cargo: título adicional para ampliar la búsqueda (opcional).
        tamano_empresa: filtro por tamaño — 'micro' | 'pequena' | 'mediana' | 'grande' | 'enterprise'.
        solo_email_verificado: si True filtra solo contactos con email verificado.

    Raises:
        AppError: APOLLO_SEARCH_ERROR (502) si Apollo responde con HTTP error.
        AppError: APOLLO_CONNECTION_ERROR (502) si no se puede conectar con Apollo.
    """
    titulos = [rubro]
    if cargo and cargo.strip() and cargo.strip().lower() != rubro.strip().lower():
        titulos.append(cargo.strip())
    payload: dict = {
        "person_titles": titulos,
        "person_locations": [ubicacion] if ubicacion else ["Argentina"],
        "organization_locations": [ubicacion] if ubicacion else ["Argentina"],
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
            return await _enriquecer_post_busqueda(contactos, api_key)
    except httpx.HTTPStatusError as exc:
        log.error("Apollo API error status %s", exc.response.status_code)
        raise AppError("Error en busqueda Apollo", "APOLLO_SEARCH_ERROR", 502) from exc
    except Exception as exc:
        log.error("Error en busqueda Apollo: %s", exc)
        raise AppError("Error al conectar con Apollo", "APOLLO_CONNECTION_ERROR", 502) from exc
