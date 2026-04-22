"""Fachada de campanas — re-exporta crud y stats para compatibilidad con imports existentes."""
from .campaigns_crud_repository import (
    listar, contar, sumar_enviados, crear, actualizar_metricas,
)
from .campaigns_stats_repository import (
    crear_resultado, listar_resultados,
    obtener_estadisticas_campana, obtener_estadisticas_globales,
)

__all__ = [
    "listar", "contar", "sumar_enviados", "crear", "actualizar_metricas",
    "crear_resultado", "listar_resultados",
    "obtener_estadisticas_campana", "obtener_estadisticas_globales",
]
