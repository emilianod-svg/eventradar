"""Tipos auxiliares para decisiones explicables (secciones 8.7 y 10.4).

Los umbrales de decisión (confianza de extracción, score de duplicados) ya
no viven acá: son campos de `app.config.Settings` (parametrizables por
variable de entorno) para que el Evaluador y el Analizador los lean desde
un único lugar sin necesidad de redeployar código para ajustarlos.
"""

from __future__ import annotations

from app.domain.enums import EvaluationDecisionType

__all__ = [
    "EvaluationDecisionType",
]
