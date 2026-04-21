"""
Repositorio de tracking — acceso a campaign_results para registrar aperturas.

Separado del campaigns_repository para mantener la ruta de tracking
desacoplada del flujo principal de campanas.
"""

from __future__ import annotations

import uuid

from integrations.postgres_client import get_pool
from logger import get_logger

log = get_logger(__name__)


async def registrar_apertura(campaign_id: str, contact_id: str) -> bool:
    """
    Actualiza opened_at en campaign_results para el par campaign/contact.

    Si ya tenia opened_at, lo sobreescribe con el timestamp mas reciente.

    Returns:
        True si se actualizo al menos un registro.
    """
    try:
        async with get_pool().acquire() as conn:
            result = await conn.execute(
                "UPDATE campaign_results SET opened_at = NOW() "
                "WHERE campaign_id = $1 AND contact_id = $2",
                uuid.UUID(campaign_id),
                uuid.UUID(contact_id),
            )
        actualizado = result.startswith("UPDATE ") and int(result.split()[1]) > 0
        if actualizado:
            log.info("Apertura: campaign=%s contact=%s", campaign_id, contact_id)
        return actualizado
    except Exception as exc:
        log.error("Error registrando apertura: %s", exc)
        return False
