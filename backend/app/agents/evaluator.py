"""Agente Evaluador (sección 8.7).

Produce una decisión explicable: ACCEPT, REJECT, REVIEW o MERGE. Usa
RapidFuzz/Levenshtein (vía `app.services.matching`) para deduplicación; el
LLM no participa en esta etapa.
"""

from __future__ import annotations

from app.domain.entities import EvaluationResult, EventCandidate


class EvaluatorAgent:
    async def execute(self, data: EventCandidate) -> EvaluationResult:
        raise NotImplementedError(
            "EvaluatorAgent.execute: pendiente de implementación (sección 8.7)."
        )
