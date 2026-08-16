"""OrchestratorAgent: ciclo E2E (sección 8.2), casos obligatorios de 18.3.

Usa CollectorAgent/AnalyzerAgent/GeoClassifierAgent reales (con sus
dependencias externas fakeadas) para que la persistencia real de
raw_contents/classifications/events/executions se ejerza de punta a punta,
igual que en un ciclo real — solo el HTTP/LLM/geocoding están fakeados.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.agents.geo_classifier import GeoClassifierAgent
from app.agents.orchestrator import OrchestratorAgent
from app.domain.entities import RawContentCandidate, SourceDefinition
from app.domain.enums import ExecutionStatus
from app.domain.errors import ConcurrentExecutionError
from app.models.event import Event
from app.models.execution import Execution
from app.models.execution_source import ExecutionSource
from app.models.source import Source


class ConditionalRssAdapter:
    def __init__(
        self,
        candidates_by_source: dict[UUID, list[RawContentCandidate]],
        failing_source_ids: frozenset[UUID] = frozenset(),
    ) -> None:
        self._by_source = candidates_by_source
        self._failing = failing_source_ids

    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        if source.id in self._failing:
            raise RuntimeError("fuente caída (timeout simulado)")
        return list(self._by_source.get(source.id, []))


class FixedLLMClient:
    def __init__(self, response: dict) -> None:
        self.response = response

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return self.response


def _raw_candidate(source_id: UUID, *, content_hash: str) -> RawContentCandidate:
    return RawContentCandidate(
        source_id=source_id,
        url="https://example.com/nota",
        raw_text="Festival del Litoral el sabado en la plaza",
        fetched_at=datetime.now(UTC),
        content_hash=content_hash,
    )


def _llm_response(**overrides: object) -> dict:
    payload = {
        "is_event": True,
        "confidence": 0.9,
        "title": "Festival del Litoral",
        "venue_name": "Plaza 9 de Julio",
        "address": "Posadas, Misiones",
        "start_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "latitude": -27.3671,
        "longitude": -55.8961,
    }
    payload.update(overrides)
    return payload


def _build_orchestrator(
    *,
    candidates_by_source: dict[UUID, list[RawContentCandidate]],
    failing_source_ids: frozenset[UUID] = frozenset(),
    llm_response: dict | None = None,
) -> OrchestratorAgent:
    rss_adapter = ConditionalRssAdapter(candidates_by_source, failing_source_ids)
    collector = CollectorAgent(rss_adapter=rss_adapter)
    analyzer = AnalyzerAgent(llm_client=FixedLLMClient(llm_response or _llm_response()))
    geo_classifier = GeoClassifierAgent()
    return OrchestratorAgent(collector=collector, analyzer=analyzer, geo_classifier=geo_classifier)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_processes_source_and_accepts_event(tortoise_connection) -> None:
    source = await Source.create(
        name="Misiones Online", base_url="https://misionesonline.net/feed/", adapter_type="rss"
    )
    orchestrator = _build_orchestrator(
        candidates_by_source={source.id: [_raw_candidate(source.id, content_hash="h1")]}
    )

    metadata = await orchestrator.execute()

    assert metadata.status == ExecutionStatus.COMPLETED
    assert metadata.execution_id is not None

    execution = await Execution.get(id=metadata.execution_id)
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.metrics["events_accepted"] == 1
    assert execution.metrics["sources_failed"] == 0

    events = await Event.all()
    assert len(events) == 1
    assert events[0].title == "Festival del Litoral"

    exec_sources = await ExecutionSource.filter(execution=execution)
    assert len(exec_sources) == 1
    assert exec_sources[0].status == "COMPLETED"
    assert exec_sources[0].items_collected == 1
    assert exec_sources[0].items_accepted == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_isolates_source_failure_as_partial(tortoise_connection) -> None:
    healthy = await Source.create(name="sana", base_url="https://a", adapter_type="rss")
    broken = await Source.create(name="caida", base_url="https://b", adapter_type="rss")
    orchestrator = _build_orchestrator(
        candidates_by_source={healthy.id: [_raw_candidate(healthy.id, content_hash="h1")]},
        failing_source_ids=frozenset({broken.id}),
    )

    metadata = await orchestrator.execute()

    assert metadata.status == ExecutionStatus.PARTIAL
    execution = await Execution.get(id=metadata.execution_id)
    assert execution.metrics["sources_failed"] == 1
    assert execution.metrics["sources_processed"] == 1

    assert await Event.all().count() == 1

    broken_exec_source = await ExecutionSource.get(execution=execution, source=broken)
    assert broken_exec_source.status == "FAILED"
    assert "fuente caída" in (broken_exec_source.error_message or "")

    healthy_exec_source = await ExecutionSource.get(execution=execution, source=healthy)
    assert healthy_exec_source.status == "COMPLETED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_rejects_concurrent_cycle(tortoise_connection) -> None:
    await Execution.create(status=ExecutionStatus.RUNNING, triggered_by="manual")
    orchestrator = _build_orchestrator(candidates_by_source={})

    with pytest.raises(ConcurrentExecutionError):
        await orchestrator.execute()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_updates_source_reliability_and_archives_past_events(
    tortoise_connection,
) -> None:
    source = await Source.create(
        name="Misiones Cuatro",
        base_url="https://misionescuatro.com/espectaculos/feed/",
        adapter_type="rss",
        reliability_score=0.5,
    )
    past_event = await Event.create(
        title="Evento vencido",
        slug="evento-vencido",
        start_at=datetime.now(UTC) - timedelta(days=1),
        venue_name="X",
    )
    orchestrator = _build_orchestrator(
        candidates_by_source={source.id: [_raw_candidate(source.id, content_hash="h1")]}
    )

    metadata = await orchestrator.execute()

    execution = await Execution.get(id=metadata.execution_id)
    assert execution.metrics["events_archived"] == 1

    await source.refresh_from_db()
    assert float(source.reliability_score) != 0.5  # el aprendizaje corrió

    await past_event.refresh_from_db()
    assert past_event.status == "ARCHIVED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_second_cycle_with_same_content_does_not_duplicate_events(
    tortoise_connection,
) -> None:
    source = await Source.create(name="s", base_url="https://s", adapter_type="rss")
    orchestrator = _build_orchestrator(
        candidates_by_source={source.id: [_raw_candidate(source.id, content_hash="stable-hash")]}
    )

    first = await orchestrator.execute()
    assert first.status == ExecutionStatus.COMPLETED
    assert await Event.all().count() == 1

    second = await orchestrator.execute()
    assert second.status == ExecutionStatus.COMPLETED

    second_execution = await Execution.get(id=second.execution_id)
    assert second_execution.metrics["items_collected"] == 0
    assert await Event.all().count() == 1
