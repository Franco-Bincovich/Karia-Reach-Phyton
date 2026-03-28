"""
Rutas de respuestas — lectura, sincronizacion y respuesta a emails recibidos.

Endpoints:
  GET  /api/replies/{campaign_id}
  POST /api/replies/{campaign_id}/sync
  POST /api/replies/{reply_id}/respond
  PATCH /api/replies/{reply_id}/read
"""

from uuid import UUID

import bleach
from fastapi import APIRouter
from pydantic import BaseModel, Field

from controllers import replies_controller

router = APIRouter(prefix="/api/replies", tags=["replies"])


class RespondRequest(BaseModel):
    """Cuerpo para responder a un email."""
    cuerpo: str = Field(..., min_length=1, max_length=10000, description="Cuerpo HTML de la respuesta")


@router.get("/{campaign_id}")
async def listar_respuestas(campaign_id: UUID) -> dict:
    """Lista todas las respuestas de una campana."""
    return await replies_controller.listar_respuestas(str(campaign_id))


@router.post("/{campaign_id}/sync")
async def sincronizar(campaign_id: UUID) -> dict:
    """Sincroniza respuestas nuevas desde Gmail para una campana."""
    return await replies_controller.sincronizar(str(campaign_id))


@router.post("/{reply_id}/respond")
async def responder(reply_id: UUID, body: RespondRequest) -> dict:
    """Responde a una respuesta recibida. Sanitiza HTML antes de enviar."""
    cuerpo_limpio = bleach.clean(body.cuerpo, tags=[], strip=True)
    return await replies_controller.responder(str(reply_id), cuerpo_limpio)


@router.patch("/{reply_id}/read")
async def marcar_leida(reply_id: UUID) -> dict:
    """Marca una respuesta como leida."""
    return await replies_controller.marcar_leida(str(reply_id))
