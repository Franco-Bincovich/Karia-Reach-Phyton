"""
Rutas de administración — solo accesibles para superadmins.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from controllers import admin_controller
from middleware.auth import get_rol_from_request, get_usuario_id_from_request
from middleware.error_handler import AppError
from utils.db import METODOS_BUSQUEDA_VALIDOS

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_superadmin(request: Request) -> str:
    """Verifica que el usuario sea superadmin. Retorna su usuario_id."""
    if get_rol_from_request(request) != "superadmin":
        raise AppError("Acceso denegado — se requiere rol superadmin", "FORBIDDEN", 403)
    return get_usuario_id_from_request(request)


class CrearUsuarioRequest(BaseModel):
    """Body para crear un usuario nuevo."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    nombre: str = Field(..., min_length=2)
    rol: str = Field("user", pattern="^(user|superadmin)$")


class EditUsuarioRequest(BaseModel):
    """Body para editar un usuario."""
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = Field(None, pattern="^(user|superadmin)$")
    metodos_habilitados: Optional[List[str]] = None


@router.post("/usuarios")
async def crear_usuario(request: Request, body: CrearUsuarioRequest) -> dict:
    """Crea un usuario nuevo. Solo superadmin."""
    _require_superadmin(request)
    return await admin_controller.crear_usuario(body.email, body.password, body.nombre, body.rol)


@router.get("/usuarios")
async def listar_usuarios(request: Request) -> dict:
    """Lista todos los usuarios con estadísticas."""
    _require_superadmin(request)
    return await admin_controller.listar_usuarios()


@router.get("/usuarios/{id}")
async def obtener_usuario(request: Request, id: str) -> dict:
    """Detalle de un usuario con contactos y campañas."""
    _require_superadmin(request)
    return await admin_controller.obtener_usuario(id)


@router.get("/usuarios/{id}/metodos")
async def obtener_metodos(request: Request, id: str) -> dict:
    """Retorna los métodos de búsqueda habilitados para un usuario. Solo superadmin."""
    _require_superadmin(request)
    return await admin_controller.obtener_metodos(id)


@router.patch("/usuarios/{id}")
async def editar_usuario(request: Request, id: str, body: EditUsuarioRequest) -> dict:
    """Edita nombre, email, rol y/o metodos_habilitados de un usuario."""
    _require_superadmin(request)
    datos = body.model_dump(exclude_none=True)
    if "metodos_habilitados" in datos:
        invalidos = set(datos["metodos_habilitados"]) - METODOS_BUSQUEDA_VALIDOS
        if invalidos:
            raise AppError(f"Métodos inválidos: {invalidos}", "INVALID_METODOS", 400)
    return await admin_controller.editar_usuario(id, datos)


@router.delete("/usuarios/{id}")
async def eliminar_usuario(request: Request, id: str) -> dict:
    """Elimina un usuario y todos sus datos en cascada."""
    mi_id = _require_superadmin(request)
    return await admin_controller.eliminar_usuario(id, mi_id)
