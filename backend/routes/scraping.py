"""
Rutas de scraping web — busqueda de contactos y preferencias.

Endpoints:
  POST /api/scraping/buscar        — crawlea sitios y devuelve contactos
  GET  /api/scraping/preferencias  — devuelve preferencias del usuario
  POST /api/scraping/preferencias  — guarda preferencias del usuario
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import scraping_controller
from middleware.auth import get_usuario_id_from_request

router = APIRouter(prefix="/api/scraping", tags=["scraping"])


# --- Modelos de validacion ---

class BuscarRequest(BaseModel):
    """Lista de URLs o nombres de sitios a scrapear."""

    entradas: list[str] = Field(..., min_length=1, description="URLs o nombres de sitios")


class PreferenciasRequest(BaseModel):
    """Preferencias de extraccion de contactos por scraping."""

    extraer_emails: bool = True
    extraer_telefonos: bool = True
    extraer_autoridades: bool = True
    extraer_direcciones: bool = False
    max_paginas: int = Field(60, ge=10, le=100)
    profundidad: int = Field(3, ge=1, le=5)
    guardar_directo: bool = False


# --- Endpoints ---

@router.post("/buscar")
async def buscar(request: Request, body: BuscarRequest) -> dict:
    """Crawlea los sitios indicados y devuelve contactos extraidos."""
    uid = get_usuario_id_from_request(request)
    return await scraping_controller.buscar(body.entradas, uid)


@router.get("/preferencias")
async def get_preferencias(request: Request) -> dict:
    """Devuelve las preferencias de scraping del usuario autenticado."""
    uid = get_usuario_id_from_request(request)
    return await scraping_controller.get_preferencias(uid)


@router.post("/preferencias")
async def post_preferencias(request: Request, body: PreferenciasRequest) -> dict:
    """Guarda las preferencias de scraping del usuario autenticado."""
    uid = get_usuario_id_from_request(request)
    return await scraping_controller.post_preferencias(uid, body.model_dump())
