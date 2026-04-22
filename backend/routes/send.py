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
from middleware.auth import get_rol_from_request, get_usuario_id_from_request
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
    uid = get_usuario_id_from_request(request)
    rol = get_rol_from_request(request)
    return await send_controller.enviar_campana(
        body.nombre, str(body.template_id),
        [str(cid) for cid in body.contact_ids],
        body.scheduled_at.isoformat() if body.scheduled_at else None,
        uid,
        rol,
    )


@router.get("/campaigns")
async def listar_campanas(request: Request) -> dict:
    """Lista todas las campanas."""
    uid = get_usuario_id_from_request(request)
    return await send_controller.listar_campanas(uid)


@router.get("/campaigns/{campaign_id}/stats")
async def estadisticas_campana(request: Request, campaign_id: UUID) -> dict:
    """Estadisticas detalladas de una campana individual."""
    uid = get_usuario_id_from_request(request)
    return await send_controller.estadisticas_campana(str(campaign_id), uid)


@router.get("/stats")
async def estadisticas_globales(request: Request) -> dict:
    """Estadisticas agregadas de todas las campanas."""
    uid = get_usuario_id_from_request(request)
    return await send_controller.estadisticas_globales(uid)


@router.get("/dashboard")
async def obtener_dashboard(request: Request) -> dict:
    """Devuelve el dashboard con totales del sistema."""
    uid = get_usuario_id_from_request(request)
    return await send_controller.obtener_dashboard(uid)
