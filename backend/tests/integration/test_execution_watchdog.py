"""ExecutionRepository.reap_abandoned contra Postgres real (sección 13)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.enums import ExecutionStatus
from app.models.execution import Execution
from app.repositories.execution import ExecutionRepository

TIMEOUT_MINUTES = 60


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reap_abandoned_noop_when_nothing_running(tortoise_connection) -> None:
    reaped = await ExecutionRepository().reap_abandoned(timeout_minutes=TIMEOUT_MINUTES)

    assert reaped is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reap_abandoned_noop_when_running_is_recent(tortoise_connection) -> None:
    await Execution.create(status=ExecutionStatus.RUNNING, triggered_by="manual")

    reaped = await ExecutionRepository().reap_abandoned(timeout_minutes=TIMEOUT_MINUTES)

    assert reaped is None
    execution = await Execution.get(status=ExecutionStatus.RUNNING)
    assert execution.status == ExecutionStatus.RUNNING


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reap_abandoned_marks_stale_execution_as_failed(tortoise_connection) -> None:
    execution = await Execution.create(status=ExecutionStatus.RUNNING, triggered_by="scheduler")
    # started_at es auto_now_add=True: Tortoise lo fuerza en el insert, así
    # que hay que pisarlo con un update explícito después de crear la fila.
    execution.started_at = datetime.now(UTC) - timedelta(minutes=TIMEOUT_MINUTES + 5)
    await execution.save(update_fields=["started_at"])

    reaped = await ExecutionRepository().reap_abandoned(timeout_minutes=TIMEOUT_MINUTES)

    assert reaped is not None
    assert reaped.id == execution.id
    assert reaped.status == ExecutionStatus.FAILED
    assert reaped.finished_at is not None
    assert "abandonada" in reaped.error_message

    # El lock quedó libre: una nueva RUNNING ya no debe romper por el
    # índice único.
    new_execution = await Execution.create(status=ExecutionStatus.RUNNING, triggered_by="manual")
    assert new_execution.status == ExecutionStatus.RUNNING
