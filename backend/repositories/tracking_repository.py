"""
Repositorio de tracking — acceso a campaign_results para registrar aperturas.

Separado del campaigns_repository para mantener la ruta de tracking
desacoplada del flujo principal de campanas.
"""

from __future__ import annotations

from datetime import datetime, timezone

from integrations.supabase_client import supabase
from logger import get_logger

log = get_logger(__name__)


async def registrar_apertura(campaign_id: str, contact_id: str) -> bool:
    """
    Actualiza opened_at en campaign_results para el par campaign/contact.

    Si ya tenia opened_at, lo sobreescribe con el timestamp mas reciente.

    Returns:
        True si se actualizo al menos un registro.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    try:
        resp = (
            supabase.table("campaign_results")
            .update({"opened_at": ahora})
            .eq("campaign_id", campaign_id)
            .eq("contact_id", contact_id)
            .execute()
        )
        actualizado = len(resp.data) > 0
        if actualizado:
            log.info("Apertura: campaign=%s contact=%s at=%s", campaign_id, contact_id, ahora)
        return actualizado
    except Exception as exc:
        log.error("Error registrando apertura: %s", exc)
        return False
