"""Agente Descubridor de Fuentes (sección 8.3).

En el MVP no descubre URLs nuevas: selecciona fuentes activas priorizando
`confiabilidad*0.70 + antiguedad_sin_revision*0.20 + bono_fuente_nueva*0.10`.
Pendiente de implementación en esta inicialización.
"""

from __future__ import annotations

from app.domain.entities import SourceDefinition


class SourceDiscovererAgent:
    async def execute(self, data: int) -> list[SourceDefinition]:
        raise NotImplementedError(
            "SourceDiscovererAgent.execute: pendiente de implementación (sección 8.3)."
        )
