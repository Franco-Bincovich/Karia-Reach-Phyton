"""
Rutas de envio — validacion con Pydantic, delegacion a controller.

Endpoints:
  POST /api/send/campaign
  GET  /api/send/campaigns
  GET  /api/send/campaigns/{campaign_id}/stats
  GET  /api/send/stats
  GET  /api/send/dashboard
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import send_controller
from middleware.rate_limiter import send_limit

router = APIRouter(prefix="/api/send", tags=["send"])


# --- Modelos de validacion ---

class CampaignRequest(BaseModel):
    """Parametros para crear y enviar una campana."""
    nombre: str = Field(..., min_length=3, description="Nombre de la campana")
    template_id: UUID = Field(..., description="UUID del template")
    contact_ids: List[UUID] = Field(..., min_length=1, description="UUIDs de contactos")
    scheduled_at: Optional[datetime] = Field(None, description="Fecha programada (ISO 8601)")


# --- Endpoints ---

@router.post("/campaign")
@send_limit
async def enviar_campana(request: Request, body: CampaignRequest) -> dict:
    """Crea y ejecuta una campana de email."""
    return await send_controller.enviar_campana(
        body.nombre, str(body.template_id),
        [str(cid) for cid in body.contact_ids],
        body.scheduled_at.isoformat() if body.scheduled_at else None,
    )


@router.get("/campaigns")
async def listar_campanas() -> dict:
    """Lista todas las campanas."""
    return await send_controller.listar_campanas()


@router.get("/campaigns/{campaign_id}/stats")
async def estadisticas_campana(campaign_id: UUID) -> dict:
    """Estadisticas detalladas de una campana individual."""
    return await send_controller.estadisticas_campana(str(campaign_id))


@router.get("/stats")
async def estadisticas_globales() -> dict:
    """Estadisticas agregadas de todas las campanas."""
    return await send_controller.estadisticas_globales()


@router.get("/dashboard")
async def obtener_dashboard() -> dict:
    """Devuelve el dashboard con totales del sistema."""
    return await send_controller.obtener_dashboard()
