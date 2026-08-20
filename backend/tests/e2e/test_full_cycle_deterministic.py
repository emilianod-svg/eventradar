"""Ciclo E2E determinístico con fuentes simuladas (sección 18.2).

Las 3 fuentes de la sección 8.4 (Ticket Misiones vía Scrapy, Misiones Online
y Misiones Cuatro vía RSS) fluyen por el ciclo completo real —
Collector → Analyzer → GeoClassifier → Evaluator → Persistence,
orquestado por `OrchestratorAgent` — usando las fixtures HTML/XML
versionadas de `tests/fixtures/` (sección 18.2: "parsers con fixtures
versionadas") en vez de red real. Solo el LLM y el geocoding están
fakeados; todo lo demás (parsers, hash, transacciones, dedup, aprendizaje)
es código real.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.agents.geo_classifier import GeoClassifierAgent
from app.agents.orchestrator import OrchestratorAgent
from app.domain.enums import EvaluationDecisionType, ExecutionStatus
from app.models.evaluation_decision import EvaluationDecision
from app.models.event import Event
from app.models.event_source import EventSource
from app.models.execution import Execution
from app.models.source import Source
from app.sources.rss_adapter import RssAdapter
from app.sources.scrapy_adapter import ScrapyAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class FixedLLMClient:
    """Mismo evento para las 7 publicaciones de las 3 fuentes: ejercita
    deduplicación real (RapidFuzz) entre fuentes distintas, no solo
    persistencia de un único candidato."""

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return {
            "is_event": True,
            "confidence": 0.88,
            "title": "Festival del Litoral",
            "venue_name": "Anfiteatro Manuel Antonio Ramirez",
            "address": "Posadas, Misiones",
            "start_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "latitude": -27.3671,
            "longitude": -55.8961,
        }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_cycle_across_three_sources_deduplicates_and_completes(
    monkeypatch: pytest.MonkeyPatch, tortoise_connection
) -> None:
    ticket_misiones_html = (FIXTURES_DIR / "scrapy" / "ticketmisiones.html").read_text(
        encoding="utf-8"
    )
    misiones_online_xml = (FIXTURES_DIR / "rss" / "misionesonline.xml").read_text(encoding="utf-8")
    misiones_cuatro_xml = (FIXTURES_DIR / "rss" / "misionescuatro_espectaculos.xml").read_text(
        encoding="utf-8"
    )

    await Source.create(
        name="Ticket Misiones", base_url="https://ticketmisiones.com", adapter_type="scrapy"
    )
    await Source.create(
        name="Misiones Online",
        base_url="https://misionesonline.net/feed/",
        adapter_type="rss_feed",
    )
    await Source.create(
        name="Misiones Cuatro",
        base_url="https://misionescuatro.com/espectaculos/feed/",
        adapter_type="rss_feed",
    )

    scrapy_adapter = ScrapyAdapter()

    async def fake_scrapy_download(url: str) -> str:
        return ticket_misiones_html

    monkeypatch.setattr(scrapy_adapter, "_download", fake_scrapy_download)

    rss_adapter = RssAdapter()
    feeds_by_url = {
        "https://misionesonline.net/feed/": misiones_online_xml,
        "https://misionescuatro.com/espectaculos/feed/": misiones_cuatro_xml,
    }

    async def fake_rss_download(url: str) -> str:
        return feeds_by_url[url]

    monkeypatch.setattr(rss_adapter, "_download", fake_rss_download)

    orchestrator = OrchestratorAgent(
        collector=CollectorAgent(scrapy_adapter=scrapy_adapter, rss_adapter=rss_adapter),
        analyzer=AnalyzerAgent(llm_client=FixedLLMClient()),
        geo_classifier=GeoClassifierAgent(),
    )

    metadata = await orchestrator.execute()

    assert metadata.status == ExecutionStatus.COMPLETED
    execution = await Execution.get(id=metadata.execution_id)
    assert execution.metrics["sources_failed"] == 0
    assert execution.metrics["sources_processed"] == 3
    assert execution.metrics["items_collected"] == 7  # 2 (scrapy) + 3 + 2 (rss)
    assert execution.metrics["events_accepted"] == 1
    assert execution.metrics["events_merged"] == 6

    # Un solo evento consolidado, con las 3 fuentes vinculadas (sección 10.5:
    # "no se elimina la fuente secundaria"). Cada URL distinta de las 7
    # publicaciones queda como su propia fila `event_sources` (unique_together
    # event+source+source_url), pero deben resolver a solo 3 `source_id`.
    events = await Event.all()
    assert len(events) == 1
    linked_sources = await EventSource.filter(event=events[0])
    assert len(linked_sources) == 7
    assert len({s.source_id for s in linked_sources}) == 3

    decisions = await EvaluationDecision.all()
    assert sum(1 for d in decisions if d.decision == EvaluationDecisionType.ACCEPT) == 1
    assert sum(1 for d in decisions if d.decision == EvaluationDecisionType.MERGE) == 6

    # Segunda corrida con el mismo contenido: idempotencia real de punta a
    # punta, sin duplicar el evento (caso obligatorio 18.3).
    second = await orchestrator.execute()
    assert second.status == ExecutionStatus.COMPLETED
    second_execution = await Execution.get(id=second.execution_id)
    assert second_execution.metrics["items_collected"] == 0
    assert await Event.all().count() == 1
