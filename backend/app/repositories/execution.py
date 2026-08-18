"""Repositorio de `executions` — lock de ejecución única (sección 13).

El lock es el índice único parcial `uq_executions_single_running`
(migración `1_20260815042852_single_running_execution.py`): Postgres
rechaza atómicamente una segunda fila `RUNNING`, sin necesidad de un
check-then-insert vulnerable a carreras entre procesos, y sin necesidad de
un `pg_advisory_lock` adicional — el índice ya es atómico entre procesos
por sí solo (decisión final, no interina: sección 13, 17/08).

`reap_abandoned` es el otro lado del lock: el watchdog (`app/scheduler/
watchdog.py`) lo usa para liberar una fila `RUNNING` que quedó colgada
(crash, restart) sin esperar a que alguien la cierre a mano.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tortoise.exceptions import IntegrityError

from app.domain.enums import ExecutionStatus
from app.domain.errors import ConcurrentExecutionError
from app.models.execution import Execution
from app.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    def __init__(self) -> None:
        super().__init__(Execution)

    async def start_new_run(self, *, triggered_by: str = "manual") -> Execution:
        try:
            return await Execution.create(status=ExecutionStatus.RUNNING, triggered_by=triggered_by)
        except IntegrityError as exc:
            raise ConcurrentExecutionError(
                "Ya existe una ejecución en curso (status=RUNNING)."
            ) from exc

    async def get_running(self) -> Execution | None:
        return await Execution.get_or_none(status=ExecutionStatus.RUNNING)

    async def reap_abandoned(self, *, timeout_minutes: int) -> Execution | None:
        """Marca `FAILED` la ejecución `RUNNING` si superó `timeout_minutes`.

        Como el índice único garantiza como máximo una fila `RUNNING` a la
        vez, alcanza con mirar `get_running()` — no hace falta filtrar una
        lista. Devuelve la ejecución si la marcó como abandonada, `None` si
        no había ninguna corriendo o si todavía está dentro del timeout.
        """

        execution = await self.get_running()
        if execution is None:
            return None

        cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)
        if execution.started_at > cutoff:
            return None

        execution.status = ExecutionStatus.FAILED
        execution.error_message = (
            f"Ejecución abandonada: sin finalizar tras {timeout_minutes} minutos (watchdog)."
        )
        execution.finished_at = datetime.now(UTC)
        await execution.save()
        return execution
