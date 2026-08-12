"""Pruebas del Agente Analizador."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.agents.analyzer import AnalyzerAgent
from app.domain.entities import RawContentCandidate, SourceDefinition


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
        fetched_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
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
        fetched_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
        content_hash="hash",
    )
    llm = FakeLLMClient({"is_event": True, "confidence": 0.4})

    agent = AnalyzerAgent(llm_client=llm)
    result = await agent.execute(raw)

    assert result == []
