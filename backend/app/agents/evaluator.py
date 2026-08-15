"""Agente Evaluador (sección 8.7).

Produce una decisión explicable: ACCEPT, REJECT, REVIEW o MERGE. Usa
RapidFuzz/Levenshtein (vía `app.services.matching`) para deduplicación; el
LLM no participa en esta etapa.
"""

from __future__ import annotations

import inspect
import json
import ipaddress
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.agents.geo_classifier import GeoClassificationResult
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
        source_url_checker: Callable[[str], Any] | None = None,
        allowed_source_hosts: Sequence[str] | None = None,
        max_future_days: int | None = None,
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
        self._source_url_checker = source_url_checker
        self._allowed_source_hosts = {
            host.strip().casefold()
            for host in (
                allowed_source_hosts
                if allowed_source_hosts is not None
                else settings.evaluation_allowed_source_hosts.split(",")
            )
            if host.strip()
        }
        self._max_future_days = (
            settings.evaluation_future_horizon_days if max_future_days is None else max_future_days
        )

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

        if not self._is_required_text_present(data.title):
            reasons.append("missing_title")
        if not self._is_required_text_present(data.venue_name):
            reasons.append("missing_venue_name")
        if not self._is_required_text_present(data.address):
            reasons.append("missing_address")

        if not self._source_url_permitted(source_url):
            reasons.append("source_url_not_permitted")
        elif not await self._source_url_accessible(source_url):
            reasons.append("source_url_not_accessible")

        if reasons:
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=reasons,
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

        if data.start_at > (self._now() + timedelta(days=self._max_future_days)):
            return EvaluationResult(
                decision=EvaluationDecisionType.REJECT,
                reasons=["event_date_beyond_horizon"],
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

    async def evaluate_dataset(
        self,
        dataset: Sequence[Mapping[str, Any]] | str | Path,
        *,
        classifier: Callable[[EventCandidate], Any] | None = None,
        minimums: Mapping[str, float] | None = None,
    ) -> GeoEvaluationReport:
        records = self._load_dataset(dataset)
        classifier = classifier or self._default_classifier
        items: list[GeoEvaluationItem] = []

        for record in records:
            candidate = self._dataset_candidate(record)
            classification = await self._call_classifier(classifier, candidate)
            expected = self._expected_label(record)
            predicted_valid = classification.decision in {"accepted", "provisional"}
            expected_valid = expected.get(
                "valid", expected.get("decision") in {"accepted", "provisional"}
            )
            items.append(
                GeoEvaluationItem(
                    id=str(
                        record.get("id") or candidate.source_url or candidate.title or len(items)
                    ),
                    expected=expected,
                    predicted=classification,
                    expected_valid=bool(expected_valid),
                    predicted_valid=predicted_valid,
                )
            )

        report = self._build_geo_report(items)
        if minimums is not None:
            self._assert_geo_quality(report, minimums=minimums)
        return report

    def _load_dataset(
        self,
        dataset: Sequence[Mapping[str, Any]] | str | Path,
    ) -> list[dict[str, Any]]:
        if isinstance(dataset, str | Path):
            payload = json.loads(Path(dataset).read_text(encoding="utf-8"))
        else:
            payload = list(dataset)
        if not isinstance(payload, list):
            raise ValueError("El dataset debe ser una lista de registros")
        return [dict(item) for item in payload if isinstance(item, Mapping)]

    async def _call_classifier(
        self,
        classifier: Callable[[EventCandidate], Any],
        candidate: EventCandidate,
    ) -> GeoClassificationResult:
        result = classifier(candidate)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, GeoClassificationResult):
            return result
        if isinstance(result, Mapping):
            return GeoClassificationResult.model_validate(result)
        raise TypeError("El clasificador debe devolver GeoClassificationResult o dict compatible")

    async def _default_classifier(self, candidate: EventCandidate) -> GeoClassificationResult:
        from app.agents.geo_classifier import GeoClassifierAgent

        return await GeoClassifierAgent().classify(candidate)

    def _dataset_candidate(self, record: Mapping[str, Any]) -> EventCandidate:
        payload = dict(record.get("candidate") or record.get("input") or record)
        payload.setdefault("is_event", True)
        payload.setdefault("confidence", 0.0)
        payload.setdefault("processing_status", ProcessingStatus.ANALYZED)
        payload.setdefault("evidence", {})
        return EventCandidate.model_validate(payload)

    def _expected_label(self, record: Mapping[str, Any]) -> dict[str, Any]:
        expected = record.get("expected")
        if isinstance(expected, Mapping):
            return dict(expected)
        label = record.get("label")
        if isinstance(label, str):
            return {"valid": label in {"accepted", "provisional", "valid"}, "decision": label}
        return {"valid": bool(record.get("valid", False))}

    def _build_geo_report(self, items: list[GeoEvaluationItem]) -> GeoEvaluationReport:
        total = len(items)
        tp = sum(1 for item in items if item.expected_valid and item.predicted_valid)
        tn = sum(1 for item in items if not item.expected_valid and not item.predicted_valid)
        fp = sum(1 for item in items if not item.expected_valid and item.predicted_valid)
        fn = sum(1 for item in items if item.expected_valid and not item.predicted_valid)
        review_count = sum(1 for item in items if item.predicted.decision == "manual_review")
        coverage_count = sum(1 for item in items if item.predicted.provider is not None)

        provider_hits: dict[str, dict[str, int]] = {}
        threshold_distribution = {
            "lt_0_50": 0,
            "ge_0_50_lt_0_75": 0,
            "ge_0_75_lt_0_90": 0,
            "ge_0_90": 0,
        }
        for item in items:
            confidence = item.predicted.confidence
            if confidence < 0.50:
                threshold_distribution["lt_0_50"] += 1
            elif confidence < 0.75:
                threshold_distribution["ge_0_50_lt_0_75"] += 1
            elif confidence < 0.90:
                threshold_distribution["ge_0_75_lt_0_90"] += 1
            else:
                threshold_distribution["ge_0_90"] += 1

            provider = item.predicted.provider or "unresolved"
            bucket = provider_hits.setdefault(provider, {"total": 0, "correct": 0})
            bucket["total"] += 1
            if item.expected_valid == item.predicted_valid:
                bucket["correct"] += 1

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        accuracy = (tp + tn) / total if total else 0.0

        return GeoEvaluationReport(
            total=total,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            review_rate=review_count / total if total else 0.0,
            false_positives=fp,
            false_negatives=fn,
            geocoding_coverage=coverage_count / total if total else 0.0,
            provider_hits={
                provider: {
                    "correct": values["correct"],
                    "total": values["total"],
                    "accuracy": values["correct"] / values["total"] if values["total"] else 0.0,
                }
                for provider, values in provider_hits.items()
            },
            threshold_distribution=threshold_distribution,
            items=items,
        )

    def _assert_geo_quality(
        self,
        report: GeoEvaluationReport,
        *,
        minimums: Mapping[str, float] | None,
    ) -> None:
        thresholds = {
            "accuracy": 0.80,
            "precision": 0.75,
            "recall": 0.75,
            "f1": 0.75,
            "geocoding_coverage": 0.80,
        }
        if minimums is not None:
            thresholds.update({key: float(value) for key, value in minimums.items()})

        failures = [
            f"{metric}={getattr(report, metric):.3f} < {minimum:.3f}"
            for metric, minimum in thresholds.items()
            if getattr(report, metric) < minimum
        ]
        if failures:
            raise AssertionError("Calidad geográfica insuficiente: " + "; ".join(failures))

    def _find_duplicate(self, data: EventCandidate) -> dict[str, Any] | None:
        best_match: dict[str, Any] | None = None
        candidate_payload = self._candidate_payload(data)
        for existing in self._duplicate_candidates(candidate_payload):
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

    def _duplicate_candidates(
        self, candidate_payload: Mapping[str, Any]
    ) -> list[Mapping[str, Any] | EventCandidate]:
        return [
            existing
            for existing in self._existing_events
            if self._is_duplicate_candidate(candidate_payload, existing)
        ]

    def _is_duplicate_candidate(
        self,
        candidate_payload: Mapping[str, Any],
        existing: Mapping[str, Any] | EventCandidate,
    ) -> bool:
        if self._date_compatible(candidate_payload, existing):
            return True
        if self._location_compatible(candidate_payload, existing):
            return True
        if self._title_similarity(candidate_payload, existing) >= 0.50:
            return True
        return False

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

    def _title_similarity(
        self,
        candidate: Mapping[str, Any],
        existing: Mapping[str, Any] | EventCandidate,
    ) -> float:
        candidate_title = candidate.get("title")
        existing_title = self._candidate_payload(existing).get("title")
        if not isinstance(candidate_title, str) or not isinstance(existing_title, str):
            return 0.0
        candidate_title = candidate_title.strip()
        existing_title = existing_title.strip()
        if not candidate_title or not existing_title:
            return 0.0
        return fuzz.token_set_ratio(candidate_title, existing_title) / 100.0

    def _is_required_text_present(self, value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    async def _source_url_accessible(self, source_url: str) -> bool:
        if self._source_url_checker is None:
            return True
        result = self._source_url_checker(source_url)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)

    def _source_url_permitted(self, source_url: str) -> bool:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        host = parsed.hostname or ""
        if not host:
            return False

        host = host.casefold()
        if self._allowed_source_hosts and not any(
            host == allowed or host.endswith(f".{allowed}") for allowed in self._allowed_source_hosts
        ):
            return False

        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return host not in {"localhost"}

        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )

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


class GeoEvaluationItem(BaseModel):
    id: str
    expected: dict[str, Any]
    predicted: GeoClassificationResult
    expected_valid: bool
    predicted_valid: bool


class GeoEvaluationReport(BaseModel):
    total: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    review_rate: float
    false_positives: int
    false_negatives: int
    geocoding_coverage: float
    provider_hits: dict[str, dict[str, float]] = Field(default_factory=dict)
    threshold_distribution: dict[str, int] = Field(default_factory=dict)
    items: list[GeoEvaluationItem] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        lines = [
            "# Geo Evaluation Report",
            f"- total: {self.total}",
            f"- accuracy: {self.accuracy:.3f}",
            f"- precision: {self.precision:.3f}",
            f"- recall: {self.recall:.3f}",
            f"- f1: {self.f1:.3f}",
            f"- review_rate: {self.review_rate:.3f}",
            f"- false_positives: {self.false_positives}",
            f"- false_negatives: {self.false_negatives}",
            f"- geocoding_coverage: {self.geocoding_coverage:.3f}",
        ]
        return "\n".join(lines)
