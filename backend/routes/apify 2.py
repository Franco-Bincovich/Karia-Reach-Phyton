"""
Rutas de Apify — enriquecimiento de contactos y busqueda en Google Maps.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import apify_controller

router = APIRouter(prefix="/api/apify", tags=["apify"])


# --- Request models ---

class EnriquecerRequest(BaseModel):
    """Body para enriquecer un contacto existente."""
    contacto_id: str = Field(..., min_length=1)


class BuscarRequest(BaseModel):
    """Body para buscar negocios en Google Maps."""
    rubro: str = Field(..., min_length=2)
    ubicacion: str = Field(..., min_length=2)
    pais: str = Field("Argentina", min_length=2)
    cantidad: int = Field(10, ge=1, le=20)


# --- Endpoints ---

@router.post("/enriquecer-contacto")
async def enriquecer_contacto(request: Request, body: EnriquecerRequest) -> dict:
    """Enriquece un contacto con el pipeline de 8 Actors de Apify."""
    return await apify_controller.enriquecer_contacto(body.contacto_id)


@router.post("/buscar")
async def buscar(request: Request, body: BuscarRequest) -> dict:
    """Busca negocios en Google Maps via Apify (sin guardar)."""
    return await apify_controller.buscar(body.rubro, body.ubicacion, body.pais, body.cantidad)


@router.get("/status")
async def status(request: Request) -> dict:
    """Verifica si Apify esta configurado (APIFY_API_KEY en .env)."""
    return await apify_controller.status()
