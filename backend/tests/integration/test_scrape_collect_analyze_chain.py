"""Cadena mínima Scrapy/RSS -> Collector (persistido) -> Analyzer.

Movido a integración: desde que `CollectorAgent` persiste `raw_contents`
(idempotencia real por hash, sección 13), necesita una fuente existente en
la base (FK) y una conexión Tortoise real, no solo objetos en memoria.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.agents.collector import CollectorAgent
from app.domain.entities import SourceDefinition
from app.models.source import Source
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


async def _source_definition(*, name: str, base_url: str, adapter_type: str) -> SourceDefinition:
    source = await Source.create(name=name, base_url=base_url, adapter_type=adapter_type)
    return SourceDefinition(
        id=source.id, name=source.name, base_url=source.base_url, adapter_type=adapter_type
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scrapy_collector_and_analyzer_chain(
    monkeypatch: pytest.MonkeyPatch, tortoise_connection
) -> None:
    fixture_path = FIXTURES_DIR / "scrapy" / "ticketmisiones.html"
    html = fixture_path.read_text(encoding="utf-8")

    source = await _source_definition(
        name="Ticket Misiones", base_url="https://ticketmisiones.com", adapter_type="scrapy"
    )

    adapter = ScrapyAdapter()

    async def fake_download(url: str) -> str:
        return html

    monkeypatch.setattr(adapter, "_download", fake_download)

    collector = CollectorAgent(scrapy_adapter=adapter)
    raw_candidates = await collector.execute(source)

    assert len(raw_candidates) == 2
    assert all(candidate.id is not None for candidate in raw_candidates)

    analyzer = AnalyzerAgent(llm_client=FakeLLMClient())
    analyzed = await analyzer.execute(raw_candidates[0])

    assert len(analyzed) == 1
    assert analyzed[0].title == "Feria Artesanal de Invierno"
    assert analyzed[0].confidence == 0.91
    assert analyzed[0].classification_id is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_three_sources_collect_and_dedupe_chain(
    monkeypatch: pytest.MonkeyPatch, tortoise_connection
) -> None:
    """Ticket Misiones (HTML) + Misiones Online (RSS) + Misiones Cuatro (RSS).

    Cubre el criterio de aceptación de la tarea: las 3 fuentes fluyen por el
    Collector y, ante una segunda corrida con el mismo contenido, la
    idempotencia por hash (ahora persistida en `raw_contents`) no deja pasar
    candidatos repetidos.
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
        await _source_definition(
            name="Ticket Misiones", base_url="https://ticketmisiones.com", adapter_type="scrapy"
        ),
        await _source_definition(
            name="Misiones Online",
            base_url="https://misionesonline.net/feed/",
            adapter_type="rss",
        ),
        await _source_definition(
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
    assert len(first_cycle) == 7  # 2 + 3 + 2

    second_cycle = await run_cycle()
    assert second_cycle == []
