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
    org = p.get("organization", {}) or {}
    phones = p.get("phone_numbers", []) or []
    # Prioridad: celular (mobile) como telefono_personal. Si no hay celular,
    # el primer telefono disponible va a telefono_empresa. Nunca duplicar.
    tel_personal = next((ph["sanitized_number"] for ph in phones if ph.get("type") == "mobile"), None)
    tel_empresa = next((ph["sanitized_number"] for ph in phones), None) if not tel_personal else None
    return {
        "nombre": p.get("name", ""),
        "empresa": org.get("name", p.get("organization_name", "")),
        "cargo": p.get("title", ""),
        "email_empresarial": p.get("email"),
        "email_personal": p.get("personal_emails", [None])[0] if p.get("personal_emails") else None,
        "telefono_empresa": tel_empresa or (org.get("primary_phone", {}) or {}).get("sanitized_number"),
        "telefono_personal": tel_personal,
        "confianza": 0.9,
        "origen": "apollo",
    }


async def buscar_personas(rubro: str, ubicacion: str, cantidad: int, api_key: str) -> list[dict]:
    """
    Busca contactos en Apollo via mixed_people search.

    Args:
        rubro: titulo o rol a buscar (ej. "CEO", "Director Comercial").
        ubicacion: ubicacion geografica.
        cantidad: cantidad de resultados (max 100).
        api_key: API key de Apollo.

    Returns:
        Lista de contactos mapeados a nuestro schema.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/api/v1/mixed_people/search",
                headers=_headers(api_key),
                json={
                    "person_titles": [rubro],
                    "person_locations": [ubicacion],
                    "per_page": min(cantidad, 100),
                },
            )
        resp.raise_for_status()
        personas = resp.json().get("people", [])
        log.info("Apollo busqueda: %d resultados para '%s' en '%s'", len(personas), rubro, ubicacion)
        return [_mapear_persona(p) for p in personas]
    except httpx.HTTPStatusError as exc:
        log.error("Apollo API error %s: %s", exc.response.status_code, exc.response.text[:200])
        raise AppError("Error en busqueda Apollo", "APOLLO_SEARCH_ERROR", 502) from exc
    except Exception as exc:
        log.error("Error en busqueda Apollo: %s", exc)
        raise AppError("Error al conectar con Apollo", "APOLLO_CONNECTION_ERROR", 502) from exc


async def enriquecer_contacto(nombre: str, empresa: str, api_key: str) -> dict:
    """Enriquece un contacto individual via Apollo people/match."""
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
    """
    Enriquece multiples contactos via Apollo bulk_match.

    Fallo individual no detiene el lote — retorna datos originales con confianza=0.
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
