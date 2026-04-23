"""
Funciones de enriquecimiento de Apollo.io — individual y bulk.
"""
from __future__ import annotations

import httpx

from logger import get_logger
from .apollo_search_client import _BASE, _TIMEOUT, _headers, _mapear_persona

log = get_logger(__name__)


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
