"""
Utilidades de seguridad — funciones criptograficas reutilizables.

Separado de routes y services para evitar imports circulares.
"""

import hashlib
import hmac

from config.settings import get_settings

settings = get_settings()


def generar_token_tracking(campaign_id: str, contact_id: str) -> str:
    """
    Genera token HMAC-SHA256 para validar una apertura de email legitima.

    Args:
        campaign_id: UUID de la campana.
        contact_id: UUID del contacto.

    Returns:
        Hex digest del HMAC firmado con SECRET_KEY.
    """
    msg = f"{campaign_id}:{contact_id}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()
