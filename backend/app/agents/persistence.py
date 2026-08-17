"""Agente de Persistencia y Aprendizaje (sección 8.8 y 14).

Persiste decisiones transaccionalmente, vincula eventos con todas sus
fuentes, actualiza confiabilidad con suavizado bayesiano y registra
`source_score_history`.

Una misma instancia debe reutilizarse para todo un ciclo del Orquestador:
acumula estadísticas por fuente en memoria (`_stats`) mientras procesa cada
`EvaluationResult`, y `update_learning()` las consume una sola vez al cierre
del ciclo — la fórmula de la sección 14.1 es agregada por fuente/ejecución,
no por evento individual.

Simplificación deliberada de MVP en `_merge`: solo completa campos vacíos
del evento existente con valores no contradictorios del candidato (sección
10.5). No implementa la regla completa "el registro de mayor confiabilidad
aporta los campos principales" (comparación campo por campo por
confiabilidad de fuente) — queda para una iteración posterior si la demo lo
exige.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.domain.entities import EvaluationResult, EventCandidate
from app.domain.enums import EvaluationDecisionType, EventStatus
from app.models.evaluation_decision import EvaluationDecision
from app.models.event import Event
from app.models.event_change_history import EventChangeHistory
from app.models.event_source import EventSource
from app.models.review_item import ReviewItem
from app.models.source import Source
from app.models.source_score_history import SourceScoreHistory
from app.services.scoring.base import ReliabilityScorer, get_reliability_scorer

logger = logging.getLogger(__name__)

_MERGEABLE_FIELDS = (
    "description",
    "end_at",
    "recurrence_text",
    "address",
    "latitude",
    "longitude",
    "price_text",
    "category",
)


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return normalized


def _decimal(value: float | None, places: int) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, places)))


@dataclass
class _SourceStats:
    processed: int = 0
    accepted: int = 0
    rejected: int = 0
    quality_sum: float = 0.0
    quality_count: int = 0


class PersistenceAgent:
    def __init__(
        self,
        execution_id: UUID | None = None,
        reliability_scorer: ReliabilityScorer | None = None,
    ) -> None:
        self._execution_id = execution_id
        self._reliability_scorer = reliability_scorer or get_reliability_scorer()
        self._stats: dict[UUID, _SourceStats] = {}

    async def execute(self, data: EvaluationResult) -> Event | None:
        """Devuelve el `Event` creado/actualizado en ACCEPT/MERGE, o `None`
        en REVIEW/REJECT — el Orquestador lo usa para mantener fresco el
        universo de deduplicación del Evaluador dentro del mismo ciclo
        (ver `EvaluatorAgent.register_existing_event`)."""
        candidate = data.event
        if candidate.classification_id is None:
            raise ValueError(
                "PersistenceAgent.execute: el EventCandidate no tiene classification_id. "
                "El Analizador debe persistir la Classification antes de que el Evaluador "
                "y el Persistidor procesen el candidato."
            )

        decision_data = await self._coerce_persistable_result(data)
        self._record_stats(decision_data)

        async with in_transaction():
            if decision_data.decision == EvaluationDecisionType.ACCEPT:
                return await self._accept(decision_data)
            if decision_data.decision == EvaluationDecisionType.MERGE:
                return await self._merge(decision_data)
            if decision_data.decision == EvaluationDecisionType.REVIEW:
                await self._review(decision_data)
                return None
            if decision_data.decision == EvaluationDecisionType.REJECT:
                await self._reject(decision_data)
                return None
            raise ValueError(
                f"PersistenceAgent.execute: decisión desconocida '{decision_data.decision}'."
            )

    async def _coerce_persistable_result(self, data: EvaluationResult) -> EvaluationResult:
        if data.decision == EvaluationDecisionType.MERGE:
            if data.duplicate_of is None:
                return self._downgrade_to_review(
                    data,
                    "merge_without_duplicate_target",
                )
            if await Event.get_or_none(id=data.duplicate_of) is None:
                return self._downgrade_to_review(
                    data,
                    "duplicate_event_not_found",
                )
            return data

        if data.decision == EvaluationDecisionType.ACCEPT and not self._can_create_event(data.event):
            return self._downgrade_to_review(
                data,
                "accept_without_persistable_fields",
            )

        return data

    def _downgrade_to_review(self, data: EvaluationResult, reason: str) -> EvaluationResult:
        logger.warning(
            "persistence_result_downgraded",
            extra={
                "classification_id": str(data.event.classification_id)
                if data.event.classification_id is not None
                else None,
                "reason": reason,
                "original_decision": data.decision,
            },
        )
        return data.model_copy(
            update={
                "decision": EvaluationDecisionType.REVIEW,
                "reasons": list(data.reasons) + [reason],
            }
        )

    def _can_create_event(self, candidate: EventCandidate) -> bool:
        return bool(candidate.title and candidate.venue_name and candidate.start_at)

    def _record_stats(self, data: EvaluationResult) -> None:
        candidate = data.event
        if candidate.source_id is None:
            return
        stats = self._stats.setdefault(candidate.source_id, _SourceStats())
        stats.processed += 1
        if data.decision in (EvaluationDecisionType.ACCEPT, EvaluationDecisionType.MERGE):
            stats.accepted += 1
            stats.quality_sum += candidate.confidence
            stats.quality_count += 1
        elif data.decision == EvaluationDecisionType.REJECT:
            stats.rejected += 1

    async def _accept(self, data: EvaluationResult) -> Event:
        candidate = data.event
        event = await self._create_event(candidate)
        await EventSource.get_or_create(
            event=event,
            source_id=candidate.source_id,
            source_url=candidate.source_url or "",
            defaults={"is_primary": True},
        )
        await self._create_decision(data, duplicate_of_id=None)
        return event

    async def _merge(self, data: EvaluationResult) -> Event:
        candidate = data.event
        event = await Event.get(id=data.duplicate_of)
        await self._fill_empty_fields(event, candidate)
        await EventSource.get_or_create(
            event=event,
            source_id=candidate.source_id,
            source_url=candidate.source_url or "",
            defaults={"is_primary": False},
        )
        await self._create_decision(data, duplicate_of_id=data.duplicate_of)
        return event

    async def _review(self, data: EvaluationResult) -> None:
        await self._create_decision(data, duplicate_of_id=data.duplicate_of)
        await ReviewItem.create(
            classification_id=data.event.classification_id,
            reason="; ".join(data.reasons) or None,
        )

    async def _reject(self, data: EvaluationResult) -> None:
        await self._create_decision(data, duplicate_of_id=None)

    async def _create_decision(
        self, data: EvaluationResult, *, duplicate_of_id: UUID | None
    ) -> EvaluationDecision:
        return await EvaluationDecision.create(
            classification_id=data.event.classification_id,
            decision=data.decision,
            reasons=data.reasons,
            duplicate_of_id=duplicate_of_id,
            score=_decimal(data.score, 3),
        )

    async def _create_event(self, candidate: EventCandidate) -> Event:
        assert candidate.title is not None
        assert candidate.venue_name is not None
        assert candidate.start_at is not None
        slug = await self._unique_slug(candidate.title, candidate.start_at)
        return await Event.create(
            title=candidate.title,
            slug=slug,
            description=candidate.description,
            start_at=candidate.start_at,
            end_at=candidate.end_at,
            recurrence_text=candidate.recurrence_text,
            venue_name=candidate.venue_name,
            address=candidate.address,
            latitude=_decimal(candidate.latitude, 6),
            longitude=_decimal(candidate.longitude, 6),
            price_text=candidate.price_text,
            category=candidate.category,
            quality_score=_decimal(candidate.confidence, 3),
            status=EventStatus.ACTIVE,
        )

    async def _fill_empty_fields(self, event: Event, candidate: EventCandidate) -> None:
        changed = False
        for field_name in _MERGEABLE_FIELDS:
            new_value = getattr(candidate, field_name, None)
            old_value = getattr(event, field_name)
            if new_value in (None, "") or old_value not in (None, ""):
                continue
            if field_name in ("latitude", "longitude"):
                new_value = _decimal(new_value, 6)
            setattr(event, field_name, new_value)
            changed = True
            await EventChangeHistory.create(
                event=event,
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value),
                source_id=candidate.source_id,
                execution_id=self._execution_id,
            )
        if changed:
            event.status = EventStatus.UPDATED
            await event.save()

    async def _unique_slug(self, title: str, start_at: datetime) -> str:
        base = _slugify(title) or "evento"
        date_suffix = start_at.strftime("%Y%m%d")
        candidate_slug = f"{base}-{date_suffix}"
        slug = candidate_slug
        suffix = 1
        while await Event.filter(slug=slug).exists():
            suffix += 1
            slug = f"{candidate_slug}-{suffix}"
        return slug

    async def update_learning(self) -> None:
        """Cierre del ciclo de aprendizaje (sección 14): recalcula
        `reliability_score` por fuente con suavizado bayesiano y guarda el
        historial. Debe llamarse una sola vez al final del ciclo
        (Orquestador), no por cada evento — la fórmula es agregada.
        """
        for source_id, stats in self._stats.items():
            source = await Source.get_or_none(id=source_id)
            if source is None:
                continue
            avg_quality = stats.quality_sum / stats.quality_count if stats.quality_count else 0.0
            previous_score = float(source.reliability_score)
            new_score = self._reliability_scorer.compute(
                previous_score=previous_score,
                accepted=stats.accepted,
                processed=stats.processed,
                extraction_quality=avg_quality,
            )
            async with in_transaction():
                await SourceScoreHistory.create(
                    source=source,
                    execution_id=self._execution_id,
                    previous_score=_decimal(previous_score, 3),
                    new_score=_decimal(new_score, 3),
                    processed_count=stats.processed,
                    accepted_count=stats.accepted,
                    rejected_count=stats.rejected,
                    avg_extraction_quality=_decimal(avg_quality, 3),
                )
                source.reliability_score = Decimal(str(round(new_score, 3)))
                await source.save()

    async def archive_past_events(self) -> int:
        """Archivado de eventos pasados (responsabilidad de 8.8; sin día
        propio en el cronograma 10/08-20/08, se ejecuta como paso final de
        cada ciclo del Orquestador). Usa `end_at` cuando existe; si no,
        `start_at` (un evento sin `end_at` se considera terminado el mismo
        día de inicio, ya que no hay forma de saber cuánto dura)."""
        now = datetime.now(UTC)
        return await Event.filter(
            Q(status__in=[EventStatus.ACTIVE, EventStatus.UPDATED])
            & (Q(end_at__lt=now) | (Q(end_at__isnull=True) & Q(start_at__lt=now)))
        ).update(status=EventStatus.ARCHIVED)
