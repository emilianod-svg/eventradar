"""Caché en memoria para geocodificación."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.services.geocoding.types import GeocodingCandidate


@dataclass(slots=True)
class GeocodingCacheEntry:
    candidates: list[GeocodingCandidate]
    expires_at: float
    negative: bool = False


class GeocodingCache(Protocol):
    def get(self, key: str) -> GeocodingCacheEntry | None: ...

    def set(
        self,
        key: str,
        candidates: list[GeocodingCandidate],
        *,
        ttl_seconds: int,
        negative: bool = False,
    ) -> None: ...


class InMemoryGeocodingCache:
    def __init__(self) -> None:
        self._entries: dict[str, GeocodingCacheEntry] = {}

    def get(self, key: str) -> GeocodingCacheEntry | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry

    def set(
        self,
        key: str,
        candidates: list[GeocodingCandidate],
        *,
        ttl_seconds: int,
        negative: bool = False,
    ) -> None:
        self._entries[key] = GeocodingCacheEntry(
            candidates=list(candidates),
            expires_at=time.monotonic() + ttl_seconds,
            negative=negative,
        )

    def clear(self) -> None:
        self._entries.clear()
