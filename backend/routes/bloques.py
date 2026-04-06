"""
Rutas de bloques — validacion con Pydantic, delegacion a controller.

Endpoints:
  GET    /api/bloques
  POST   /api/bloques
  PUT    /api/bloques/{bloque_id}
  DELETE /api/bloques/{bloque_id}
  POST   /api/bloques/{bloque_id}/contactos
  GET    /api/bloques/{bloque_id}/contactos
  DELETE /api/bloques/{bloque_id}/contactos/{contacto_id}
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import bloques_controller
from middleware.auth import get_usuario_id_from_request

router = APIRouter(prefix="/api/bloques", tags=["bloques"])


# --- Modelos de validacion ---

class CrearBloqueRequest(BaseModel):
    """Datos para crear un bloque."""
    nombre: str = Field(..., min_length=2, description="Nombre del bloque")


class AgregarContactosRequest(BaseModel):
    """IDs de contactos a agregar al bloque."""
    contacto_ids: List[str] = Field(..., min_length=1, max_length=500)


# --- Endpoints ---

@router.get("")
async def listar(request: Request) -> dict:
    """Lista todos los bloques del usuario."""
    uid = get_usuario_id_from_request(request)
    return await bloques_controller.listar(uid)


@router.post("")
async def crear(request: Request, body: CrearBloqueRequest) -> dict:
    """Crea un bloque nuevo."""
    uid = get_usuario_id_from_request(request)
    return await bloques_controller.crear(body.nombre, uid)


@router.put("/{bloque_id}")
async def actualizar(bloque_id: UUID, body: CrearBloqueRequest) -> dict:
    """Actualiza el nombre de un bloque."""
    return await bloques_controller.actualizar(str(bloque_id), body.nombre)


@router.delete("/{bloque_id}")
async def eliminar(bloque_id: UUID) -> dict:
    """Elimina un bloque por UUID."""
    return await bloques_controller.eliminar(str(bloque_id))


@router.post("/{bloque_id}/contactos")
async def agregar_contactos(bloque_id: UUID, body: AgregarContactosRequest) -> dict:
    """Agrega contactos a un bloque."""
    return await bloques_controller.agregar_contactos(str(bloque_id), body.contacto_ids)


@router.get("/{bloque_id}/contactos")
async def obtener_contactos(bloque_id: UUID) -> dict:
    """Devuelve los contactos de un bloque."""
    return await bloques_controller.obtener_contactos(str(bloque_id))


@router.delete("/{bloque_id}/contactos/{contacto_id}")
async def eliminar_contacto(bloque_id: UUID, contacto_id: UUID) -> dict:
    """Elimina un contacto de un bloque."""
    return await bloques_controller.eliminar_contacto(str(bloque_id), str(contacto_id))
