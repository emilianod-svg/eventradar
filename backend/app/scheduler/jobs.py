"""Configuración de APScheduler (sección 13 del plan).

Un único scheduler activo: debe ejecutarse como proceso/servicio separado
del backend web (o garantizar una sola instancia activa), nunca en cada
worker de FastAPI (ver Fase 5 del prompt de inicialización y sección 19.2
del plan). El cron se lee desde `SCHEDULER_CRON` y solo se activa si
`SCHEDULER_ENABLED=true`.

`max_instances=1`/`coalesce=True` evitan que este job se solape consigo
mismo, pero no contra un ciclo disparado manualmente por
`POST /internal/cycles` en paralelo — para eso está el lock interino de
`ExecutionRepository.start_new_run` (`ConcurrentExecutionError`), que acá se
absorbe como resultado normal ("ya hay un ciclo corriendo, se lo salta"), no
como una falla del scheduler.

TODO(17/08): esto sigue siendo el esqueleto de proceso único; falta el
`pg_advisory_lock` real y el watchdog de ejecuciones abandonadas (sección
13) para el caso de múltiples workers/instancias del scheduler.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agents.orchestrator import OrchestratorAgent
from app.config import get_settings
from app.domain.errors import ConcurrentExecutionError

logger = logging.getLogger("eventradar.scheduler")


async def run_cycle_job() -> None:
    try:
        metadata = await OrchestratorAgent(triggered_by="scheduler").execute()
    except ConcurrentExecutionError:
        logger.info("scheduler_cycle_skipped_already_running")
        return
    logger.info(
        "scheduler_cycle_finished",
        extra={"status": metadata.status, "execution_id": str(metadata.execution_id)},
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
