"""
Servicio de campanas programadas — logica de negocio.

Valida datos, crea registros y orquesta la ejecucion via send_service.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from integrations.postgres_client import get_pool
from logger import get_logger
from middleware.error_handler import AppError
from repositories import campanas_programadas_repository as repo
from services import send_service

log = get_logger(__name__)


async def _validar_template(template_id: str, usuario_id: str) -> None:
    """Verifica que el template exista y pertenezca al usuario."""
    try:
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM templates WHERE id = $1 AND usuario_id = $2 LIMIT 1",
                uuid.UUID(template_id),
                uuid.UUID(usuario_id),
            )
    except Exception as e:
        raise AppError(f"Error validando datos: {str(e)}", "VALIDATION_DB_ERROR", 500)
    if not row:
        raise AppError("Template no encontrado", "TEMPLATE_NOT_FOUND", 404)


async def _validar_contactos(contact_ids: list[str], usuario_id: str) -> None:
    """Verifica que TODOS los contactos existan y pertenezcan al usuario."""
    try:
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id FROM contacts WHERE id = ANY($1::uuid[]) AND usuario_id = $2",
                [uuid.UUID(cid) for cid in contact_ids],
                uuid.UUID(usuario_id),
            )
    except Exception as e:
        raise AppError(f"Error validando datos: {str(e)}", "VALIDATION_DB_ERROR", 500)
    if len(rows) != len(contact_ids):
        raise AppError("Ningun contacto encontrado", "CONTACTS_NOT_FOUND", 404)


async def crear(usuario_id: str, datos: dict) -> dict:
    """Valida y crea una campana programada. Retorna el registro creado."""
    tipo = datos.get("tipo")
    if tipo not in ("unica", "recurrente"):
        raise AppError("tipo debe ser 'unica' o 'recurrente'", "TIPO_INVALIDO", 400)
    if not datos.get("hora_envio"):
        raise AppError("hora_envio es requerida (HH:MM)", "HORA_REQUERIDA", 400)
    if tipo == "unica" and not datos.get("fecha_envio"):
        raise AppError("fecha_envio es requerida para campanas de tipo 'unica'", "FECHA_REQUERIDA", 400)
    if tipo == "recurrente" and not datos.get("dias_semana"):
        raise AppError("dias_semana es requerido para campanas recurrentes", "DIAS_REQUERIDOS", 400)

    await _validar_template(str(datos["template_id"]), usuario_id)
    await _validar_contactos([str(cid) for cid in datos["contact_ids"]], usuario_id)

    campana = await repo.crear(usuario_id, {
        "nombre": datos["nombre"],
        "template_id": str(datos["template_id"]),
        "contact_ids": [str(cid) for cid in datos["contact_ids"]],
        "bloque_id": datos.get("bloque_id"),
        "tipo": tipo,
        "fecha_envio": datos.get("fecha_envio"),
        "dias_semana": datos.get("dias_semana"),
        "hora_envio": datos["hora_envio"],
        "estado": "programada",
    })
    log.info("Campana programada '%s' creada (%s)", campana["nombre"], campana["id"])
    return campana


async def listar(usuario_id: str) -> list[dict]:
    """Lista campanas programadas del usuario."""
    return await repo.listar(usuario_id)


async def cancelar(campana_id: str, usuario_id: str) -> None:
    """Cancela una campana programada del usuario."""
    await repo.cancelar(campana_id, usuario_id)
    log.info("Campana programada cancelada: %s", campana_id)


async def ejecutar(campana_id: str) -> None:
    """Ejecuta una campana programada: obtiene datos y llama a send_service."""
    try:
        campana = await repo.obtener_sin_usuario(campana_id)
        contact_ids = [str(cid) for cid in campana.get("contact_ids", [])]
        log.info("Ejecutando campana programada '%s' (%s)", campana["nombre"], campana_id)

        await send_service.enviar_campana(
            campana["nombre"], campana["template_id"], contact_ids, None,
            usuario_id=campana.get("usuario_id"), rol="user",
        )
        ahora = datetime.now(timezone.utc).isoformat()
        # Recurrente vuelve a 'programada'; unica pasa a 'ejecutada'
        nuevo_estado = "programada" if campana["tipo"] == "recurrente" else "ejecutada"
        await repo.actualizar_estado(campana_id, nuevo_estado, ahora)
        log.info("Campana %s ejecutada → estado '%s'", campana_id, nuevo_estado)
    except AppError:
        await repo.actualizar_estado(campana_id, "fallida")
        raise
    except Exception as exc:
        log.error("Error ejecutando campana programada %s: %s", campana_id, exc)
        await repo.actualizar_estado(campana_id, "fallida")
        raise AppError("Error al ejecutar campana programada", "CAMPANA_PROG_EXEC", 500) from exc
