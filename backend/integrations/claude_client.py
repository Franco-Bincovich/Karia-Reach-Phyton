"""Fachada del cliente Claude — re-exporta contacts y compose para compatibilidad con imports existentes."""
from .claude_contacts_client import buscar_contactos
from .claude_compose_client import generar_emails, componer_desde_contactos, formatear_manual

__all__ = [
    "buscar_contactos",
    "generar_emails",
    "componer_desde_contactos",
    "formatear_manual",
]
