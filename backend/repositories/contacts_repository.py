"""Fachada de contactos — re-exporta crud y search para compatibilidad con imports existentes."""
from ._contacts_base import _CAMPOS_MERGE, _COLUMNAS_CONTACTS
from .contacts_crud_repository import (
    listar_emails, listar, contar, listar_por_ids,
    crear, crear_bulk, eliminar, listar_emails_con_ids,
)
from .contacts_search_repository import (
    buscar_por_email, find_similar, merge_contact, save_enrichment_log,
)

__all__ = [
    "_CAMPOS_MERGE", "_COLUMNAS_CONTACTS",
    "listar_emails", "listar", "contar", "listar_por_ids",
    "crear", "crear_bulk", "eliminar", "listar_emails_con_ids",
    "buscar_por_email", "find_similar", "merge_contact", "save_enrichment_log",
]
