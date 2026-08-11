"""Adaptador Scrapy para fuentes web estáticas (sección 8.4).

Fuentes previstas: Ticket Misiones, Misiones Online, Misiones Cuatro. Pendiente
de implementación: parsers por fuente, fixtures HTML versionadas (sección
18.2) y respeto de `robots.txt`/rate limits por dominio (sección 16.3).
"""

from __future__ import annotations

from app.domain.entities import RawContentCandidate, SourceDefinition


class ScrapyAdapter:
    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        raise NotImplementedError("ScrapyAdapter.fetch: pendiente de implementación (sección 8.4).")
