"""Interfaz común de adaptadores de fuente (sección 8.4 y 6.2 del plan)."""

from __future__ import annotations

from typing import Protocol

from app.domain.entities import RawContentCandidate, SourceDefinition


class SourceAdapter(Protocol):
    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]: ...
