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


class BayesianReliabilityScorer:
    """Suavizado bayesiano de la sección 14.1.

    `acceptance_score` usa un prior equivalente a 2 aceptados / 4 procesados
    para que una fuente nueva o con pocas observaciones no quede en 0.0 o
    1.0 por un puñado de resultados.
    """

    def compute(
        self, *, previous_score: float, accepted: int, processed: int, extraction_quality: float
    ) -> float:
        acceptance_score = (accepted + 2) / (processed + 4)
        new_score = previous_score * 0.40 + acceptance_score * 0.40 + extraction_quality * 0.20
        return min(1.0, max(0.0, new_score))


def get_reliability_scorer() -> ReliabilityScorer:
    return BayesianReliabilityScorer()
