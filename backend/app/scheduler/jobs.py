"""Configuración de APScheduler (sección 13 del plan).

Un único scheduler activo: debe ejecutarse como proceso/servicio separado
del backend web (o garantizar una sola instancia activa), nunca en cada
worker de FastAPI (ver Fase 5 del prompt de inicialización y sección 19.2
del plan). El cron se lee desde `SCHEDULER_CRON` y solo se activa si
`SCHEDULER_ENABLED=true`.

Esta inicialización deja el esqueleto listo mostrando la intención de
diseño (proceso separado). La conexión con el Orquestador real queda
pendiente porque el Orquestador todavía no está implementado.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings

logger = logging.getLogger("eventradar.scheduler")


async def run_cycle_job() -> None:
    raise NotImplementedError(
        "run_cycle_job: depende de OrchestratorAgent, pendiente de implementación."
    )


def build_scheduler() -> AsyncIOScheduler | None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("Scheduler deshabilitado (SCHEDULER_ENABLED=false).")
        return None

    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_cycle_job,
        trigger=CronTrigger.from_crontab(settings.scheduler_cron, timezone=settings.timezone),
        id="eventradar-cycle",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
