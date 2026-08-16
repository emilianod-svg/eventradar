"""Pruebas del Agente Evaluador."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.agents.evaluator import EvaluatorAgent
from app.agents.geo_classifier import GeoClassificationResult
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


class CountingDuplicateMatcher:
    def __init__(self, score_value: float = 0.95) -> None:
        self.score_value = score_value
        self.calls: list[tuple[dict, dict]] = []

    def score(self, *, candidate: dict, existing: dict) -> float:
        self.calls.append((candidate, existing))
        return self.score_value


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
async def test_evaluator_rejects_missing_required_fields() -> None:
    agent = EvaluatorAgent(existing_events=[])

    result = await agent.execute(_candidate(title="", venue_name=" ", address="", confidence=0.9))

    assert result.decision == EvaluationDecisionType.REJECT
    assert result.reasons == [
        "missing_title",
        "missing_venue_name",
    ]


@pytest.mark.asyncio
async def test_evaluator_accepts_event_without_address() -> None:
    agent = EvaluatorAgent(existing_events=[])

    result = await agent.execute(_candidate(address=None))

    assert result.decision == EvaluationDecisionType.ACCEPT


@pytest.mark.asyncio
async def test_evaluator_rejects_unpermitted_source_url() -> None:
    agent = EvaluatorAgent(existing_events=[])

    result = await agent.execute(_candidate(source_url="ftp://example.com/evento"))

    assert result.decision == EvaluationDecisionType.REJECT
    assert "source_url_not_permitted" in result.reasons


@pytest.mark.asyncio
async def test_evaluator_rejects_inaccessible_source_url() -> None:
    agent = EvaluatorAgent(existing_events=[], source_url_checker=lambda _: False)

    result = await agent.execute(_candidate())

    assert result.decision == EvaluationDecisionType.REJECT
    assert result.reasons == ["source_url_not_accessible"]


@pytest.mark.asyncio
async def test_evaluator_rejects_events_beyond_future_horizon() -> None:
    agent = EvaluatorAgent(existing_events=[], max_future_days=30)

    result = await agent.execute(_candidate(start_at=datetime.now(UTC) + timedelta(days=31)))

    assert result.decision == EvaluationDecisionType.REJECT
    assert result.reasons == ["event_date_beyond_horizon"]


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
async def test_evaluator_prunes_duplicate_candidates_before_scoring() -> None:
    duplicate_id = uuid4()
    matcher = CountingDuplicateMatcher()
    agent = EvaluatorAgent(
        existing_events=[
            {
                "id": uuid4(),
                "title": "Otro evento",
                "venue_name": "Lugar lejano",
                "address": "Otra ciudad",
                "start_at": datetime.now(UTC) + timedelta(days=10),
            },
            {
                "id": duplicate_id,
                "title": "Festival del Litoral",
                "venue_name": "Anfiteatro Manuel Antonio Ramirez",
                "address": "Posadas, Misiones",
                "start_at": datetime.now(UTC) + timedelta(days=2),
                "latitude": -27.3671,
                "longitude": -55.8961,
            },
        ],
        duplicate_matcher=matcher,
    )

    result = await agent.execute(_candidate())

    assert result.decision == EvaluationDecisionType.MERGE
    assert result.duplicate_of == duplicate_id
    assert len(matcher.calls) == 1


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


@pytest.mark.asyncio
async def test_register_existing_event_makes_it_visible_for_later_candidates() -> None:
    """El Orquestador llama a esto tras persistir un ACCEPT/MERGE, para que
    otra fuente del mismo ciclo publicando el mismo evento sí lo detecte
    como duplicado (sección 10.2)."""
    agent = EvaluatorAgent(existing_events=[])
    accepted = await agent.execute(_candidate())
    assert accepted.decision == EvaluationDecisionType.ACCEPT

    agent.register_existing_event(
        {
            "id": uuid4(),
            "title": "Festival del Litoral",
            "venue_name": "Anfiteatro Manuel Antonio Ramirez",
            "address": "Posadas, Misiones",
            "start_at": datetime.now(UTC) + timedelta(days=2),
            "latitude": -27.3671,
            "longitude": -55.8961,
        }
    )

    duplicate_from_another_source = await agent.execute(_candidate(source_id=uuid4()))

    assert duplicate_from_another_source.decision == EvaluationDecisionType.MERGE


@pytest.mark.asyncio
async def test_evaluator_evaluates_labeled_dataset_and_generates_report() -> None:
    dataset = [
        {
            "id": "case-1",
            "candidate": {
                "is_event": True,
                "confidence": 0.9,
                "title": "Festival del Litoral",
                "venue_name": "Anfiteatro Manuel Antonio Ramirez",
                "address": "Posadas, Misiones",
                "source_url": "https://example.com/1",
            },
            "expected": {"valid": True, "decision": "accepted", "provider": "catalog"},
        },
        {
            "id": "case-2",
            "candidate": {
                "is_event": True,
                "confidence": 0.6,
                "title": "Sin ubicación",
                "venue_name": None,
                "address": None,
                "source_url": "https://example.com/2",
            },
            "expected": {"valid": False, "decision": "manual_review"},
        },
    ]

    async def classifier(candidate: EventCandidate) -> GeoClassificationResult:
        if candidate.title == "Festival del Litoral":
            return GeoClassificationResult(
                original_text="Posadas, Misiones",
                normalized_text="posadas misiones",
                decision="accepted",
                confidence=0.96,
                latitude=-27.3671,
                longitude=-55.8961,
                city="Posadas",
                state="Misiones",
                country_code="ar",
                matched_catalog_entry="Posadas",
                provider="catalog",
                reasons=["catalog_exact_match"],
                score_breakdown={"text_similarity": 1.0},
                geo_query="Posadas, Misiones",
            )
        return GeoClassificationResult(
            original_text="",
            normalized_text="",
            decision="manual_review",
            confidence=0.60,
            reasons=["missing_location_text"],
            score_breakdown={"text_similarity": 0.0},
        )

    agent = EvaluatorAgent(existing_events=[])
    report = await agent.evaluate_dataset(dataset, classifier=classifier)

    assert report.total == 2
    assert report.accuracy >= 0.5
    assert report.provider_hits["catalog"]["correct"] == 1
    assert "geocoding_coverage" in report.model_dump()
    assert "# Geo Evaluation Report" in report.to_markdown()
