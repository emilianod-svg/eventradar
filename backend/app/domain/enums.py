"""Enumeraciones de dominio (sección 11.3 y 8.7 del plan)."""

from enum import StrEnum


class ProcessingStatus(StrEnum):
    """Estados por los que pasa un contenido/evento durante el ciclo."""

    COLLECTED = "COLLECTED"
    ANALYZED = "ANALYZED"
    PENDING_REVIEW = "PENDING_REVIEW"
    GEOLOCATED = "GEOLOCATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    MERGED = "MERGED"
    FAILED = "FAILED"


class EventStatus(StrEnum):
    """Estado público de un evento persistido."""

    ACTIVE = "ACTIVE"
    UPDATED = "UPDATED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class EvaluationDecisionType(StrEnum):
    """Decisión explicable que produce el Agente Evaluador (sección 8.7)."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    REVIEW = "REVIEW"
    MERGE = "MERGE"


class ExecutionStatus(StrEnum):
    """Estado de una ejecución del ciclo completo (sección 6.3)."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SourceAdapterType(StrEnum):
    """Tipo de adaptador de recolección (sección 8.4)."""

    SCRAPY_STATIC = "SCRAPY_STATIC"
    PLAYWRIGHT_DYNAMIC = "PLAYWRIGHT_DYNAMIC"
    RSS_FEED = "RSS_FEED"
    FACEBOOK = "FACEBOOK"
