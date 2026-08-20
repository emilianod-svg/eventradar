"""run_cycle_job: conecta con el Orquestador y absorbe ciclos concurrentes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app import scheduler as scheduler_pkg  # noqa: F401  (asegura import limpio del paquete)
from app.domain.entities import AgentRunMetadata
from app.domain.errors import ConcurrentExecutionError
from app.scheduler import jobs


class FakeOrchestratorSuccess:
    def __init__(self, triggered_by: str) -> None:
        self.triggered_by = triggered_by

    async def execute(self, data=None) -> AgentRunMetadata:
        return AgentRunMetadata(
            agent="OrchestratorAgent", duration_ms=1.0, status="COMPLETED", execution_id=uuid4()
        )


class FakeOrchestratorConcurrent:
    def __init__(self, triggered_by: str) -> None:
        self.triggered_by = triggered_by

    async def execute(self, data=None) -> AgentRunMetadata:
        raise ConcurrentExecutionError("ya hay un ciclo RUNNING")


@pytest.mark.asyncio
async def test_run_cycle_job_triggers_orchestrator_as_scheduler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    class Capturing(FakeOrchestratorSuccess):
        def __init__(self, triggered_by: str) -> None:
            captured["triggered_by"] = triggered_by
            super().__init__(triggered_by)

    monkeypatch.setattr(jobs, "OrchestratorAgent", Capturing)

    await jobs.run_cycle_job()

    assert captured["triggered_by"] == "scheduler"


@pytest.mark.asyncio
async def test_run_cycle_job_swallows_concurrent_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs, "OrchestratorAgent", FakeOrchestratorConcurrent)

    await jobs.run_cycle_job()  # no debe propagar la excepción


def test_build_scheduler_returns_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")

    assert jobs.build_scheduler() is None

    get_settings.cache_clear()


def test_build_scheduler_registers_cycle_and_watchdog_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")

    scheduler = jobs.build_scheduler()
    assert scheduler is not None
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert job_ids == {"eventradar-cycle", "eventradar-watchdog"}

    get_settings.cache_clear()
