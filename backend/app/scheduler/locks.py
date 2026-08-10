"""Lock de ejecución única (sección 13 del plan).

Debe garantizar que nunca exista más de una ejecución `RUNNING`
simultáneamente, incluso con múltiples workers de FastAPI (mediante un lock
PostgreSQL con `pg_advisory_lock` u equivalente). Pendiente de
implementación: por ahora expone únicamente la interfaz para que el
Orquestador pueda depender de ella sin conocer el mecanismo concreto.
"""

from __future__ import annotations

from typing import Protocol


class ExecutionLock(Protocol):
    async def acquire(self) -> bool: ...
    async def release(self) -> None: ...


class NotImplementedExecutionLock:
    async def acquire(self) -> bool:
        raise NotImplementedError("ExecutionLock.acquire: pendiente de implementación (sección 13).")

    async def release(self) -> None:
        raise NotImplementedError("ExecutionLock.release: pendiente de implementación (sección 13).")
