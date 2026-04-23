"""
Scheduler de campanas programadas — APScheduler AsyncIO.

Usa un job de polling cada 1 minuto que evalua todas las campanas activas.
Exporta crear_scheduler() para el lifespan de la app y helpers para el controller.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from logger import get_logger

log = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Devuelve la instancia activa del scheduler."""
    return _scheduler


async def ejecutar_campanas_programadas() -> None:
    """
    Job de polling (cada 1 minuto): dispara campanas con vencimiento alcanzado.

    - Tipo 'unica': ejecuta si fecha_envio <= ahora.
    - Tipo 'recurrente': ejecuta si hoy es uno de los dias_semana programados,
      ya paso la hora_envio y no se ejecuto todavia hoy.
    """
    from repositories import campanas_programadas_repository as cp_repo
    from services import campanas_programadas_service as cp_svc

    try:
        campanas = await cp_repo.listar_programadas()
        if not campanas:
            return
        ahora = datetime.now(timezone.utc)
        hoy = ahora.date()
        hora_hoy = ahora.strftime("%H:%M")
        dia = ahora.weekday()  # 0=Lun … 6=Dom, igual que el frontend

        for c in campanas:
            cid = c["id"]
            try:
                fe_str = c.get("fecha_envio")
                ue_str = c.get("ultima_ejecucion")

                if c["tipo"] == "unica":
                    if not fe_str:
                        continue
                    fe = datetime.fromisoformat(fe_str)
                    fe = fe if fe.tzinfo else fe.replace(tzinfo=timezone.utc)
                    debe = fe <= ahora
                else:  # recurrente
                    ya_hoy = ue_str and datetime.fromisoformat(ue_str).date() >= hoy
                    debe = (
                        dia in (c.get("dias_semana") or [])
                        and hora_hoy >= c.get("hora_envio", "25:00")
                        and not ya_hoy
                    )

                if debe:
                    log.info("Scheduler: ejecutando campana '%s' (%s)", c.get("nombre"), cid)
                    await cp_svc.ejecutar(cid)
            except Exception as exc:
                log.error("Scheduler: error en campana %s: %s", cid, exc)
    except Exception as exc:
        log.error("Scheduler: error en job ejecutar_campanas_programadas: %s", exc)


def crear_scheduler() -> AsyncIOScheduler:
    """Crea y configura el scheduler con el job de polling.

    Returns:
        AsyncIOScheduler configurado. Llamar .start() al usar.
    """
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        ejecutar_campanas_programadas,
        IntervalTrigger(minutes=1),
        id="campanas_programadas",
        replace_existing=True,
    )
    return _scheduler


def agregar_campana(campana: dict) -> None:
    """Notifica al scheduler que hay una nueva campana.

    En el modelo de polling no requiere accion — el siguiente ciclo
    la detectara automaticamente.
    """
    log.debug("Campana '%s' creada — sera detectada en el proximo ciclo de polling", campana.get("id"))


def cancelar_campana(campana_id: str) -> None:
    """Notifica al scheduler que una campana fue cancelada.

    En el modelo de polling no requiere accion — las campanas con
    estado != 'programada' son omitidas por listar_programadas().
    """
    log.debug("Campana '%s' cancelada — sera omitida en el proximo ciclo de polling", campana_id)
