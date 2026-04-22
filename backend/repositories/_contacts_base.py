"""Helpers y constantes compartidos por los repositorios de contactos."""
from __future__ import annotations

import json
import uuid

_CAMPOS_STR_NO_NULL = (
    "email_empresarial", "email_personal", "telefono_empresa", "telefono_personal",
    "linkedin_url", "instagram_username", "facebook_url", "whatsapp",
    "website", "direccion", "ciudad", "pais",
)

_CAMPOS_MERGE = (
    "cargo", "email_empresarial", "email_personal", "telefono_empresa", "telefono_personal",
    "linkedin_url", "instagram_username", "facebook_url", "whatsapp",
    "website", "direccion", "ciudad", "pais", "confianza",
)

_COLUMNAS_CONTACTS = frozenset({
    "nombre", "empresa", "email_empresarial", "email_personal", "cargo", "confianza",
    "origen", "telefono_empresa", "telefono_personal", "linkedin_url", "rubro",
    "instagram_username", "facebook_url", "whatsapp", "twitter_url", "tiktok_username",
    "website", "direccion", "ciudad", "pais", "usuario_id",
    "enrichment_sources", "last_enriched_at",
})


def _normalizar_contacto(contacto: dict) -> dict:
    """Prepara un contacto antes de insertar: vacios a None, confianza normalizada."""
    for campo in _CAMPOS_STR_NO_NULL:
        contacto[campo] = contacto.get(campo) or None
    val = contacto.get("confianza")
    if val is not None:
        val = float(val)
        if val > 1.0:
            val = val / 100.0
        contacto["confianza"] = max(0.0, min(1.0, val))
    contacto.pop("apollo_id", None)
    return contacto


def _confianza_to_db(val: float) -> int:
    """Convierte confianza float 0-1 a smallint 0-100 para Postgres."""
    return int(round(val * 100))


def _build_insert_parts(datos: dict) -> tuple[list[str], list[str], list]:
    """Arma columnas, placeholders y valores para un INSERT dinamico con columnas allowlisted."""
    datos_filtrados = {k: v for k, v in datos.items() if k in _COLUMNAS_CONTACTS}
    cols, placeholders, vals = [], [], []
    for i, (col, val) in enumerate(datos_filtrados.items(), 1):
        cols.append(col)
        if col == "origen":
            placeholders.append(f"${i}::contact_source")
        else:
            placeholders.append(f"${i}")
        if col == "enrichment_sources" and val is not None:
            val = json.dumps(val)
        elif col == "usuario_id" and isinstance(val, str):
            val = uuid.UUID(val)
        vals.append(val)
    return cols, placeholders, vals
