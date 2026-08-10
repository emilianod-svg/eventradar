"""Agente Orquestador (sección 8.2).

Responsabilidades futuras: lock global, crear ejecución RUNNING, priorizar
fuentes, procesar en aislamiento, consolidar métricas, ejecutar aprendizaje,
finalizar en COMPLETED/PARTIAL/FAILED liberando el lock incluso ante
excepciones. No debe implementar scraping, prompts, fuzzy matching ni SQL
directo.

Fuera de alcance de esta inicialización (requiere que collector, analyzer,
geo_classifier, evaluator y persistence estén implementados primero).
"""

from __future__ import annotations

from app.domain.entities import AgentRunMetadata


class OrchestratorAgent:
    async def execute(self, data: None = None) -> AgentRunMetadata:
        raise NotImplementedError(
            "OrchestratorAgent.execute: pendiente de implementación (sección 8.2)."
        )
