"""reap_abandoned_executions_job: dispara el reap y loguea si liberó algo."""

from __future__ import annotations

import logging
from uuid import uuid4

import pytest
from app.scheduler import watchdog


class _FakeExecution:
    def __init__(self, id_):
        self.id = id_


class FakeExecutionRepositoryReaps:
    def __init__(self) -> None:
        self.execution = _FakeExecution(uuid4())

    async def reap_abandoned(self, *, timeout_minutes: int):
        self.timeout_minutes = timeout_minutes
        return self.execution


class FakeExecutionRepositoryNoop:
    async def reap_abandoned(self, *, timeout_minutes: int):
        return None


@pytest.mark.asyncio
async def test_watchdog_job_logs_when_execution_reaped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fake_repo = FakeExecutionRepositoryReaps()
    monkeypatch.setattr(watchdog, "ExecutionRepository", lambda: fake_repo)

    with caplog.at_level(logging.WARNING, logger="eventradar.scheduler.watchdog"):
        await watchdog.reap_abandoned_executions_job()

    assert any(record.message == "watchdog_execution_reaped" for record in caplog.records)


@pytest.mark.asyncio
async def test_watchdog_job_silent_when_nothing_reaped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(watchdog, "ExecutionRepository", FakeExecutionRepositoryNoop)

    with caplog.at_level(logging.WARNING, logger="eventradar.scheduler.watchdog"):
        await watchdog.reap_abandoned_executions_job()

    assert not any(record.message == "watchdog_execution_reaped" for record in caplog.records)
