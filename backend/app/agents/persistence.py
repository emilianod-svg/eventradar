"""Agente de Persistencia y Aprendizaje (sección 8.8 y 14).

Persiste decisiones transaccionalmente, vincula eventos con todas sus
fuentes, actualiza confiabilidad con suavizado bayesiano y registra
`source_score_history`.
"""

from __future__ import annotations

from app.domain.entities import EvaluationResult


class PersistenceAgent:
    async def execute(self, data: EvaluationResult) -> None:
        raise NotImplementedError(
            "PersistenceAgent.execute: pendiente de implementación (sección 8.8)."
        )
