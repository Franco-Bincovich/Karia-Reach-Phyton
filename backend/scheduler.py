"""
Scheduler de campanas programadas — AsyncIOScheduler de APScheduler.

Al arrancar carga todas las campanas con estado 'programada'.
Expone funciones para agregar y cancelar jobs en tiempo real.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from logger import get_logger
from repositories import campanas_programadas_repository as repo
from services import campanas_programadas_service

log = get_logger(__name__)

_scheduler = AsyncIOScheduler()


def get_scheduler() -> AsyncIOScheduler:
    """Devuelve la instancia global del scheduler."""
    return _scheduler


async def iniciar() -> None:
    """Carga campanas activas de la DB y arranca el scheduler."""
    campanas = await repo.listar_programadas()
    for campana in campanas:
        _agregar_job(campana)
    _scheduler.start()
    log.info("Scheduler iniciado con %d campana(s) programada(s)", len(campanas))


def detener() -> None:
    """Detiene el scheduler limpiamente en shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler detenido")


def _agregar_job(campana: dict) -> None:
    """Calcula el trigger y registra el job en el scheduler."""
    campana_id = campana["id"]
    job_id = f"campana_{campana_id}"
    hora_envio = campana.get("hora_envio", "09:00")
    hora, minuto = hora_envio.split(":")

    if campana["tipo"] == "unica":
        fecha_envio = campana.get("fecha_envio")
        if not fecha_envio:
            log.warning("Campana unica %s sin fecha_envio — ignorada", campana_id)
            return
        if isinstance(fecha_envio, str):
            fecha_envio = datetime.fromisoformat(fecha_envio.replace("Z", "+00:00"))
        if fecha_envio < datetime.now(timezone.utc):
            log.warning("Campana unica %s con fecha en el pasado — ignorada", campana_id)
            return
        trigger = DateTrigger(run_date=fecha_envio)
    else:
        dias = campana.get("dias_semana") or []
        if not dias:
            log.warning("Campana recurrente %s sin dias_semana — ignorada", campana_id)
            return
        dia_str = ",".join(str(d) for d in dias)
        trigger = CronTrigger(day_of_week=dia_str, hour=int(hora), minute=int(minuto))

    _scheduler.add_job(
        campanas_programadas_service.ejecutar,
        trigger=trigger,
        args=[campana_id],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,
    )
    log.info("Job registrado: %s (tipo=%s)", job_id, campana["tipo"])


def agregar_campana(campana: dict) -> None:
    """Agrega una campana al scheduler en tiempo real al crearla."""
    if _scheduler.running:
        _agregar_job(campana)


def cancelar_campana(campana_id: str) -> None:
    """Remueve el job del scheduler al cancelar una campana."""
    job_id = f"campana_{campana_id}"
    job = _scheduler.get_job(job_id)
    if job:
        job.remove()
        log.info("Job removido: %s", job_id)
