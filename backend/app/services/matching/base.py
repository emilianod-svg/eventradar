"""Interfaz de matching/deduplicación (sección 10 del plan).

`rapidfuzz` ya está declarado en las dependencias del backend. Esta capa
implementa el score compuesto de la sección 10.3 y deja al Evaluador la
decisión final (sección 10.4).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any, Protocol

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.casefold()
    normalized = "".join(ch for ch in normalized if ch.isalnum() or ch.isspace())
    return " ".join(normalized.split())


def _get_field(value: Mapping[str, Any] | Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _haversine_km(
    latitude_a: float | None,
    longitude_a: float | None,
    latitude_b: float | None,
    longitude_b: float | None,
) -> float | None:
    if None in {latitude_a, longitude_a, latitude_b, longitude_b}:
        return None

    radius_km = 6371.0
    lat1 = radians(latitude_a or 0.0)
    lon1 = radians(longitude_a or 0.0)
    lat2 = radians(latitude_b or 0.0)
    lon2 = radians(longitude_b or 0.0)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    hav = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * radius_km * asin(sqrt(hav))


class DuplicateMatcher(Protocol):
    def score(self, *, candidate: dict, existing: dict) -> float:
        """Debe implementar el score compuesto de la sección 10.3."""
        ...


class RapidFuzzDuplicateMatcher:
    """Implementa el score compuesto con RapidFuzz + heurísticas de fecha y lugar."""

    def score(self, *, candidate: dict, existing: dict) -> float:
        title_similarity = self._text_similarity(
            _get_field(candidate, "title"), _get_field(existing, "title")
        )
        venue_similarity = self._text_similarity(
            self._venue_text(candidate), self._venue_text(existing)
        )
        date_similarity = self._date_similarity(candidate, existing)
        geographic_similarity = self._geographic_similarity(candidate, existing)

        return (
            title_similarity * 0.45
            + venue_similarity * 0.20
            + date_similarity * 0.25
            + geographic_similarity * 0.10
        )

    def date_compatible(self, *, candidate: dict, existing: dict) -> bool:
        candidate_start = _as_datetime(_get_field(candidate, "start_at"))
        existing_start = _as_datetime(_get_field(existing, "start_at"))
        if candidate_start is None or existing_start is None:
            return False
        return abs((candidate_start - existing_start).total_seconds()) <= 24 * 3600

    def location_compatible(self, *, candidate: dict, existing: dict) -> bool:
        candidate_lat = _get_field(candidate, "latitude")
        candidate_lon = _get_field(candidate, "longitude")
        existing_lat = _get_field(existing, "latitude")
        existing_lon = _get_field(existing, "longitude")

        distance = _haversine_km(candidate_lat, candidate_lon, existing_lat, existing_lon)
        if distance is not None:
            return distance <= 2.0

        return (
            self._text_similarity(self._venue_text(candidate), self._venue_text(existing)) >= 0.85
        )

    def _text_similarity(self, left: str | None, right: str | None) -> float:
        normalized_left = _normalize_text(left)
        normalized_right = _normalize_text(right)
        if not normalized_left or not normalized_right:
            return 0.0

        token_score = fuzz.token_set_ratio(normalized_left, normalized_right) / 100.0
        levenshtein_score = Levenshtein.normalized_similarity(normalized_left, normalized_right)
        return (token_score * 0.80) + (levenshtein_score * 0.20)

    def _venue_text(self, value: Mapping[str, Any] | Any) -> str | None:
        venue_name = _get_field(value, "venue_name")
        address = _get_field(value, "address")
        pieces = [
            piece for piece in (venue_name, address) if isinstance(piece, str) and piece.strip()
        ]
        if not pieces:
            return None
        return " ".join(pieces)

    def _date_similarity(self, candidate: dict, existing: dict) -> float:
        candidate_start = _as_datetime(_get_field(candidate, "start_at"))
        existing_start = _as_datetime(_get_field(existing, "start_at"))
        if candidate_start is None or existing_start is None:
            return 0.0

        delta_hours = abs((candidate_start - existing_start).total_seconds()) / 3600.0
        if delta_hours <= 4:
            return 1.0
        if delta_hours <= 24:
            return 0.75
        if delta_hours <= 72:
            return 0.35
        return 0.0

    def _geographic_similarity(self, candidate: dict, existing: dict) -> float:
        candidate_lat = _get_field(candidate, "latitude")
        candidate_lon = _get_field(candidate, "longitude")
        existing_lat = _get_field(existing, "latitude")
        existing_lon = _get_field(existing, "longitude")

        distance = _haversine_km(candidate_lat, candidate_lon, existing_lat, existing_lon)
        if distance is None:
            return 0.0
        if distance <= 0.25:
            return 1.0
        if distance <= 1.0:
            return 0.8
        if distance <= 2.0:
            return 0.6
        if distance <= 5.0:
            return 0.3
        return 0.0


class NotImplementedDuplicateMatcher:
    def score(self, *, candidate: dict, existing: dict) -> float:
        raise NotImplementedError(
            "DuplicateMatcher.score: pendiente de implementación (sección 10)."
        )


def get_duplicate_matcher() -> DuplicateMatcher:
    return RapidFuzzDuplicateMatcher()
