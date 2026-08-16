"""Pruebas auxiliares de geocodificación."""

from __future__ import annotations

import time

import pytest
from app.agents.geo_classifier import GeoClassifierAgent
from app.domain.entities import EventCandidate
from app.domain.enums import ProcessingStatus
from app.domain.errors import ExternalServiceNotConfiguredError
from app.services.geocoding.base import NotConfiguredGeocodingClient
from app.services.geocoding.cache import InMemoryGeocodingCache
from app.services.geocoding.catalog import LocationCatalog
from app.services.geocoding.normalization import normalize_location_text
from app.services.geocoding.providers import GeocodingProviderChain
from app.services.geocoding.resilience import AsyncRateLimiter, CircuitBreaker
from app.services.geocoding.types import GeocodingCandidate


def test_normalize_location_text_handles_common_abbreviations() -> None:
    assert (
        normalize_location_text("Av. Sta. Fe, Posadas Mnes.") == "avenida santa fe posadas misiones"
    )


def test_location_catalog_loads_default_catalog() -> None:
    catalog = LocationCatalog.default()
    match = catalog.search("Plaza 9 de Julio")

    assert match is not None
    assert match.entry.name == "Plaza 9 de Julio"
    assert match.exact is True


@pytest.mark.asyncio
async def test_not_configured_geocoding_client_fails_explicitly() -> None:
    client = NotConfiguredGeocodingClient()

    with pytest.raises(ExternalServiceNotConfiguredError):
        await client.geocode(query="Sarmiento 123")


def test_in_memory_geocoding_cache_supports_positive_and_negative_entries() -> None:
    cache = InMemoryGeocodingCache()
    candidate = GeocodingCandidate(
        provider="nominatim",
        display_name="Posadas",
        normalized_name="posadas",
        latitude=-27.3671,
        longitude=-55.8961,
    )

    cache.set("posadas", [candidate], ttl_seconds=30)
    entry = cache.get("posadas")
    assert entry is not None
    assert entry.negative is False
    assert entry.candidates[0].display_name == "Posadas"

    cache.set("missing", [], ttl_seconds=30, negative=True)
    entry = cache.get("missing")
    assert entry is not None
    assert entry.negative is True
    assert entry.candidates == []


def test_circuit_breaker_opens_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, reset_seconds=60)

    assert breaker.allow_request() is True
    breaker.record_failure()
    breaker.record_failure()

    assert breaker.allow_request() is False
    breaker.opened_at = time.monotonic() - 120
    assert breaker.allow_request() is True


@pytest.mark.asyncio
async def test_async_rate_limiter_waits_between_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("app.services.geocoding.resilience.asyncio.sleep", fake_sleep)
    limiter = AsyncRateLimiter(min_interval_seconds=1.0)

    await limiter.wait()
    await limiter.wait()

    assert len(sleeps) == 1
    assert sleeps[0] >= 0.0


@pytest.mark.asyncio
async def test_provider_chain_returns_first_non_empty_result() -> None:
    class EmptyProvider:
        async def search(self, query: str, *, country_code: str | None = None, limit: int = 5):
            return []

    class ResultProvider:
        async def search(self, query: str, *, country_code: str | None = None, limit: int = 5):
            return [
                GeocodingCandidate(
                    provider="catalog",
                    display_name="Plaza 9 de Julio",
                    normalized_name="plaza 9 de julio",
                    latitude=-27.369,
                    longitude=-55.8968,
                    country_code="ar",
                    city="Posadas",
                    state="Misiones",
                )
            ]

    chain = GeocodingProviderChain([EmptyProvider(), ResultProvider()])
    result = await chain.search("Plaza 9 de Julio", country_code="ar")

    assert result
    assert result[0].provider == "catalog"


@pytest.mark.asyncio
async def test_geo_classifier_can_use_local_catalog_without_network() -> None:
    class FailIfCalledClient:
        async def geocode(self, *, query: str) -> dict:
            raise AssertionError("no debía haber acceso a red")

    agent = GeoClassifierAgent(geocoding_client=FailIfCalledClient())

    result = await agent.classify(
        EventCandidate.model_validate(
            {
                "is_event": True,
                "confidence": 0.9,
                "title": "x",
                "venue_name": "Plaza 9 de Julio",
                "address": "Plaza 9 de Julio",
                "processing_status": ProcessingStatus.ANALYZED,
            }
        )
    )

    assert result.provider == "catalog"
