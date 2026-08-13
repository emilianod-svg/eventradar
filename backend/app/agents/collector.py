"""Agente Recolector (sección 8.4).

Entrada: `SourceDefinition`. Salida: `list[RawContentCandidate]`. Depende de
los adaptadores en `app.sources` (Scrapy/Playwright/Facebook), que también
son stubs en esta inicialización.
"""

from __future__ import annotations

from app.domain.entities import RawContentCandidate, SourceDefinition
from app.sources.rss_adapter import RssAdapter
from app.sources.scrapy_adapter import ScrapyAdapter


class CollectorAgent:
    def __init__(
        self,
        scrapy_adapter: ScrapyAdapter | None = None,
        rss_adapter: RssAdapter | None = None,
    ) -> None:
        self._scrapy_adapter = scrapy_adapter or ScrapyAdapter()
        self._rss_adapter = rss_adapter or RssAdapter()

    async def execute(self, data: SourceDefinition) -> list[RawContentCandidate]:
        adapter_type = data.adapter_type.strip().lower()
        if adapter_type in {"scrapy", "scrapy_static", "static", "html"}:
            return await self._scrapy_adapter.fetch(data)
        if adapter_type in {"rss", "rss_feed"}:
            return await self._rss_adapter.fetch(data)
        raise NotImplementedError(
            f"CollectorAgent.execute: adaptador '{data.adapter_type}' aún no implementado."
        )
