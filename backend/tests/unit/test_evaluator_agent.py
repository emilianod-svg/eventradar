"""Pruebas del Agente Evaluador."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.agents.evaluator import EvaluatorAgent
from app.domain.entities import EventCandidate
from app.domain.enums import EvaluationDecisionType, ProcessingStatus


def _candidate(**overrides: object) -> EventCandidate:
    payload = {
        "is_event": True,
        "confidence": 0.92,
        "source_id": uuid4(),
        "source_url": "https://example.com/evento",
        "title": "Festival del Litoral",
        "venue_name": "Anfiteatro Manuel Antonio Ramirez",
        "address": "Posadas, Misiones",
        "start_at": datetime.now(UTC) + timedelta(days=2),
        "processing_status": ProcessingStatus.GEOLOCATED,
        "latitude": -27.3671,
        "longitude": -55.8961,
    }
    payload.update(overrides)
    return EventCandidate.model_validate(payload)


@pytest.mark.asyncio
async def test_evaluator_accepts_valid_event_without_duplicates() -> None:
    agent = EvaluatorAgent(existing_events=[])

    result = await agent.execute(_candidate())

    assert result.decision == EvaluationDecisionType.ACCEPT
    assert result.reasons == ["passed_validation"]


@pytest.mark.asyncio
async def test_evaluator_reviews_low_confidence_events() -> None:
    agent = EvaluatorAgent(existing_events=[])

    result = await agent.execute(
        _candidate(confidence=0.6, processing_status=ProcessingStatus.PENDING_REVIEW)
    )

    assert result.decision == EvaluationDecisionType.REVIEW
    assert "low_confidence_requires_review" in result.reasons


@pytest.mark.asyncio
async def test_evaluator_merges_high_similarity_duplicate() -> None:
    duplicate_id = uuid4()
    existing = {
        "id": duplicate_id,
        "title": "Festival del Litoral",
        "venue_name": "Anfiteatro Manuel Antonio Ramirez",
        "address": "Posadas, Misiones",
        "start_at": datetime.now(UTC) + timedelta(days=2),
        "latitude": -27.3671,
        "longitude": -55.8961,
    }
    agent = EvaluatorAgent(existing_events=[existing])

    result = await agent.execute(_candidate())

    assert result.decision == EvaluationDecisionType.MERGE
    assert result.duplicate_of == duplicate_id
    assert result.score is not None and result.score >= 0.90


@pytest.mark.asyncio
async def test_evaluator_reviews_high_similarity_but_incompatible_date() -> None:
    duplicate_id = uuid4()
    existing = {
        "id": duplicate_id,
        "title": "Festival del Litoral",
        "venue_name": "Anfiteatro Manuel Antonio Ramirez",
        "address": "Posadas, Misiones",
        "start_at": datetime.now(UTC) + timedelta(days=5),
        "latitude": -27.3671,
        "longitude": -55.8961,
    }
    agent = EvaluatorAgent(existing_events=[existing])

    result = await agent.execute(_candidate(start_at=datetime.now(UTC) + timedelta(days=2)))

    assert result.decision == EvaluationDecisionType.REVIEW
    assert result.duplicate_of == duplicate_id


@pytest.mark.asyncio
async def test_evaluator_accepts_moderate_similarity_as_non_duplicate() -> None:
    existing = {
        "id": uuid4(),
        "title": "Festival de Verano",
        "venue_name": "Plaza 9 de Julio",
        "address": "Posadas, Misiones",
        "start_at": datetime.now(UTC) + timedelta(days=2),
    }
    agent = EvaluatorAgent(existing_events=[existing])

    result = await agent.execute(
        _candidate(title="Noche de Salsa", venue_name="Casa de la Cultura")
    )

    assert result.decision == EvaluationDecisionType.ACCEPT


@pytest.mark.asyncio
async def test_evaluator_rejects_events_outside_radius() -> None:
    agent = EvaluatorAgent(
        existing_events=[],
        base_latitude=-27.3671,
        base_longitude=-55.8961,
        search_radius_km=1.0,
    )

    result = await agent.execute(_candidate(latitude=-26.0, longitude=-54.0))

    assert result.decision == EvaluationDecisionType.REJECT
    assert any(reason.startswith("outside_radius_") for reason in result.reasons)
