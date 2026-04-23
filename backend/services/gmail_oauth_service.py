"""Fachada del servicio OAuth de Gmail — re-exporta flujo y gestión de credenciales."""
from .gmail_oauth_flow import generar_url_autorizacion, validar_state, procesar_callback
from .gmail_credentials_service import obtener_credenciales_validas

__all__ = [
    "generar_url_autorizacion",
    "validar_state",
    "procesar_callback",
    "obtener_credenciales_validas",
]
