"""
Repositorio de templates — unico punto de acceso a la tabla `templates`.

Campos: id, nombre, asunto, cuerpo, tono, objetivo, created_at, updated_at.
"""

from __future__ import annotations

from integrations.supabase_client import supabase
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_TABLE = "templates"


async def listar() -> list[dict]:
    """Devuelve todos los templates ordenados por fecha de creacion desc."""
    try:
        resp = supabase.table(_TABLE).select("*").order("created_at", desc=True).execute()
        return resp.data
    except Exception as exc:
        log.error("Error listando templates: %s", exc)
        raise AppError("Error al listar templates", "DB_TEMPLATES_LIST", 500) from exc


async def crear(template: dict) -> dict:
    """
    Inserta un template nuevo.

    Args:
        template: dict con nombre, asunto, cuerpo, tono, objetivo.

    Returns:
        Dict del template creado con id y timestamps.
    """
    try:
        resp = supabase.table(_TABLE).insert(template).execute()
        log.info("Template creado: %s", template.get("nombre"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando template: %s", exc)
        raise AppError("Error al crear template", "DB_TEMPLATES_CREATE", 500) from exc


async def eliminar(id: str) -> bool:
    """
    Elimina un template por id.

    Args:
        id: UUID del template.

    Returns:
        True si se elimino, False si no existia.
    """
    try:
        resp = supabase.table(_TABLE).delete().eq("id", id).execute()
        eliminado = len(resp.data) > 0
        if eliminado:
            log.info("Template eliminado: %s", id)
        return eliminado
    except Exception as exc:
        log.error("Error eliminando template %s: %s", id, exc)
        raise AppError("Error al eliminar template", "DB_TEMPLATES_DELETE", 500) from exc
