"""Fachada de Gmail — re-exporta funciones de envío y lectura."""
from .gmail_send_client import enviar_email, enviar_bulk
from .gmail_reader_client import leer_respuestas

__all__ = ["enviar_email", "enviar_bulk", "leer_respuestas"]
