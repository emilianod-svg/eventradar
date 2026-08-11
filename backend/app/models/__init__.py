"""Modelos Tortoise ORM (sección 11 del plan — Modelo de datos).

Este módulo se referencia como `app.models` en `TORTOISE_ORM["apps"]["models"]`
(ver `app/config.py`) para que Tortoise y Aerich descubran las clases.
"""

from app.models.classification import Classification
from app.models.evaluation_decision import EvaluationDecision
from app.models.event import Event
from app.models.event_change_history import EventChangeHistory
from app.models.event_source import EventSource
from app.models.execution import Execution
from app.models.execution_source import ExecutionSource
from app.models.raw_content import RawContent
from app.models.review_item import ReviewItem
from app.models.source import Source
from app.models.source_score_history import SourceScoreHistory

__all__ = [
    "Classification",
    "Event",
    "EventChangeHistory",
    "EventSource",
    "EvaluationDecision",
    "Execution",
    "ExecutionSource",
    "RawContent",
    "ReviewItem",
    "Source",
    "SourceScoreHistory",
]
