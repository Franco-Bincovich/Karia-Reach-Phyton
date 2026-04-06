"""
Rutas de campanas programadas — validacion Pydantic, JWT requerido.

Endpoints:
  POST   /api/campanas-programadas       → crear campana programada
  GET    /api/campanas-programadas       → listar campanas del usuario
  DELETE /api/campanas-programadas/{id} → cancelar campana
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from controllers import campanas_programadas_controller
from middleware.auth import get_usuario_id_from_request

router = APIRouter(prefix="/api/campanas-programadas", tags=["campanas-programadas"])


def get_usuario_id(request: Request) -> str:
    """Extrae usuario_id del JWT usando la función centralizada."""
    uid = get_usuario_id_from_request(request)
    if not uid:
        from middleware.error_handler import AppError
        raise AppError("Se requiere autenticacion JWT", "JWT_REQUIRED", 401)
    return uid


# --- Modelos de validacion ---

class CrearCampanaRequest(BaseModel):
    """Parametros para crear una campana programada."""
    nombre: str = Field(..., min_length=3)
    template_id: UUID
    contact_ids: List[UUID] = Field(..., min_length=1)
    bloque_id: Optional[UUID] = None
    tipo: str = Field(..., pattern="^(unica|recurrente)$")
    fecha_envio: Optional[str] = None   # ISO 8601 para tipo 'unica'
    dias_semana: Optional[List[int]] = None  # [0..6] para tipo 'recurrente'
    hora_envio: str = Field(..., pattern="^([01]\\d|2[0-3]):[0-5]\\d$")


# --- Endpoints ---

@router.post("")
async def crear(
    body: CrearCampanaRequest,
    usuario_id: str = Depends(get_usuario_id),
) -> dict:
    """Crea y programa una campana de email."""
    return await campanas_programadas_controller.crear(usuario_id, body.model_dump())


@router.get("")
async def listar(usuario_id: str = Depends(get_usuario_id)) -> dict:
    """Lista las campanas programadas del usuario autenticado."""
    return await campanas_programadas_controller.listar(usuario_id)


@router.delete("/{campana_id}")
async def cancelar(
    campana_id: UUID,
    usuario_id: str = Depends(get_usuario_id),
) -> dict:
    """Cancela una campana programada del usuario."""
    return await campanas_programadas_controller.cancelar(str(campana_id), usuario_id)
