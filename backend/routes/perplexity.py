"""
Rutas de Perplexity — configuracion y busqueda de contactos.

Endpoints:
  GET    /api/perplexity/status
  POST   /api/perplexity/config
  DELETE /api/perplexity/config
  POST   /api/perplexity/search
"""

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import perplexity_controller
from middleware.auth import get_usuario_id_from_request
from middleware.rate_limiter import search_limit

router = APIRouter(prefix="/api/perplexity", tags=["perplexity"])


# --- Modelos de validacion ---

class ConfigRequest(BaseModel):
    """API key de Perplexity."""
    api_key: str = Field(..., min_length=10, description="API key de Perplexity")


class SearchRequest(BaseModel):
    """Parametros de busqueda en Perplexity."""
    rubro: str = Field("", description="Industria o sector")
    ubicacion: str = Field("", description="Zona geografica")
    cantidad: int = Field(10, ge=1, le=50)
    prompt_personalizado: Optional[str] = Field(None, description="Instruccion libre")


# --- Endpoints ---

@router.get("/status")
async def status(request: Request) -> dict:
    """Verifica si Perplexity esta configurado."""
    uid = get_usuario_id_from_request(request)
    return await perplexity_controller.status(uid)


@router.post("/config")
async def guardar_config(request: Request, body: ConfigRequest) -> dict:
    """Guarda la API key de Perplexity."""
    uid = get_usuario_id_from_request(request)
    return await perplexity_controller.guardar_config(body.api_key, uid)


@router.delete("/config")
async def eliminar_config(request: Request) -> dict:
    """Elimina la API key de Perplexity."""
    uid = get_usuario_id_from_request(request)
    return await perplexity_controller.eliminar_config(uid)


@router.post("/search")
@search_limit
async def buscar(request: Request, body: SearchRequest) -> dict:
    """Busca contactos con Perplexity."""
    uid = get_usuario_id_from_request(request)
    return await perplexity_controller.buscar(
        body.rubro, body.ubicacion, body.cantidad, body.prompt_personalizado, uid,
    )
