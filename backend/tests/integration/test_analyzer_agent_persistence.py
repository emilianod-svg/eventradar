"""AnalyzerAgent: persistencia de `classifications` (sección 8.5, paso 8)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.domain.entities import RawContentCandidate
from app.models.classification import Classification
from app.models.raw_content import RawContent
from app.models.source import Source


class FakeLLMClient:
    def __init__(self, response: dict) -> None:
        self.response = response

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return self.response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyzer_persists_classification_linked_to_raw_content(
    tortoise_connection,
) -> None:
    source = await Source.create(
        name="Ticket Misiones", base_url="https://ticketmisiones.com", adapter_type="scrapy"
    )
    raw_content = await RawContent.create(
        source_id=source.id,
        url="https://ticketmisiones.com/eventos/feria-artesanal-2026",
        raw_text="Feria Artesanal de Invierno\n15 ago 2026",
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="hash-1",
    )
    raw = RawContentCandidate(
        id=raw_content.id,
        source_id=source.id,
        url=raw_content.url,
        raw_text=raw_content.raw_text,
        fetched_at=raw_content.fetched_at,
        content_hash=raw_content.content_hash,
    )
    llm = FakeLLMClient(
        {
            "is_event": True,
            "confidence": 0.92,
            "title": "Feria Artesanal de Invierno",
            "start_at": "2026-08-15T20:00:00-03:00",
            "venue_name": "Plaza 9 de Julio",
        }
    )
    agent = AnalyzerAgent(llm_client=llm)

    await agent.execute(raw)

    classifications = await Classification.filter(raw_content_id=raw_content.id)
    assert len(classifications) == 1
    stored = classifications[0]
    assert stored.is_event is True
    assert float(stored.confidence) == pytest.approx(0.92)
    assert stored.extracted_fields["title"] == "Feria Artesanal de Invierno"
    assert stored.prompt_version is not None
    assert stored.latency_ms is not None and stored.latency_ms >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyzer_skips_persistence_without_raw_content_id(tortoise_connection) -> None:
    raw = RawContentCandidate(
        source_id=(
            await Source.create(
                name="Sin persistir", base_url="https://example.com", adapter_type="rss"
            )
        ).id,
        url="https://example.com/nota",
        raw_text="Texto sin id de raw_content",
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="hash-2",
    )
    llm = FakeLLMClient({"is_event": False, "confidence": 0.1})
    agent = AnalyzerAgent(llm_client=llm)

    await agent.execute(raw)

    assert await Classification.all().count() == 0
