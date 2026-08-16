"""Interfaz de geocodificación y fábrica de proveedores."""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError
from app.services.geocoding.cache import InMemoryGeocodingCache
from app.services.geocoding.providers import (
    GeoapifyGeocodingProvider,
    GeocodingProviderChain,
    LocationIQGeocodingProvider,
    NominatimGeocodingProvider,
)
from app.services.geocoding.types import GeocodingCandidate, GeocodingProvider


class GeocodingClient(Protocol):
    async def geocode(self, *, query: str) -> dict: ...


def _is_precise_result(result: dict) -> bool:
    return (
        result.get("latitude") is not None
        and result.get("longitude") is not None
        and not result.get("candidates")
    )


def _candidate_to_dict(candidate: GeocodingCandidate) -> dict:
    return {
        "latitude": candidate.latitude,
        "longitude": candidate.longitude,
        "precision": candidate.precision or candidate.metadata.get("precision", "estimated"),
        "display_name": candidate.display_name,
        "provider": candidate.provider,
        "score": candidate.provider_confidence
        if candidate.provider_confidence is not None
        else candidate.provider_importance or 0.0,
        "country_code": candidate.country_code,
        "state": candidate.state,
        "city": candidate.city,
        "postcode": candidate.postcode,
        "raw_reference": candidate.raw_reference,
        "normalized_name": candidate.normalized_name,
    }


def _candidates_to_dict(candidates: list[GeocodingCandidate], query: str) -> dict:
    if not candidates:
        return {}
    if len(candidates) == 1:
        result = _candidate_to_dict(candidates[0])
        result["query"] = query
        return result
    return {
        "provider": candidates[0].provider,
        "query": query,
        "candidates": [_candidate_to_dict(candidate) for candidate in candidates],
    }


async def _invoke_geocoder(provider: object, query: str) -> dict:
    search = getattr(provider, "search", None)
    if callable(search):
        candidates = await search(query, country_code="ar", limit=5)
        if isinstance(candidates, list):
            return _candidates_to_dict(candidates, query)

    geocode = getattr(provider, "geocode", None)
    if callable(geocode):
        result = await geocode(query=query)
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            return _candidates_to_dict(result, query)
    return {}


class ProviderGeocodingClient:
    def __init__(self, provider_chain: GeocodingProviderChain) -> None:
        self._provider_chain = provider_chain

    async def geocode(self, *, query: str) -> dict:
        result = await self._provider_chain.search(query, country_code="ar", limit=5)
        return _candidates_to_dict(result, query)


class FallbackGeocodingClient:
    def __init__(self, primary: object, fallback: object) -> None:
        self._primary = primary
        self._fallback = fallback

    async def geocode(self, *, query: str) -> dict:
        try:
            primary_result = await _invoke_geocoder(self._primary, query)
        except Exception:
            primary_result = {}

        if _is_precise_result(primary_result):
            return primary_result

        fallback_result = await _invoke_geocoder(self._fallback, query)
        if fallback_result:
            return fallback_result
        return primary_result


class NotConfiguredGeocodingClient:
    async def geocode(self, *, query: str) -> dict:
        raise ExternalServiceNotConfiguredError(
            "No hay proveedor de geocodificación configurado. "
            "Definí NOMINATIM_ENABLED/LOCATIONIQ_ENABLED/GEOAPIFY_ENABLED y sus credenciales."
        )


def _build_provider_chain() -> GeocodingProviderChain:
    settings = get_settings()
    cache = InMemoryGeocodingCache()
    providers: list[GeocodingProvider] = []

    for name in settings.geocoding_provider_order_list:
        if name == "nominatim" and settings.nominatim_enabled and settings.nominatim_contact_email:
            providers.append(
                NominatimGeocodingProvider(
                    base_url=settings.nominatim_base_url,
                    timeout_seconds=settings.geocoding_timeout_seconds,
                    enabled=True,
                    cache=cache,
                    min_interval_seconds=settings.nominatim_rate_limit_seconds,
                    failure_threshold=settings.geocoding_circuit_breaker_threshold,
                    reset_seconds=settings.geocoding_circuit_breaker_reset_seconds,
                    max_attempts=settings.geocoding_max_attempts,
                    backoff_base_seconds=settings.geocoding_backoff_base_seconds,
                    backoff_jitter_seconds=settings.geocoding_backoff_jitter_seconds,
                )
            )
        elif name == "locationiq" and settings.locationiq_enabled and settings.locationiq_api_key:
            providers.append(
                LocationIQGeocodingProvider(
                    base_url=settings.locationiq_base_url,
                    timeout_seconds=settings.geocoding_timeout_seconds,
                    enabled=True,
                    cache=cache,
                    min_interval_seconds=0.0,
                    failure_threshold=settings.geocoding_circuit_breaker_threshold,
                    reset_seconds=settings.geocoding_circuit_breaker_reset_seconds,
                    max_attempts=settings.geocoding_max_attempts,
                    backoff_base_seconds=settings.geocoding_backoff_base_seconds,
                    backoff_jitter_seconds=settings.geocoding_backoff_jitter_seconds,
                )
            )
        elif name == "geoapify" and settings.geoapify_enabled and settings.geoapify_api_key:
            providers.append(
                GeoapifyGeocodingProvider(
                    base_url=settings.geoapify_base_url,
                    timeout_seconds=settings.geocoding_timeout_seconds,
                    enabled=True,
                    cache=cache,
                    min_interval_seconds=0.0,
                    failure_threshold=settings.geocoding_circuit_breaker_threshold,
                    reset_seconds=settings.geocoding_circuit_breaker_reset_seconds,
                    max_attempts=settings.geocoding_max_attempts,
                    backoff_base_seconds=settings.geocoding_backoff_base_seconds,
                    backoff_jitter_seconds=settings.geocoding_backoff_jitter_seconds,
                )
            )

    return GeocodingProviderChain(providers)


def get_geocoding_client() -> GeocodingClient:
    provider_chain = _build_provider_chain()
    if provider_chain.providers:
        return ProviderGeocodingClient(provider_chain)
    return NotConfiguredGeocodingClient()
