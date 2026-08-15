"""Tipos comunes de geocodificación."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class GeocodingCandidate(BaseModel):
    provider: str
    display_name: str
    normalized_name: str
    latitude: float
    longitude: float
    country_code: str | None = None
    state: str | None = None
    city: str | None = None
    postcode: str | None = None
    precision: str | None = None
    provider_importance: float | None = None
    provider_confidence: float | None = None
    raw_reference: str | None = None
    query: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GeocodingProvider(Protocol):
    async def search(
        self,
        query: str,
        *,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[GeocodingCandidate]: ...
