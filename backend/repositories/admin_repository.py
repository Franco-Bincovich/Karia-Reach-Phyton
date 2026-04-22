"""Fachada de admin — re-exporta crud y stats para compatibilidad con imports existentes."""
from .admin_crud_repository import (
    buscar_por_email, insertar_usuario, editar_usuario, eliminar_usuario_cascade,
)
from .admin_stats_repository import (
    listar_usuarios, obtener_usuario_por_id, obtener_contactos_usuario,
    obtener_campanas_usuario, obtener_contadores_usuario, obtener_integraciones_usuario,
    obtener_metodos_habilitados,
)

__all__ = [
    "buscar_por_email", "insertar_usuario", "editar_usuario", "eliminar_usuario_cascade",
    "listar_usuarios", "obtener_usuario_por_id", "obtener_contactos_usuario",
    "obtener_campanas_usuario", "obtener_contadores_usuario", "obtener_integraciones_usuario",
    "obtener_metodos_habilitados",
]
