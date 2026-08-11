"""Tipos auxiliares para decisiones explicables (secciones 8.7 y 10.4)."""

from __future__ import annotations

from app.domain.enums import EvaluationDecisionType

# Umbrales consolidados en el plan (sección 2.3 y 10.4). Se centralizan aquí
# para que el Evaluador y el Analizador los importen desde un único lugar.
CONFIDENCE_ACCEPT_THRESHOLD = 0.70
CONFIDENCE_REVIEW_THRESHOLD = 0.50

DUPLICATE_CANDIDATE_THRESHOLD = 0.50
DUPLICATE_REVIEW_THRESHOLD = 0.75
DUPLICATE_AUTO_MERGE_THRESHOLD = 0.90

__all__ = [
    "EvaluationDecisionType",
    "CONFIDENCE_ACCEPT_THRESHOLD",
    "CONFIDENCE_REVIEW_THRESHOLD",
    "DUPLICATE_CANDIDATE_THRESHOLD",
    "DUPLICATE_REVIEW_THRESHOLD",
    "DUPLICATE_AUTO_MERGE_THRESHOLD",
]
