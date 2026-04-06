"""
Servicio de administración — lógica de negocio para gestión de usuarios.

Solo accesible para superadmins.
"""

from __future__ import annotations

import asyncio

from integrations.supabase_client import get_supabase_client
from logger import get_logger
from middleware.error_handler import AppError

log = get_logger(__name__)

_db = get_supabase_client


async def _run(fn):
    """Ejecuta función sync de Supabase en executor."""
    return await asyncio.get_event_loop().run_in_executor(None, fn)


async def listar_usuarios() -> list[dict]:
    """Lista todos los usuarios con estadísticas de contactos y campañas."""
    resp = await _run(lambda: _db().table("usuarios_reach")
        .select("id, nombre, email, rol, created_at").order("created_at", desc=True).execute())
    usuarios = resp.data or []
    for u in usuarios:
        uid = u["id"]
        c_resp, camp_resp, emails_resp = await asyncio.gather(
            _run(lambda uid=uid: _db().table("contacts")
                .select("id", count="exact").eq("usuario_id", uid).execute()),
            _run(lambda uid=uid: _db().table("campaigns")
                .select("id", count="exact").eq("usuario_id", uid).execute()),
            _run(lambda uid=uid: _db().table("campaigns")
                .select("sent_count").eq("usuario_id", uid).execute()),
        )
        u["total_contactos"] = c_resp.count or 0
        u["total_campanas"] = camp_resp.count or 0
        u["total_emails_enviados"] = sum(r.get("sent_count", 0) for r in (emails_resp.data or []))
    log.info("Admin: listados %d usuarios", len(usuarios))
    return usuarios


async def obtener_usuario(id: str) -> dict:
    """Obtiene detalle de un usuario con sus últimos contactos y campañas."""
    resp = await _run(lambda: _db().table("usuarios_reach")
        .select("*").eq("id", id).limit(1).execute())
    if not resp.data:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    usuario = resp.data[0]
    contactos = await _run(lambda: _db().table("contacts")
        .select("*").eq("usuario_id", id).order("created_at", desc=True).limit(20).execute())
    campanas = await _run(lambda: _db().table("campaigns")
        .select("*").eq("usuario_id", id).order("created_at", desc=True).limit(10).execute())
    usuario["contactos"] = contactos.data or []
    usuario["campanas"] = campanas.data or []
    # Integraciones activas del usuario
    try:
        integ = await _run(lambda: _db().table("integraciones")
            .select("servicio").eq("activo", True).eq("usuario_id", id).execute())
        servicios = [r["servicio"] for r in (integ.data or [])]
        if usuario.get("rol") == "superadmin":
            from config.settings import get_settings
            if get_settings().GMAIL_FROM_EMAIL:
                servicios.append("gmail")
        usuario["integraciones"] = servicios
    except Exception:
        usuario["integraciones"] = []
    # Stats
    c_count = await _run(lambda: _db().table("contacts")
        .select("id", count="exact").eq("usuario_id", id).execute())
    camp_count = await _run(lambda: _db().table("campaigns")
        .select("sent_count").eq("usuario_id", id).execute())
    usuario["total_contactos"] = c_count.count or 0
    usuario["total_campanas"] = len(camp_count.data or [])
    usuario["total_emails_enviados"] = sum(r.get("sent_count", 0) for r in (camp_count.data or []))
    return usuario


async def editar_usuario(id: str, datos: dict) -> dict:
    """Edita nombre, email o rol de un usuario."""
    campos = {k: v for k, v in datos.items() if k in ("nombre", "email", "rol") and v}
    if not campos:
        raise AppError("No hay campos para actualizar", "NO_UPDATE_FIELDS", 400)
    if "rol" in campos and campos["rol"] not in ("user", "superadmin"):
        raise AppError("Rol inválido", "INVALID_ROLE", 400)
    resp = await _run(lambda: _db().table("usuarios_reach")
        .update(campos).eq("id", id).execute())
    if not resp.data:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    log.info("Admin: usuario %s editado — campos: %s", id, list(campos.keys()))
    return resp.data[0]


async def eliminar_usuario(id: str, mi_id: str) -> bool:
    """Elimina un usuario y todos sus datos en cascada."""
    if id == mi_id:
        raise AppError("No podés eliminarte a vos mismo", "CANNOT_DELETE_SELF", 400)
    # Verificar que existe
    resp = await _run(lambda: _db().table("usuarios_reach")
        .select("id").eq("id", id).limit(1).execute())
    if not resp.data:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    # Cascada en orden para respetar FK
    tablas = ["email_replies", "campaign_results", "campaigns",
              "bloque_contactos", "bloques", "contacts", "api_keys"]
    for tabla in tablas:
        try:
            await _run(lambda t=tabla: _db().table(t).delete().eq("usuario_id", id).execute())
        except Exception as exc:
            log.warning("Admin: error borrando %s de usuario %s: %s", tabla, id, exc)
    await _run(lambda: _db().table("usuarios_reach").delete().eq("id", id).execute())
    log.info("Admin: usuario %s eliminado con cascada", id)
    return True
