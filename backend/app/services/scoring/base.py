"""Interfaz de scoring de confiabilidad (sección 14.1 del plan).

`new_score = previous*0.40 + acceptance_score*0.40 + extraction_quality*0.20`,
con suavizado bayesiano `acceptance_score = (accepted+2)/(processed+4)`.
"""

from __future__ import annotations

from typing import Protocol


class ReliabilityScorer(Protocol):
    def compute(
        self, *, previous_score: float, accepted: int, processed: int, extraction_quality: float
    ) -> float: ...


class NotImplementedReliabilityScorer:
    def compute(
        self, *, previous_score: float, accepted: int, processed: int, extraction_quality: float
    ) -> float:
        raise NotImplementedError(
            "ReliabilityScorer.compute: pendiente de implementación (sección 14.1)."
        )


def get_reliability_scorer() -> ReliabilityScorer:
    return NotImplementedReliabilityScorer()
