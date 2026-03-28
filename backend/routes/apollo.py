"""
Rutas de Apollo.io — configuracion, busqueda y enriquecimiento.

Endpoints:
  GET    /api/apollo/status
  POST   /api/apollo/config
  DELETE /api/apollo/config
  POST   /api/apollo/search
  POST   /api/apollo/enrich
"""

from typing import List

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import apollo_controller
from middleware.rate_limiter import apollo_limit

router = APIRouter(prefix="/api/apollo", tags=["apollo"])


# --- Modelos de validacion ---

class ConfigRequest(BaseModel):
    """API key de Apollo."""
    api_key: str = Field(..., min_length=10, description="API key de Apollo.io")


class SearchRequest(BaseModel):
    """Parametros de busqueda en Apollo."""
    rubro: str = Field(..., min_length=2, description="Titulo o rol a buscar")
    ubicacion: str = Field(..., min_length=2, description="Zona geografica")
    cantidad: int = Field(10, ge=1, le=100)


class ContactoEnrich(BaseModel):
    """Contacto minimo para enriquecimiento."""
    nombre: str = Field(..., min_length=1)
    empresa: str = Field(..., min_length=1)


class EnrichRequest(BaseModel):
    """Lista de contactos a enriquecer."""
    contactos: List[ContactoEnrich] = Field(..., min_length=1)


# --- Endpoints ---

@router.get("/status")
async def status() -> dict:
    """Verifica si Apollo esta configurado."""
    return await apollo_controller.status()


@router.post("/config")
async def guardar_config(body: ConfigRequest) -> dict:
    """Guarda la API key de Apollo."""
    return await apollo_controller.guardar_config(body.api_key)


@router.delete("/config")
async def eliminar_config() -> dict:
    """Elimina la API key de Apollo."""
    return await apollo_controller.eliminar_config()


@router.post("/search")
@apollo_limit
async def buscar(request: Request, body: SearchRequest) -> dict:
    """Busca contactos en Apollo."""
    return await apollo_controller.buscar(body.rubro, body.ubicacion, body.cantidad)


@router.post("/enrich")
@apollo_limit
async def enriquecer(request: Request, body: EnrichRequest) -> dict:
    """Enriquece contactos con datos de Apollo."""
    contactos = [c.model_dump() for c in body.contactos]
    return await apollo_controller.enriquecer(contactos)
