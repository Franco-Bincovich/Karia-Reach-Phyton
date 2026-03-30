"""
Cliente singleton de Supabase.

Inicializa una unica instancia del cliente supabase-py
usando las credenciales de settings. Lazy singleton: se crea en el primer uso.
"""

from typing import Optional

from supabase import Client, create_client

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
settings = get_settings()


def _crear_cliente() -> Client:
    """
    Crea e inicializa el cliente de Supabase.

    Raises:
        AppError: si faltan credenciales o la conexion falla.

    Returns:
        Instancia autenticada del cliente Supabase.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise AppError(
            message="Faltan credenciales de Supabase (URL o SERVICE_KEY)",
            code="SUPABASE_CONFIG_ERROR",
            status_code=500,
        )

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        log.info("Supabase cliente creado para %s", settings.SUPABASE_URL)
        return client
    except Exception as exc:
        log.error("Error creando cliente Supabase: %s", exc)
        raise AppError(
            message="No se pudo conectar a Supabase",
            code="SUPABASE_CONNECTION_ERROR",
            status_code=500,
        ) from exc


_cliente: Optional[Client] = None


def get_supabase_client() -> Client:
    """Devuelve el cliente Supabase, creandolo en el primer uso (lazy singleton)."""
    global _cliente
    if _cliente is None:
        _cliente = _crear_cliente()
    return _cliente
