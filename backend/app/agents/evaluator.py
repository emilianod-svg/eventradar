"""Agente Evaluador (sección 8.7).

Produce una decisión explicable: ACCEPT, REJECT, REVIEW o MERGE. Usa
RapidFuzz/Levenshtein (vía `app.services.matching`) para deduplicación; el
LLM no participa en esta etapa.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any, cast

from app.config import get_settings
from app.domain.decisions import (
    CONFIDENCE_ACCEPT_THRESHOLD,
    CONFIDENCE_REVIEW_THRESHOLD,
    DUPLICATE_AUTO_MERGE_THRESHOLD,
    DUPLICATE_REVIEW_THRESHOLD,
)
from app.domain.entities import EvaluationResult, EventCandidate
from app.domain.enums import EvaluationDecisionType, ProcessingStatus
from app.services.matching.base import DuplicateMatcher, get_duplicate_matcher


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


class EvaluatorAgent:
    def __init__(
        self,
        existing_events: list[Mapping[str, Any] | EventCandidate] | None = None,
        duplicate_matcher: DuplicateMatcher | None = None,
        base_latitude: float | None = None,
        base_longitude: float | None = None,
        search_radius_km: float | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        settings = get_settings()
        self._existing_events = list(existing_events or [])
        self._duplicate_matcher = duplicate_matcher or get_duplicate_matcher()
        self._base_latitude = settings.base_latitude if base_latitude is None else base_latitude
        self._base_longitude = settings.base_longitude if base_longitude is None else base_longitude
        self._search_radius_km = (
            settings.search_radius_km if search_radius_km is None else search_radius_km
        )
        self._now = now or (lambda: datetime.now(UTC))

    async def execute(self, data: EventCandidate) -> EvaluationResult:
        reasons: list[str] = []

        if not data.is_event:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["publication_is_not_an_event"],
                score=data.confidence,
            )

        source_url = self._source_url(data)
        if not source_url:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["missing_source_url"],
                score=data.confidence,
            )

        if data.confidence < CONFIDENCE_REVIEW_THRESHOLD:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["confidence_below_minimum"],
                score=data.confidence,
            )

        if data.start_at is None:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["missing_start_at"],
                score=data.confidence,
            )

        if data.start_at <= self._now():
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["event_date_is_not_future"],
                score=data.confidence,
            )

        if data.end_at is not None and data.end_at < data.start_at:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["end_at_before_start_at"],
                score=data.confidence,
            )

        if data.latitude is not None and data.longitude is not None:
            distance = self._distance_to_base(data.latitude, data.longitude)
            if distance is not None and distance > self._search_radius_km:
                return EvaluationResult(
                    decision=EvaluationDecisionType.REJECT,
                    reasons=[f"outside_radius_{distance:.2f}km"],
                    score=data.confidence,
                )

        if (
            data.confidence < CONFIDENCE_ACCEPT_THRESHOLD
            or data.processing_status == ProcessingStatus.PENDING_REVIEW
        ):
            reasons.append("low_confidence_requires_review")

        duplicate = self._find_duplicate(data)
        if duplicate is not None:
            score = duplicate["score"]
            if (
                score >= DUPLICATE_AUTO_MERGE_THRESHOLD
                and duplicate["date_compatible"]
                and duplicate["location_compatible"]
            ):
                return EvaluationResult(
                    decision=EvaluationDecisionType.MERGE,
                    reasons=reasons + duplicate["reasons"],
                    duplicate_of=duplicate["id"],
                    score=score,
                )
            if score >= DUPLICATE_REVIEW_THRESHOLD:
                return EvaluationResult(
                    decision=EvaluationDecisionType.REVIEW,
                    reasons=reasons + duplicate["reasons"],
                    duplicate_of=duplicate["id"],
                    score=score,
                )

        if reasons:
            return EvaluationResult(
                decision=EvaluationDecisionType.REVIEW,
                reasons=reasons,
                score=data.confidence,
            )

        return EvaluationResult(
            decision=EvaluationDecisionType.ACCEPT,
            reasons=["passed_validation"],
            score=data.confidence,
        )

    def _find_duplicate(self, data: EventCandidate) -> dict[str, Any] | None:
        best_match: dict[str, Any] | None = None
        candidate_payload = self._candidate_payload(data)
        for existing in self._existing_events:
            existing_payload = self._candidate_payload(existing)
            score = self._duplicate_matcher.score(
                candidate=candidate_payload,
                existing=existing_payload,
            )
            if best_match is None or score > best_match["score"]:
                best_match = {
                    "id": self._existing_id(existing),
                    "score": score,
                    "date_compatible": self._date_compatible(candidate_payload, existing),
                    "location_compatible": self._location_compatible(candidate_payload, existing),
                    "reasons": [f"duplicate_candidate_score={score:.3f}"],
                }
        return best_match

    def _candidate_payload(self, value: Mapping[str, Any] | EventCandidate) -> dict[str, Any]:
        if isinstance(value, Mapping):
            payload = dict(value)
        elif hasattr(value, "model_dump"):
            payload = value.model_dump()
        else:
            payload = {
                key: getattr(value, key, None)
                for key in (
                    "id",
                    "title",
                    "start_at",
                    "end_at",
                    "venue_name",
                    "address",
                    "latitude",
                    "longitude",
                    "source_url",
                    "confidence",
                    "processing_status",
                    "evidence",
                )
            }
        if not payload.get("source_url"):
            payload["source_url"] = self._source_url(value)
        return payload

    def _existing_id(self, value: Mapping[str, Any] | EventCandidate) -> Any:
        if isinstance(value, Mapping):
            return value.get("id")
        return getattr(value, "id", None)

    def _source_url(self, value: Mapping[str, Any] | EventCandidate) -> str | None:
        if isinstance(value, Mapping):
            source_url = value.get("source_url")
            if isinstance(source_url, str) and source_url.strip():
                return source_url.strip()
            evidence = value.get("evidence")
            if isinstance(evidence, Mapping):
                fallback = evidence.get("source_url")
                if isinstance(fallback, str) and fallback.strip():
                    return fallback.strip()
            return None
        source_url = getattr(value, "source_url", None)
        if isinstance(source_url, str) and source_url.strip():
            return source_url.strip()
        evidence = getattr(value, "evidence", {})
        if isinstance(evidence, Mapping):
            fallback = evidence.get("source_url")
            if isinstance(fallback, str) and fallback.strip():
                return fallback.strip()
        return None

    def _date_compatible(
        self,
        candidate: dict[str, Any],
        existing: Mapping[str, Any] | EventCandidate,
    ) -> bool:
        candidate_start = candidate.get("start_at")
        existing_start = self._candidate_payload(existing).get("start_at")
        if not isinstance(candidate_start, datetime) or not isinstance(existing_start, datetime):
            return False
        return abs((candidate_start - existing_start).total_seconds()) <= 24 * 3600

    def _location_compatible(
        self,
        candidate: dict[str, Any],
        existing: Mapping[str, Any] | EventCandidate,
    ) -> bool:
        existing_payload = self._candidate_payload(existing)
        candidate_lat = candidate.get("latitude")
        candidate_lon = candidate.get("longitude")
        existing_lat = existing_payload.get("latitude")
        existing_lon = existing_payload.get("longitude")
        if not all(
            isinstance(value, int | float)
            for value in (candidate_lat, candidate_lon, existing_lat, existing_lon)
        ):
            candidate_venue = self._venue_text(candidate)
            existing_venue = self._venue_text(existing_payload)
            if not candidate_venue or not existing_venue:
                return False

            from rapidfuzz import fuzz

            return fuzz.token_set_ratio(candidate_venue, existing_venue) / 100.0 >= 0.85

        candidate_lat_f = float(cast(float | int, candidate_lat))
        candidate_lon_f = float(cast(float | int, candidate_lon))
        existing_lat_f = float(cast(float | int, existing_lat))
        existing_lon_f = float(cast(float | int, existing_lon))
        distance = _haversine_km(
            candidate_lat_f,
            candidate_lon_f,
            existing_lat_f,
            existing_lon_f,
        )
        return distance is not None and distance <= 2.0

    def _distance_to_base(self, latitude: float | None, longitude: float | None) -> float | None:
        return _haversine_km(latitude, longitude, self._base_latitude, self._base_longitude)

    def _venue_text(self, value: Mapping[str, Any] | EventCandidate) -> str | None:
        if isinstance(value, Mapping):
            venue_name = value.get("venue_name")
            address = value.get("address")
        else:
            venue_name = value.venue_name
            address = value.address

        pieces = [
            piece for piece in (venue_name, address) if isinstance(piece, str) and piece.strip()
        ]
        if not pieces:
            return None
        return " ".join(pieces)
