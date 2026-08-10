"""Agente Clasificador Geográfico (sección 8.6).

Orden de resolución: coordenadas explícitas -> dirección completa ->
`lugar + Posadas + Misiones + Argentina` -> caché de venues -> revisión
manual. Depende de `app.services.geocoding` (Nominatim), stub en esta
inicialización.
"""

from __future__ import annotations

from app.domain.entities import EventCandidate


class GeoClassifierAgent:
    async def execute(self, data: EventCandidate) -> EventCandidate:
        raise NotImplementedError(
            "GeoClassifierAgent.execute: pendiente de implementación (sección 8.6)."
        )
