"""Pruebas del Agente Analizador."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.domain.entities import RawContentCandidate, SourceDefinition
from app.domain.enums import ProcessingStatus


class FakeLLMClient:
    def __init__(self, response: dict) -> None:
        self.response = response

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return self.response


@pytest.mark.asyncio
async def test_analyzer_agent_returns_event_candidate_when_confident() -> None:
    source = SourceDefinition(
        id=uuid4(),
        name="Ticket Misiones",
        base_url="https://ticketmisiones.com",
        adapter_type="scrapy",
    )
    raw = RawContentCandidate(
        source_id=source.id,
        url="https://ticketmisiones.com/eventos/feria-artesanal-2026",
        raw_text="Feria Artesanal de Invierno\n15 ago 2026\nArtesanos locales",
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="hash",
    )
    llm = FakeLLMClient(
        {
            "is_event": True,
            "confidence": 0.92,
            "title": "Feria Artesanal de Invierno",
        }
    )

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(raw)

    assert len(result) == 1
    assert result[0].title == "Feria Artesanal de Invierno"
    assert result[0].confidence == 0.92


@pytest.mark.asyncio
async def test_analyzer_agent_discards_low_confidence_or_non_event() -> None:
    raw = RawContentCandidate(
        source_id=uuid4(),
        url="https://example.com",
        raw_text="texto",
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="hash",
    )
    llm = FakeLLMClient({"is_event": True, "confidence": 0.4})

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(raw)

    assert result == []


def _raw_candidate(raw_text: str = "texto") -> RawContentCandidate:
    return RawContentCandidate(
        source_id=uuid4(),
        url="https://example.com",
        raw_text=raw_text,
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="hash",
    )


@pytest.mark.asyncio
async def test_analyzer_agent_marks_pending_review_between_thresholds() -> None:
    # Sección 8.5: confianza 0.50-0.69 debe crear un elemento PENDING_REVIEW,
    # no descartarse (a diferencia de <0.50, que sí se rechaza).
    llm = FakeLLMClient({"is_event": True, "confidence": 0.6, "title": "Feria"})

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(_raw_candidate())

    assert len(result) == 1
    assert result[0].processing_status == ProcessingStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_analyzer_agent_discards_publication_that_is_not_an_event() -> None:
    llm = FakeLLMClient({"is_event": False, "confidence": 0.95})

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(_raw_candidate("Publicidad de un local, no hay evento."))

    assert result == []


@pytest.mark.asyncio
async def test_analyzer_agent_accepts_recurrent_event_with_recurrence_text() -> None:
    llm = FakeLLMClient(
        {
            "is_event": True,
            "confidence": 0.85,
            "title": "Clase de yoga",
            "recurrence_text": "Todos los sábados a las 10hs",
        }
    )

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(_raw_candidate("Clase de yoga todos los sábados a las 10hs"))

    assert len(result) == 1
    assert result[0].recurrence_text == "Todos los sábados a las 10hs"
    assert result[0].processing_status == ProcessingStatus.ANALYZED


@pytest.mark.asyncio
async def test_analyzer_agent_resolves_relative_date_returned_by_llm() -> None:
    # El LLM es quien resuelve la fecha relativa a partir de extraction_date_iso
    # (sección 8.5); el Analizador solo valida que el resultado sea una fecha válida.
    llm = FakeLLMClient(
        {
            "is_event": True,
            "confidence": 0.8,
            "title": "Recital",
            "start_at": "2026-08-15T21:00:00Z",
        }
    )

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(_raw_candidate("Recital el próximo sábado"))

    assert len(result) == 1
    assert result[0].start_at is not None
    assert result[0].start_at.year == 2026
    assert result[0].start_at.month == 8
    assert result[0].start_at.day == 15
