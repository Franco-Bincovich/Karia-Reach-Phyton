"""
Rutas de administración — solo accesibles para superadmins.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from controllers import admin_controller
from middleware.auth import get_rol_from_request, get_usuario_id_from_request
from middleware.error_handler import AppError

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_superadmin(request: Request) -> str:
    """Verifica que el usuario sea superadmin. Retorna su usuario_id."""
    if get_rol_from_request(request) != "superadmin":
        raise AppError("Acceso denegado — se requiere rol superadmin", "FORBIDDEN", 403)
    uid = get_usuario_id_from_request(request)
    if not uid:
        raise AppError("No se pudo identificar al usuario", "UNAUTHORIZED", 401)
    return uid


class EditUsuarioRequest(BaseModel):
    """Body para editar un usuario."""
    nombre: Optional[str] = None
    email: Optional[str] = None
    rol: Optional[str] = Field(None, pattern="^(user|superadmin)$")


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


@router.patch("/usuarios/{id}")
async def editar_usuario(request: Request, id: str, body: EditUsuarioRequest) -> dict:
    """Edita nombre, email o rol de un usuario."""
    _require_superadmin(request)
    return await admin_controller.editar_usuario(id, body.model_dump(exclude_none=True))


@router.delete("/usuarios/{id}")
async def eliminar_usuario(request: Request, id: str) -> dict:
    """Elimina un usuario y todos sus datos en cascada."""
    mi_id = _require_superadmin(request)
    return await admin_controller.eliminar_usuario(id, mi_id)
