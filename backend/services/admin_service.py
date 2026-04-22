"""
Servicio de administracion — logica de negocio para gestion de usuarios.
Solo accesible para superadmins.
"""
from __future__ import annotations

import bcrypt

from config.settings import get_settings
from logger import get_logger
from middleware.error_handler import AppError
from repositories import admin_repository
from utils.db import METODOS_BUSQUEDA_VALIDOS

log = get_logger(__name__)


async def crear_usuario(email: str, password: str, nombre: str, rol: str) -> dict:
    """Crea usuario validando rol, verificando email unico y hasheando password."""
    if rol not in ("user", "superadmin"):
        raise AppError("Rol invalido", "INVALID_ROLE", 400)
    if await admin_repository.buscar_por_email(email):
        raise AppError("El email ya esta registrado", "EMAIL_ALREADY_EXISTS", 409)
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    usuario = await admin_repository.insertar_usuario(email, password_hash, nombre, rol)
    log.info("Admin: usuario creado — %s (%s)", email, rol)
    return usuario


async def listar_usuarios() -> list[dict]:
    """Lista todos los usuarios con estadisticas."""
    result = await admin_repository.listar_usuarios()
    log.info("Admin: listados %d usuarios", len(result))
    return result


async def obtener_usuario(id: str) -> dict:
    """Obtiene detalle completo de un usuario con contactos, campanas e integraciones."""
    usuario = await admin_repository.obtener_usuario_por_id(id)
    if not usuario:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    contactos = await admin_repository.obtener_contactos_usuario(id)
    campanas = await admin_repository.obtener_campanas_usuario(id)
    contadores = await admin_repository.obtener_contadores_usuario(id)
    servicios = await admin_repository.obtener_integraciones_usuario(id)
    if usuario.get("rol") == "superadmin" and get_settings().GMAIL_FROM_EMAIL:
        servicios.append("gmail")
    usuario["contactos"] = contactos
    usuario["campanas"] = campanas
    usuario["total_contactos"] = contadores["total_contactos"]
    usuario["total_campanas"] = len(campanas)
    usuario["total_emails_enviados"] = contadores["total_emails"]
    usuario["integraciones"] = servicios
    return usuario


async def obtener_metodos(id: str) -> dict:
    """Retorna metodos_habilitados del usuario (todos si la columna es NULL)."""
    metodos = await admin_repository.obtener_metodos_habilitados(id)
    return {"metodos_habilitados": metodos if metodos is not None else list(METODOS_BUSQUEDA_VALIDOS)}


async def editar_usuario(id: str, datos: dict) -> dict:
    """Edita campos del usuario validando rol y metodos antes de persistir."""
    campos = {k: v for k, v in datos.items() if k in ("nombre", "email", "rol", "metodos_habilitados") and v is not None}
    if not campos:
        raise AppError("No hay campos para actualizar", "NO_UPDATE_FIELDS", 400)
    if "rol" in campos and campos["rol"] not in ("user", "superadmin"):
        raise AppError("Rol invalido", "INVALID_ROLE", 400)
    if "metodos_habilitados" in campos:
        metodos = campos["metodos_habilitados"]
        if not isinstance(metodos, list) or not all(m in METODOS_BUSQUEDA_VALIDOS for m in metodos):
            raise AppError("metodos_habilitados contiene valores invalidos", "INVALID_METODOS", 400)
    row = await admin_repository.editar_usuario(id, campos)
    if not row:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    log.info("Admin: usuario %s editado — campos: %s", id, list(campos.keys()))
    return row


async def eliminar_usuario(id: str, mi_id: str) -> bool:
    """Elimina usuario con cascada; lanza error si intenta eliminarse a si mismo."""
    if id == mi_id:
        raise AppError("No podes eliminarte a vos mismo", "CANNOT_DELETE_SELF", 400)
    eliminado = await admin_repository.eliminar_usuario_cascade(id)
    if not eliminado:
        raise AppError("Usuario no encontrado", "USER_NOT_FOUND", 404)
    log.info("Admin: usuario %s eliminado con cascada", id)
    return True
