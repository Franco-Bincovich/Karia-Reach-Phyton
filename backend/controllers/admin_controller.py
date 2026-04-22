"""
Controller de administración — thin layer que delega a admin_service.
"""

from __future__ import annotations

from services import admin_service


async def crear_usuario(email: str, password: str, nombre: str, rol: str) -> dict:
    """Crea un usuario nuevo."""
    usuario = await admin_service.crear_usuario(email, password, nombre, rol)
    return {"data": usuario}


async def listar_usuarios() -> dict:
    """Lista todos los usuarios con estadísticas."""
    usuarios = await admin_service.listar_usuarios()
    return {"data": usuarios, "total": len(usuarios)}


async def obtener_usuario(id: str) -> dict:
    """Obtiene detalle de un usuario."""
    usuario = await admin_service.obtener_usuario(id)
    return {"data": usuario}


async def obtener_metodos(id: str) -> dict:
    """Retorna los métodos de búsqueda habilitados para un usuario."""
    return {"data": await admin_service.obtener_metodos(id)}


async def editar_usuario(id: str, datos: dict) -> dict:
    """Edita un usuario."""
    usuario = await admin_service.editar_usuario(id, datos)
    return {"data": usuario}


async def eliminar_usuario(id: str, mi_id: str) -> dict:
    """Elimina un usuario y sus datos."""
    await admin_service.eliminar_usuario(id, mi_id)
    return {"deleted": True}
