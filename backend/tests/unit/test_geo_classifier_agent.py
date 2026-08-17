"""Pruebas del Agente Clasificador Geográfico."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.agents.geo_classifier import GeoClassifierAgent
from app.config import get_settings
from app.domain.entities import EventCandidate
from app.domain.enums import ProcessingStatus
from app.services.geocoding.base import FallbackGeocodingClient
from app.services.geocoding.normalization import normalize_location_text


class FakeGeocodingClient:
    def __init__(self, responses: dict[str, dict]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    async def geocode(self, *, query: str) -> dict:
        self.calls.append(query)
        return self.responses[query]


class EmptyGeocodingClient:
    async def geocode(self, *, query: str) -> dict:
        return {}


def _candidate(**overrides: object) -> EventCandidate:
    payload = {
        "is_event": True,
        "confidence": 0.9,
        "source_id": uuid4(),
        "source_url": "https://example.com/evento",
        "title": "Festival",
        "venue_name": "Parque",
        "address": "Sarmiento 123",
        "start_at": datetime(2026, 8, 20, tzinfo=UTC),
        "processing_status": ProcessingStatus.ANALYZED,
    }
    payload.update(overrides)
    return EventCandidate.model_validate(payload)


@pytest.mark.asyncio
async def test_geo_classifier_uses_explicit_coordinates_before_geocoding() -> None:
    agent = GeoClassifierAgent(
        geocoding_client=FakeGeocodingClient({}),
        base_latitude=-27.3671,
        base_longitude=-55.8961,
        search_radius_km=15.0,
    )

    result = await agent.execute(
        _candidate(latitude=-27.366, longitude=-55.895, geo_precision="exact", geo_query="manual")
    )

    assert result.processing_status == ProcessingStatus.GEOLOCATED
    assert result.latitude == -27.366
    assert result.longitude == -55.895
    assert result.geo_precision == "exact"
    assert result.geo_query == "manual"


@pytest.mark.asyncio
async def test_geo_classifier_resolves_address_query_first() -> None:
    client = FakeGeocodingClient(
        {
            "Sarmiento 123": {
                "latitude": -27.3671,
                "longitude": -55.8961,
                "precision": "rooftop",
            }
        }
    )
    agent = GeoClassifierAgent(geocoding_client=client)

    result = await agent.execute(_candidate())

    assert client.calls[0] == "Sarmiento 123"
    assert result.processing_status == ProcessingStatus.GEOLOCATED
    assert result.geo_precision == "rooftop"


@pytest.mark.asyncio
async def test_geo_classifier_marks_ambiguous_matches_for_review() -> None:
    client = FakeGeocodingClient(
        {
            "Sarmiento 123": {
                "candidates": [
                    {"latitude": -27.3671, "longitude": -55.8961, "score": 0.88},
                    {"latitude": -27.368, "longitude": -55.897, "score": 0.82},
                ]
            }
        }
    )
    agent = GeoClassifierAgent(geocoding_client=client)

    result = await agent.execute(_candidate())

    assert result.processing_status == ProcessingStatus.PENDING_REVIEW
    assert result.geo_query == "Sarmiento 123"


@pytest.mark.asyncio
async def test_geo_classifier_rejects_results_outside_radius() -> None:
    client = FakeGeocodingClient(
        {
            "Sarmiento 123": {
                "latitude": -26.0,
                "longitude": -54.0,
                "precision": "city",
            }
        }
    )
    agent = GeoClassifierAgent(
        geocoding_client=client,
        base_latitude=-27.3671,
        base_longitude=-55.8961,
        search_radius_km=5.0,
    )

    result = await agent.execute(_candidate())

    assert result.processing_status == ProcessingStatus.REJECTED
    assert result.latitude == -26.0
    assert result.longitude == -54.0


@pytest.mark.asyncio
async def test_geo_classifier_uses_google_fallback_after_nominatim_empty() -> None:
    fallback = FakeGeocodingClient(
        {
            "Sarmiento 123": {
                "latitude": -27.3671,
                "longitude": -55.8961,
                "precision": "rooftop",
                "provider": "google",
            }
        }
    )
    agent = GeoClassifierAgent(
        geocoding_client=FallbackGeocodingClient(EmptyGeocodingClient(), fallback)
    )

    result = await agent.execute(_candidate())

    assert result.processing_status == ProcessingStatus.GEOLOCATED
    assert result.evidence["geo_source"] == "google"


@pytest.mark.asyncio
async def test_geo_classifier_uses_catalog_before_geocoding() -> None:
    class FailIfCalledClient:
        async def geocode(self, *, query: str) -> dict:
            raise AssertionError(f"geocoder no debía ser llamado: {query}")

    agent = GeoClassifierAgent(geocoding_client=FailIfCalledClient())

    result = await agent.execute(
        _candidate(venue_name="Plaza 9 de Julio", address="Plaza 9 de Julio")
    )

    assert result.processing_status == ProcessingStatus.GEOLOCATED
    assert result.geo_provider == "catalog"
    assert result.matched_catalog_entry == "Plaza 9 de Julio"


def test_geo_classifier_threshold_boundaries() -> None:
    settings = get_settings()
    agent = GeoClassifierAgent(geocoding_client=EmptyGeocodingClient())

    assert (
        agent._decision_from_confidence(settings.geo_confidence_reject_threshold - 0.01)
        == "rejected"
    )
    assert (
        agent._decision_from_confidence(settings.geo_confidence_reject_threshold) == "manual_review"
    )
    assert (
        agent._decision_from_confidence(settings.geo_confidence_review_threshold) == "provisional"
    )
    assert agent._decision_from_confidence(settings.geo_confidence_auto_threshold) == "accepted"


@pytest.mark.asyncio
async def test_geo_classifier_rejects_posadas_outside_allowed_country() -> None:
    agent = GeoClassifierAgent(geocoding_client=EmptyGeocodingClient())

    result = await agent.execute(
        _candidate(
            venue_name="Encarnacion",
            address="Encarnacion, Itapua, Paraguay",
            title="Festival fuera de alcance",
        )
    )

    assert result.processing_status == ProcessingStatus.REJECTED
    assert result.geo_decision == "rejected"
    assert result.country_code == "py"
    assert normalize_location_text(result.geo_query or "").startswith("encarnacion")
