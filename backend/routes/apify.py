"""
Rutas de Apify — enriquecimiento de contactos y busqueda en Google Maps.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import apify_controller
from middleware.auth import get_usuario_id_from_request

router = APIRouter(prefix="/api/apify", tags=["apify"])


# --- Request models ---

class ConfigRequest(BaseModel):
    """Body para guardar API key de Apify."""
    api_key: str = Field(..., min_length=10)


class EnriquecerRequest(BaseModel):
    """Body para enriquecer un contacto existente."""
    contacto_id: str = Field(..., min_length=1)


class BuscarRequest(BaseModel):
    """Body para buscar negocios en Google Maps."""
    rubro: str = Field(..., min_length=2)
    ubicacion: str = Field(..., min_length=2)
    pais: str = Field("Argentina", min_length=2)
    cantidad: int = Field(10, ge=1, le=20)


class InstagramBuscarRequest(BaseModel):
    """Body para buscar contactos desde perfiles de competencia en Instagram."""
    handles: list[str] = Field(
        ..., min_length=1, max_length=8,
        description="Hasta 8 usernames de Instagram sin @",
    )
    max_por_perfil: int = Field(500, ge=10, le=2000)


# --- Endpoints ---

@router.post("/enriquecer-contacto")
async def enriquecer_contacto(request: Request, body: EnriquecerRequest) -> dict:
    """Enriquece un contacto con el pipeline de 8 Actors de Apify."""
    uid = get_usuario_id_from_request(request)
    return await apify_controller.enriquecer_contacto(body.contacto_id, uid)


@router.post("/buscar")
async def buscar(request: Request, body: BuscarRequest) -> dict:
    """Busca negocios en Google Maps via Apify (sin guardar)."""
    return await apify_controller.buscar(body.rubro, body.ubicacion, body.pais, body.cantidad)


@router.get("/status")
async def status(request: Request) -> dict:
    """Verifica si Apify esta configurado (DB o .env)."""
    uid = get_usuario_id_from_request(request)
    return await apify_controller.status(uid)


@router.post("/config")
async def guardar_config(request: Request, body: ConfigRequest) -> dict:
    """Guarda la API key de Apify."""
    uid = get_usuario_id_from_request(request)
    return await apify_controller.guardar_config(body.api_key, uid)


@router.delete("/config")
async def eliminar_config(request: Request) -> dict:
    """Elimina la API key de Apify."""
    uid = get_usuario_id_from_request(request)
    return await apify_controller.eliminar_config(uid)


@router.post("/instagram/buscar")
async def buscar_instagram(request: Request, body: InstagramBuscarRequest) -> dict:
    """Busca contactos desde seguidores/likers de perfiles de competencia en Instagram."""
    uid = get_usuario_id_from_request(request)
    return await apify_controller.buscar_instagram(body.handles, body.max_por_perfil, uid)
