"""Fachada de Apollo — re-exporta funciones de búsqueda y enriquecimiento."""
from .apollo_search_client import buscar_personas
from .apollo_enrich_client import enriquecer_contacto, enriquecer_bulk

__all__ = ["buscar_personas", "enriquecer_contacto", "enriquecer_bulk"]
