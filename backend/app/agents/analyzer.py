"""Agente Analizador (sección 8.5 y 9).

Combina texto web + OCR, llama al LLM (familia Llama, proveedor pendiente de
decisión — ver `app/services/llm`), valida el JSON contra el schema y aplica
las reglas de confianza (>=0.70 continuar, 0.50-0.69 revisión, <0.50
rechazar).
"""

from __future__ import annotations

from app.domain.entities import EventCandidate, RawContentCandidate


class AnalyzerAgent:
    async def execute(self, data: RawContentCandidate) -> list[EventCandidate]:
        raise NotImplementedError(
            "AnalyzerAgent.execute: pendiente de implementación (sección 8.5)."
        )
