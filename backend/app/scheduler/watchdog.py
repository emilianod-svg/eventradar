"""Watchdog de ejecuciones abandonadas (sección 13 del plan).

Job periódico independiente del ciclo cron: si no corriera, una `RUNNING`
colgada por un crash o un restart del contenedor quedaría bloqueando
`/internal/cycles` (vía `ConcurrentExecutionError`) hasta el próximo
ciclo programado (lunes/viernes). La lógica de qué cuenta como "abandonada"
vive en `ExecutionRepository.reap_abandoned` — acá solo se dispara y se
loguea el resultado.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.repositories.execution import ExecutionRepository

logger = logging.getLogger("eventradar.scheduler.watchdog")


async def reap_abandoned_executions_job() -> None:
    settings = get_settings()
    reaped = await ExecutionRepository().reap_abandoned(
        timeout_minutes=settings.execution_timeout_minutes
    )
    if reaped is not None:
        logger.warning(
            "watchdog_execution_reaped",
            extra={
                "execution_id": str(reaped.id),
                "timeout_minutes": settings.execution_timeout_minutes,
            },
        )
