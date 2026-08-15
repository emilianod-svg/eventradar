"""Repositorio de `executions` — lock de ejecución única (sección 13).

Lock interino del Orquestador (sección 8.2): se apoya en la unique index
parcial `uq_executions_single_running` (migración
`1_20260815042852_single_running_execution.py`) para que Postgres rechace
atómicamente una segunda fila `RUNNING`, sin necesidad de un
check-then-insert vulnerable a carreras entre procesos.

TODO(17/08 - scheduler): esto cubre el caso de un solo proceso/worker de
FastAPI. Cuando entre APScheduler con múltiples workers (sección 13), sumar
un `pg_advisory_lock` de sesión real en `app/scheduler/locks.py` para
serializar también el arranque del ciclo, no solo la fila en `executions`.
"""

from __future__ import annotations

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
