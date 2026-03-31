"""
Controller de campanas programadas — adapta HTTP a services.
Sin logica de negocio, solo traduce request/response.
"""

from __future__ import annotations

from services import campanas_programadas_service


async def crear(usuario_id: str, datos: dict) -> dict:
    """Crea una campana programada y agrega el job al scheduler."""
    from scheduler import agregar_campana  # import local para evitar ciclos
    campana = await campanas_programadas_service.crear(usuario_id, datos)
    agregar_campana(campana)
    return {"data": campana}


async def listar(usuario_id: str) -> dict:
    """Lista las campanas programadas del usuario."""
    campanas = await campanas_programadas_service.listar(usuario_id)
    return {"data": campanas, "total": len(campanas)}


async def cancelar(campana_id: str, usuario_id: str) -> dict:
    """Cancela una campana programada y remueve el job del scheduler."""
    from scheduler import cancelar_campana  # import local para evitar ciclos
    await campanas_programadas_service.cancelar(campana_id, usuario_id)
    cancelar_campana(campana_id)
    return {"cancelada": True}
