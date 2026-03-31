"""
Repositorio de campanas programadas — acceso a `campanas_programadas`.

Funciones: crear, listar, obtener, obtener_sin_usuario,
           listar_programadas, actualizar_estado, cancelar.
"""

from __future__ import annotations

import asyncio

from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)
_TABLE = "campanas_programadas"


async def crear(usuario_id: str, datos: dict) -> dict:
    """Inserta una campana programada nueva."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .insert({**datos, "usuario_id": usuario_id}).execute()
        ))
        log.info("Campana programada creada: %s", datos.get("nombre"))
        return resp.data[0]
    except Exception as exc:
        log.error("Error creando campana programada: %s", exc)
        raise AppError("Error al crear campana programada", "DB_CAMPANA_PROG_CREATE", 500) from exc


async def listar(usuario_id: str) -> list[dict]:
    """Devuelve las campanas programadas del usuario, desc por creacion."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("usuario_id", usuario_id)
            .order("created_at", desc=True).execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando campanas programadas: %s", exc)
        raise AppError("Error al listar campanas programadas", "DB_CAMPANA_PROG_LIST", 500) from exc


async def obtener(campana_id: str, usuario_id: str) -> dict:
    """Obtiene una campana por ID validando que pertenezca al usuario."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("id", campana_id).eq("usuario_id", usuario_id).limit(1).execute()
        ))
        if not resp.data:
            raise AppError("Campana programada no encontrada", "CAMPANA_PROG_NOT_FOUND", 404)
        return resp.data[0]
    except AppError:
        raise
    except Exception as exc:
        log.error("Error obteniendo campana programada %s: %s", campana_id, exc)
        raise AppError("Error al obtener campana programada", "DB_CAMPANA_PROG_GET", 500) from exc


async def obtener_sin_usuario(campana_id: str) -> dict:
    """Obtiene una campana por ID sin filtro de usuario (uso interno del scheduler)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("id", campana_id).limit(1).execute()
        ))
        if not resp.data:
            raise AppError("Campana programada no encontrada", "CAMPANA_PROG_NOT_FOUND", 404)
        return resp.data[0]
    except AppError:
        raise
    except Exception as exc:
        raise AppError("Error al obtener campana programada", "DB_CAMPANA_PROG_GET", 500) from exc


async def listar_programadas() -> list[dict]:
    """Lista todas las campanas con estado 'programada' (para el scheduler al arrancar)."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).select("*")
            .eq("estado", "programada").execute()
        ))
        return resp.data
    except Exception as exc:
        log.error("Error listando campanas activas: %s", exc)
        raise AppError("Error al listar campanas activas", "DB_CAMPANA_PROG_ACTIVAS", 500) from exc


async def actualizar_estado(
    campana_id: str, estado: str, ultima_ejecucion: str | None = None
) -> None:
    """Actualiza estado y opcionalmente ultima_ejecucion de una campana."""
    try:
        datos: dict = {"estado": estado}
        if ultima_ejecucion:
            datos["ultima_ejecucion"] = ultima_ejecucion
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE).update(datos).eq("id", campana_id).execute()
        ))
    except Exception as exc:
        log.error("Error actualizando estado campana %s: %s", campana_id, exc)
        raise AppError("Error al actualizar estado", "DB_CAMPANA_PROG_UPDATE", 500) from exc


async def cancelar(campana_id: str, usuario_id: str) -> None:
    """Cancela una campana programada verificando propiedad y estado."""
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: (
            get_supabase_client().table(_TABLE)
            .update({"estado": "cancelada"})
            .eq("id", campana_id).eq("usuario_id", usuario_id)
            .eq("estado", "programada").execute()
        ))
        if not resp.data:
            raise AppError(
                "Campana no encontrada o ya no esta programada",
                "CAMPANA_PROG_NOT_FOUND", 404,
            )
    except AppError:
        raise
    except Exception as exc:
        log.error("Error cancelando campana %s: %s", campana_id, exc)
        raise AppError("Error al cancelar campana", "DB_CAMPANA_PROG_CANCEL", 500) from exc
