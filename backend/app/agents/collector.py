"""Agente Recolector (sección 8.4).

Entrada: `SourceDefinition`. Salida: `list[RawContentCandidate]`. Depende de
los adaptadores en `app.sources` (Scrapy/Playwright/Facebook), que también
son stubs en esta inicialización.
"""

from __future__ import annotations

from app.sources.scrapy_adapter import ScrapyAdapter
from app.domain.entities import RawContentCandidate, SourceDefinition


class CollectorAgent:
    def __init__(self, scrapy_adapter: ScrapyAdapter | None = None) -> None:
        self._scrapy_adapter = scrapy_adapter or ScrapyAdapter()

    async def execute(self, data: SourceDefinition) -> list[RawContentCandidate]:
        adapter_type = data.adapter_type.strip().lower()
        if adapter_type in {"scrapy", "scrapy_static", "static", "html"}:
            return await self._scrapy_adapter.fetch(data)
        raise NotImplementedError(
            f"CollectorAgent.execute: adaptador '{data.adapter_type}' aún no implementado."
        )
