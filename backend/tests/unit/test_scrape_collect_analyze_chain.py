"""Cadena mínima Scrapy -> Collector -> Analyzer."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.domain.dedupe import dedupe_by_hash
from app.domain.entities import SourceDefinition
from app.sources.rss_adapter import RssAdapter
from app.sources.scrapy_adapter import ScrapyAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


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

    async def fake_download(url: str) -> str:
        return html

    monkeypatch.setattr(adapter, "_download", fake_download)

    collector = CollectorAgent(scrapy_adapter=adapter)
    raw_candidates = await collector.execute(source)

    assert len(raw_candidates) == 2

    analyzer = AnalyzerAgent(llm_client=FakeLLMClient())
    analyzed = await analyzer.execute(raw_candidates[0])

    assert len(analyzed) == 1
    assert analyzed[0].title == "Feria Artesanal de Invierno"
    assert analyzed[0].confidence == 0.91


@pytest.mark.asyncio
async def test_three_sources_collect_and_dedupe_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ticket Misiones (HTML) + Misiones Online (RSS) + Misiones Cuatro (RSS).

    Cubre el criterio de aceptación de la tarea: las 3 fuentes fluyen por el
    Collector y, ante una segunda corrida con el mismo contenido, la
    idempotencia por hash no deja pasar candidatos repetidos.
    """
    ticket_misiones_html = (FIXTURES_DIR / "scrapy" / "ticketmisiones.html").read_text(
        encoding="utf-8"
    )
    misiones_online_xml = (FIXTURES_DIR / "rss" / "misionesonline.xml").read_text(encoding="utf-8")
    misiones_cuatro_xml = (FIXTURES_DIR / "rss" / "misionescuatro_espectaculos.xml").read_text(
        encoding="utf-8"
    )

    scrapy_adapter = ScrapyAdapter()

    async def fake_download(url: str) -> str:
        return ticket_misiones_html

    monkeypatch.setattr(scrapy_adapter, "_download", fake_download)

    rss_adapter = RssAdapter()
    feeds_by_url = {
        "https://misionesonline.net/feed/": misiones_online_xml,
        "https://misionescuatro.com/espectaculos/feed/": misiones_cuatro_xml,
    }

    async def fake_rss_download(url: str) -> str:
        return feeds_by_url[url]

    monkeypatch.setattr(rss_adapter, "_download", fake_rss_download)

    collector = CollectorAgent(scrapy_adapter=scrapy_adapter, rss_adapter=rss_adapter)
    sources = [
        SourceDefinition(
            id=uuid4(),
            name="Ticket Misiones",
            base_url="https://ticketmisiones.com",
            adapter_type="scrapy",
        ),
        SourceDefinition(
            id=uuid4(),
            name="Misiones Online",
            base_url="https://misionesonline.net/feed/",
            adapter_type="rss",
        ),
        SourceDefinition(
            id=uuid4(),
            name="Misiones Cuatro",
            base_url="https://misionescuatro.com/espectaculos/feed/",
            adapter_type="rss",
        ),
    ]

    async def run_cycle() -> list:
        all_candidates = []
        for source in sources:
            all_candidates.extend(await collector.execute(source))
        return all_candidates

    first_cycle = await run_cycle()
    new_in_first_cycle, seen_hashes = dedupe_by_hash(first_cycle)
    assert len(new_in_first_cycle) == len(first_cycle) == 7  # 2 + 3 + 2

    second_cycle = await run_cycle()
    new_in_second_cycle, _ = dedupe_by_hash(second_cycle, seen_hashes=seen_hashes)
    assert new_in_second_cycle == []
