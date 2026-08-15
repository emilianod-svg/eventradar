"""PersistenceAgent: decisiones transaccionales + aprendizaje (sección 8.8/14)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.agents.persistence import PersistenceAgent
from app.domain.entities import EvaluationResult, EventCandidate
from app.domain.enums import EvaluationDecisionType, EventStatus
from app.models.classification import Classification
from app.models.evaluation_decision import EvaluationDecision
from app.models.event import Event
from app.models.event_change_history import EventChangeHistory
from app.models.event_source import EventSource
from app.models.raw_content import RawContent
from app.models.review_item import ReviewItem
from app.models.source import Source


async def _make_classification(source: Source, *, content_hash: str = "hash") -> Classification:
    raw_content = await RawContent.create(
        source_id=source.id,
        url="https://example.com/nota",
        raw_text="texto",
        fetched_at=datetime.now(UTC),
        content_hash=content_hash,
    )
    return await Classification.create(
        raw_content_id=raw_content.id,
        is_event=True,
        confidence=0.9,
        extracted_fields={},
    )


def _candidate(source: Source, classification_id, **overrides: object) -> EventCandidate:
    payload = {
        "is_event": True,
        "confidence": 0.85,
        "classification_id": classification_id,
        "source_id": source.id,
        "source_url": "https://example.com/nota",
        "title": "Festival del Litoral",
        "venue_name": "Anfiteatro Manuel Antonio Ramirez",
        "address": "Posadas, Misiones",
        "start_at": datetime.now(UTC) + timedelta(days=2),
    }
    payload.update(overrides)
    return EventCandidate.model_validate(payload)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_execute_rejects_candidate_without_classification_id(tortoise_connection) -> None:
    source = await Source.create(name="s", base_url="https://s", adapter_type="rss")
    candidate = _candidate(source, classification_id=None)
    result = EvaluationResult(decision=EvaluationDecisionType.ACCEPT, score=0.9, event=candidate)
    agent = PersistenceAgent()

    with pytest.raises(ValueError):
        await agent.execute(result)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_creates_event_and_primary_source(tortoise_connection) -> None:
    source = await Source.create(name="s", base_url="https://s", adapter_type="rss")
    classification = await _make_classification(source)
    candidate = _candidate(source, classification.id)
    result = EvaluationResult(
        decision=EvaluationDecisionType.ACCEPT,
        reasons=["passed_validation"],
        score=0.85,
        event=candidate,
    )
    agent = PersistenceAgent()

    await agent.execute(result)

    events = await Event.all()
    assert len(events) == 1
    assert events[0].title == "Festival del Litoral"
    assert events[0].status == EventStatus.ACTIVE

    sources = await EventSource.filter(event=events[0])
    assert len(sources) == 1
    assert sources[0].is_primary is True

    decisions = await EvaluationDecision.filter(classification_id=classification.id)
    assert len(decisions) == 1
    assert decisions[0].decision == EvaluationDecisionType.ACCEPT


@pytest.mark.integration
@pytest.mark.asyncio
async def test_merge_fills_empty_fields_and_links_secondary_source(tortoise_connection) -> None:
    source_b = await Source.create(name="b", base_url="https://b", adapter_type="rss")
    existing = await Event.create(
        title="Festival del Litoral",
        slug="festival-del-litoral-existing",
        start_at=datetime.now(UTC) + timedelta(days=2),
        venue_name="Anfiteatro Manuel Antonio Ramirez",
        address=None,
        price_text=None,
    )
    classification = await _make_classification(source_b, content_hash="hash-2")
    candidate = _candidate(
        source_b,
        classification.id,
        address="Posadas, Misiones",
        price_text="Entrada libre",
        source_url="https://b/nota",
    )
    result = EvaluationResult(
        decision=EvaluationDecisionType.MERGE,
        duplicate_of=existing.id,
        score=0.93,
        event=candidate,
    )
    agent = PersistenceAgent()

    await agent.execute(result)

    await existing.refresh_from_db()
    assert existing.address == "Posadas, Misiones"
    assert existing.price_text == "Entrada libre"
    assert existing.status == EventStatus.UPDATED

    changes = await EventChangeHistory.filter(event=existing)
    changed_fields = {c.field_name for c in changes}
    assert {"address", "price_text"} <= changed_fields

    sources = await EventSource.filter(event=existing)
    assert len(sources) == 1
    assert sources[0].is_primary is False
    assert sources[0].source_id == source_b.id

    decisions = await EvaluationDecision.filter(classification_id=classification.id)
    assert decisions[0].decision == EvaluationDecisionType.MERGE
    assert decisions[0].duplicate_of_id == existing.id

    # Retry de la misma ejecución: no debe duplicar la fila event_sources.
    await agent.execute(result)
    assert await EventSource.filter(event=existing).count() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_creates_review_item_without_event(tortoise_connection) -> None:
    source = await Source.create(name="s", base_url="https://s", adapter_type="rss")
    classification = await _make_classification(source)
    candidate = _candidate(source, classification.id, confidence=0.6)
    result = EvaluationResult(
        decision=EvaluationDecisionType.REVIEW,
        reasons=["low_confidence_requires_review"],
        score=0.6,
        event=candidate,
    )
    agent = PersistenceAgent()

    await agent.execute(result)

    assert await Event.all().count() == 0
    review_items = await ReviewItem.filter(classification_id=classification.id)
    assert len(review_items) == 1
    assert review_items[0].reason == "low_confidence_requires_review"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_only_creates_decision(tortoise_connection) -> None:
    source = await Source.create(name="s", base_url="https://s", adapter_type="rss")
    classification = await _make_classification(source)
    candidate = _candidate(source, classification.id, is_event=False)
    result = EvaluationResult(
        decision=EvaluationDecisionType.REJECT,
        reasons=["publication_is_not_an_event"],
        score=0.2,
        event=candidate,
    )
    agent = PersistenceAgent()

    await agent.execute(result)

    assert await Event.all().count() == 0
    assert await ReviewItem.all().count() == 0
    decisions = await EvaluationDecision.filter(classification_id=classification.id)
    assert decisions[0].decision == EvaluationDecisionType.REJECT


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_learning_applies_bayesian_formula_and_records_history(
    tortoise_connection,
) -> None:
    source = await Source.create(
        name="s", base_url="https://s", adapter_type="rss", reliability_score=0.5
    )
    agent = PersistenceAgent()

    accepted_classification = await _make_classification(source, content_hash="h1")
    await agent.execute(
        EvaluationResult(
            decision=EvaluationDecisionType.ACCEPT,
            score=0.9,
            event=_candidate(source, accepted_classification.id, confidence=0.9),
        )
    )
    rejected_classification = await _make_classification(source, content_hash="h2")
    await agent.execute(
        EvaluationResult(
            decision=EvaluationDecisionType.REJECT,
            score=0.2,
            event=_candidate(source, rejected_classification.id, is_event=False),
        )
    )

    await agent.update_learning()

    await source.refresh_from_db()
    acceptance_score = (1 + 2) / (2 + 4)
    expected = 0.5 * 0.40 + acceptance_score * 0.40 + 0.9 * 0.20
    assert float(source.reliability_score) == pytest.approx(expected, abs=1e-3)

    history = await source.score_history.all()
    assert len(history) == 1
    assert history[0].processed_count == 2
    assert history[0].accepted_count == 1
    assert history[0].rejected_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_archive_past_events_marks_expired_events_only(tortoise_connection) -> None:
    past_no_end = await Event.create(
        title="Pasado sin fin",
        slug="pasado-sin-fin",
        start_at=datetime.now(UTC) - timedelta(days=1),
        venue_name="X",
    )
    past_with_future_end = await Event.create(
        title="Pasado con fin futuro",
        slug="pasado-con-fin-futuro",
        start_at=datetime.now(UTC) - timedelta(hours=2),
        end_at=datetime.now(UTC) + timedelta(hours=2),
        venue_name="X",
    )
    future_event = await Event.create(
        title="Futuro",
        slug="futuro",
        start_at=datetime.now(UTC) + timedelta(days=1),
        venue_name="X",
    )
    agent = PersistenceAgent()

    archived_count = await agent.archive_past_events()

    assert archived_count == 1
    await past_no_end.refresh_from_db()
    await past_with_future_end.refresh_from_db()
    await future_event.refresh_from_db()
    assert past_no_end.status == EventStatus.ARCHIVED
    assert past_with_future_end.status == EventStatus.ACTIVE
    assert future_event.status == EventStatus.ACTIVE
