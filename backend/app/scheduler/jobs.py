"""Configuración de APScheduler (sección 13 del plan).

Corre in-process, dentro del lifespan de FastAPI (`app/main.py`): la
sección 19.2 del plan lo permite explícitamente ("puede vivir dentro de un
único proceso dedicado o del backend") y hoy `docker-compose.yml` levanta
un único contenedor `backend` sin `--workers`, así que no hay instancias
duplicadas corriendo. El scheduler entero se activa solo si
`SCHEDULER_ENABLED=true`.

Registra dos jobs:

- `eventradar-cycle`: dispara el ciclo real por `SCHEDULER_CRON`.
  `max_instances=1`/`coalesce=True` evitan que se solape consigo mismo,
  pero no contra un ciclo disparado manualmente por `POST
  /internal/cycles` en paralelo — para eso está el lock de
  `ExecutionRepository.start_new_run` (índice único parcial
  `uq_executions_single_running`, `ConcurrentExecutionError`), que acá se
  absorbe como resultado normal ("ya hay un ciclo corriendo, se lo
  salta"), no como una falla del scheduler.
- `eventradar-watchdog`: cada `WATCHDOG_INTERVAL_MINUTES`, libera una
  `RUNNING` colgada que superó `EXECUTION_TIMEOUT_MINUTES` (ver
  `app/scheduler/watchdog.py` y `ExecutionRepository.reap_abandoned`).

No hay `pg_advisory_lock`: el índice único ya es atómico entre procesos
por sí solo, así que agregar un lock de sesión encima sería redundante
(decisión final, sección 13, 17/08).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.agents.orchestrator import OrchestratorAgent
from app.config import get_settings
from app.domain.errors import ConcurrentExecutionError
from app.scheduler.watchdog import reap_abandoned_executions_job

logger = logging.getLogger("eventradar.scheduler")

WATCHDOG_INTERVAL_MINUTES = 5


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
    scheduler.add_job(
        reap_abandoned_executions_job,
        trigger=IntervalTrigger(minutes=WATCHDOG_INTERVAL_MINUTES),
        id="eventradar-watchdog",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
