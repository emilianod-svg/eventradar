"""Pruebas del cliente de geocoding."""

from __future__ import annotations

import pytest
from app.services.geocoding.base import FallbackGeocodingClient


class EmptyClient:
    async def geocode(self, *, query: str) -> dict:
        return {}


class PreciseClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def geocode(self, *, query: str) -> dict:
        self.calls.append(query)
        return {
            "latitude": -27.3671,
            "longitude": -55.8961,
            "precision": "rooftop",
            "provider": "google",
        }


@pytest.mark.asyncio
async def test_fallback_geocoding_client_uses_google_when_primary_fails() -> None:
    fallback = PreciseClient()
    client = FallbackGeocodingClient(EmptyClient(), fallback)

    result = await client.geocode(query="Sarmiento 123")

    assert fallback.calls == ["Sarmiento 123"]
    assert result["provider"] == "google"
    assert result["latitude"] == -27.3671
    assert result["longitude"] == -55.8961
