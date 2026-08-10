"""Agente Recolector (sección 8.4).

Entrada: `SourceDefinition`. Salida: `list[RawContentCandidate]`. Depende de
los adaptadores en `app.sources` (Scrapy/Playwright/Facebook), que también
son stubs en esta inicialización.
"""

from __future__ import annotations

from app.domain.entities import RawContentCandidate, SourceDefinition


class CollectorAgent:
    async def execute(self, data: SourceDefinition) -> list[RawContentCandidate]:
        raise NotImplementedError(
            "CollectorAgent.execute: pendiente de implementación (sección 8.4)."
        )
