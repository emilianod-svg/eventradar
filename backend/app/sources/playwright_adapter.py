"""Adaptador Playwright para contenido dinámico (sección 2.2, funcionalidad P1).

Se usa como fallback cuando el HTML estático no contiene los datos
necesarios (ver tabla de política por adaptador, sección 8.4).
"""

from __future__ import annotations

from app.domain.entities import RawContentCandidate, SourceDefinition


class PlaywrightAdapter:
    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        raise NotImplementedError(
            "PlaywrightAdapter.fetch: pendiente de implementación (funcionalidad P1)."
        )
