"""Cadena mínima Scrapy -> Collector -> Analyzer."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.domain.entities import SourceDefinition
from app.sources.scrapy_adapter import ScrapyAdapter


class FakeLLMClient:
    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        return {
            "is_event": True,
            "confidence": 0.91,
            "title": "Feria Artesanal de Invierno",
            "description": text,
            "category": "feria",
            "evidence": {"title": "Feria Artesanal de Invierno"},
        }


@pytest.mark.asyncio
async def test_scrapy_collector_and_analyzer_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "scrapy" / "ticketmisiones.html"
    )
    html = fixture_path.read_text(encoding="utf-8")

    source = SourceDefinition(
        id=uuid4(),
        name="Ticket Misiones",
        base_url="https://ticketmisiones.com",
        adapter_type="scrapy",
    )

    adapter = ScrapyAdapter()
    monkeypatch.setattr(adapter, "_download", lambda url: html)

    collector = CollectorAgent(scrapy_adapter=adapter)
    raw_candidates = await collector.execute(source)

    assert len(raw_candidates) == 2

    analyzer = AnalyzerAgent(llm_client=FakeLLMClient())
    analyzed = await analyzer.execute(raw_candidates[0])

    assert len(analyzed) == 1
    assert analyzed[0].title == "Feria Artesanal de Invierno"
    assert analyzed[0].confidence == 0.91
