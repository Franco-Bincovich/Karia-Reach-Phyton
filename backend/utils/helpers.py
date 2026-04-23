"""
Utilidades compartidas entre capas de la aplicación.
"""
from middleware.error_handler import AppError


def require_uid(usuario_id: str | None) -> str:
    """Valida que usuario_id no sea None y lo retorna.

    Raises:
        AppError(UNAUTHORIZED, 401): Si usuario_id es None.
    """
    if not usuario_id:
        raise AppError("No autorizado", "UNAUTHORIZED", 401)
    return usuario_id
