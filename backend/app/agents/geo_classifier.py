"""Agente Clasificador Geográfico."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any, Literal, cast

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.config import get_settings
from app.domain.entities import EventCandidate
from app.domain.enums import ProcessingStatus
from app.services.geocoding import (
    CatalogMatch,
    GeocodingCandidate,
    LocationCatalog,
    get_geocoding_client,
    load_catalog,
    normalize_location_text,
)


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


@dataclass(slots=True)
class GeoScoreWeights:
    text_similarity: float = 0.30
    city_match: float = 0.15
    state_match: float = 0.10
    country_match: float = 0.10
    coordinate_in_allowed_area: float = 0.15
    provider_confidence: float = 0.15
    catalog_exact_match: float = 0.05

    def validate(self) -> None:
        total = sum(
            (
                self.text_similarity,
                self.city_match,
                self.state_match,
                self.country_match,
                self.coordinate_in_allowed_area,
                self.provider_confidence,
                self.catalog_exact_match,
            )
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError("GeoScoreWeights debe sumar 1.0")


GeoDecision = Literal["accepted", "provisional", "manual_review", "rejected", "unresolved"]
REJECTED_DECISION: GeoDecision = "rejected"


class GeoClassificationResult(BaseModel):
    original_text: str
    normalized_text: str
    decision: GeoDecision
    confidence: float = Field(ge=0.0, le=1.0)
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    state: str | None = None
    country_code: str | None = None
    precision: str | None = None
    matched_catalog_entry: str | None = None
    provider: str | None = None
    reasons: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    geo_query: str | None = None


class GeoClassifierAgent:
    def __init__(
        self,
        geocoding_client: object | None = None,
        venue_cache: Mapping[str, dict[str, Any]] | None = None,
        catalog: LocationCatalog | None = None,
        base_latitude: float | None = None,
        base_longitude: float | None = None,
        search_radius_km: float | None = None,
        score_weights: GeoScoreWeights | None = None,
    ) -> None:
        settings = get_settings()
        self._geocoding_client = geocoding_client or get_geocoding_client()
        self._venue_cache = dict(venue_cache or {})
        self._catalog = catalog or load_catalog(settings.geocoding_catalog_path)
        self._base_latitude = settings.base_latitude if base_latitude is None else base_latitude
        self._base_longitude = settings.base_longitude if base_longitude is None else base_longitude
        self._search_radius_km = (
            settings.search_radius_km if search_radius_km is None else search_radius_km
        )
        self._threshold_reject = settings.geo_confidence_reject_threshold
        self._threshold_review = settings.geo_confidence_review_threshold
        self._threshold_auto = settings.geo_confidence_auto_threshold
        self._catalog_threshold = settings.geo_catalog_match_threshold
        self._weights = score_weights or GeoScoreWeights()
        self._weights.validate()

    async def execute(self, data: EventCandidate) -> EventCandidate:
        if data.latitude is not None and data.longitude is not None:
            decision: GeoDecision = (
                "accepted" if self._in_allowed_area(data.latitude, data.longitude) else "rejected"
            )
            geo_update: dict[str, Any] = {
                "geo_query": data.geo_query or "explicit_coordinates",
                "geo_provider": data.geo_provider or "explicit",
                "geo_source": data.geo_provider or "explicit",
                "geo_decision": decision,
                "city": data.city,
                "state": data.state,
                "country_code": data.country_code,
                "geo_score_breakdown": {
                    "text_similarity": 1.0,
                    "city_match": 1.0,
                    "state_match": 1.0,
                    "country_match": 1.0,
                    "coordinate_in_allowed_area": 1.0 if decision == "accepted" else 0.0,
                    "provider_confidence": 1.0,
                    "catalog_exact_match": 0.0,
                },
                "matched_catalog_entry": data.matched_catalog_entry,
                "processing_status": ProcessingStatus.GEOLOCATED
                if decision == "accepted"
                else ProcessingStatus.REJECTED,
                "geo_precision": data.geo_precision or "explicit",
            }
            return data.model_copy(update=geo_update)

        result = await self.classify(data)
        update: dict[str, Any] = {
            "geo_query": result.geo_query,
            "geo_provider": result.provider,
            "geo_decision": result.decision,
            "geo_score_breakdown": result.score_breakdown,
            "matched_catalog_entry": result.matched_catalog_entry,
            "evidence": self._with_evidence(
                data,
                geo_query=result.geo_query,
                geo_provider=result.provider,
                geo_source=result.provider or result.decision,
                geo_decision=result.decision,
                geo_confidence=f"{result.confidence:.3f}",
                geo_reason=", ".join(result.reasons) if result.reasons else "classified",
            ),
        }

        if result.latitude is not None:
            update["latitude"] = result.latitude
        if result.longitude is not None:
            update["longitude"] = result.longitude
        update["city"] = result.city
        update["state"] = result.state
        update["country_code"] = result.country_code
        if result.decision in {"accepted", "provisional"}:
            update["processing_status"] = ProcessingStatus.GEOLOCATED
            update["geo_precision"] = result.precision or result.decision
        elif result.decision == "manual_review" or result.decision == "unresolved":
            update["processing_status"] = ProcessingStatus.PENDING_REVIEW
            update["geo_precision"] = result.precision or result.decision
        else:
            update["processing_status"] = ProcessingStatus.REJECTED
            update["geo_precision"] = result.precision or result.decision

        return data.model_copy(update=update)

    async def classify(self, data: EventCandidate) -> GeoClassificationResult:
        original_text = self._original_text(data)
        normalized_text = normalize_location_text(original_text)
        reasons: list[str] = []

        if not normalized_text:
            return GeoClassificationResult(
                original_text=original_text,
                normalized_text="",
                decision="unresolved",
                confidence=0.0,
                reasons=["missing_location_text"],
            )

        catalog_candidates = [
            match
            for match in (
                self._catalog.search(original_text),
                self._catalog.search(normalized_text),
            )
            if match is not None
        ]
        catalog_match = (
            max(catalog_candidates, key=lambda match: match.score) if catalog_candidates else None
        )
        if catalog_match is not None and (
            catalog_match.exact or catalog_match.score >= self._catalog_threshold
        ):
            return self._result_from_catalog_match(
                original_text=original_text,
                normalized_text=normalized_text,
                catalog_match=catalog_match,
            )

        provider_candidates = await self._resolve_provider_candidates(data, normalized_text)
        if not provider_candidates:
            return GeoClassificationResult(
                original_text=original_text,
                normalized_text=normalized_text,
                decision="unresolved",
                confidence=0.0,
                reasons=["no_geocoding_candidates"],
            )

        ordered_candidates = sorted(
            provider_candidates,
            key=lambda candidate: self._normalize_float(
                candidate.provider_confidence or candidate.provider_importance
            ),
            reverse=True,
        )
        if len(ordered_candidates) > 1:
            top_score = self._normalize_float(
                ordered_candidates[0].provider_confidence
                or ordered_candidates[0].provider_importance
            )
            second_score = self._normalize_float(
                ordered_candidates[1].provider_confidence
                or ordered_candidates[1].provider_importance
            )
            if (top_score - second_score) < 0.1:
                confidence, breakdown, top_candidate = self._score_candidate(
                    original_text=original_text,
                    normalized_text=normalized_text,
                    candidate=ordered_candidates[0],
                )
                return GeoClassificationResult(
                    original_text=original_text,
                    normalized_text=normalized_text,
                    decision="manual_review",
                    confidence=confidence,
                    latitude=top_candidate.latitude,
                    longitude=top_candidate.longitude,
                    city=top_candidate.city,
                    state=top_candidate.state,
                    country_code=top_candidate.country_code,
                    precision=top_candidate.precision,
                    matched_catalog_entry=self._normalize_optional_str(
                        breakdown.get("matched_catalog_entry")
                    ),
                    provider=top_candidate.provider,
                    reasons=["multiple_close_matches"] + self._breakdown_reasons(breakdown),
                    score_breakdown={
                        key: float(value)
                        for key, value in breakdown.items()
                        if key not in {"reasons", "matched_catalog_entry"}
                    },
                    geo_query=top_candidate.query,
                )

        best = max(
            (
                self._score_candidate(
                    original_text=original_text,
                    normalized_text=normalized_text,
                    candidate=candidate,
                )
                for candidate in provider_candidates
            ),
            key=lambda item: item[0],
        )
        confidence, breakdown, candidate = best
        decision: str = self._decision_from_confidence(confidence)
        if (
            candidate.country_code
            and candidate.country_code.casefold() != self._allowed_country_code()
        ):
            decision = REJECTED_DECISION
            reasons.append("country_out_of_scope")
        if (
            candidate.latitude is not None
            and candidate.longitude is not None
            and not self._in_allowed_area(candidate.latitude, candidate.longitude)
        ):
            decision = REJECTED_DECISION
            reasons.append("outside_allowed_area")

        if candidate.city and normalize_location_text(candidate.city) == "posadas":
            reasons.append("city_matches_posadas")
        if candidate.state and normalize_location_text(candidate.state) == "misiones":
            reasons.append("state_matches_misiones")

        if confidence < self._threshold_reject and decision != "rejected":
            decision = REJECTED_DECISION

        return GeoClassificationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            decision=cast(GeoDecision, decision),
            confidence=confidence,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            city=candidate.city,
            state=candidate.state,
            country_code=candidate.country_code,
            precision=candidate.precision,
            matched_catalog_entry=self._normalize_optional_str(
                breakdown.get("matched_catalog_entry")
            ),
            provider=candidate.provider,
            reasons=reasons + self._breakdown_reasons(breakdown),
            score_breakdown={
                key: float(value)
                for key, value in breakdown.items()
                if key not in {"reasons", "matched_catalog_entry"}
            },
            geo_query=candidate.query,
        )

    def _result_from_catalog_match(
        self,
        *,
        original_text: str,
        normalized_text: str,
        catalog_match: CatalogMatch,
    ) -> GeoClassificationResult:
        entry = catalog_match.entry
        in_allowed_area = (
            self._in_allowed_area(entry.latitude, entry.longitude)
            if entry.latitude is not None and entry.longitude is not None
            else False
        )
        confidence = self._compose_confidence(
            text_similarity=catalog_match.score,
            city_match=self._match_city(entry.city),
            state_match=self._match_state(entry.state),
            country_match=self._match_country(entry.country_code),
            coordinate_in_allowed_area=1.0 if in_allowed_area else 0.0,
            provider_confidence=1.0,
            catalog_exact_match=1.0 if catalog_match.exact else 0.0,
        )
        decision = self._decision_from_confidence(confidence)
        if not entry.allowed:
            decision = REJECTED_DECISION
        if entry.country_code and entry.country_code.casefold() != self._allowed_country_code():
            decision = "rejected"
        if entry.latitude is not None and entry.longitude is not None and not in_allowed_area:
            decision = "rejected"

        return GeoClassificationResult(
            original_text=original_text,
            normalized_text=normalized_text,
            decision=decision,
            confidence=confidence,
            latitude=entry.latitude,
            longitude=entry.longitude,
            city=entry.city,
            state=entry.state,
            country_code=entry.country_code,
            precision="catalog",
            matched_catalog_entry=entry.name,
            provider="catalog",
            reasons=["catalog_exact_match" if catalog_match.exact else "catalog_fuzzy_match"],
            score_breakdown={
                "text_similarity": catalog_match.score,
                "city_match": self._match_city(entry.city),
                "state_match": self._match_state(entry.state),
                "country_match": self._match_country(entry.country_code),
                "coordinate_in_allowed_area": 1.0 if in_allowed_area else 0.0,
                "provider_confidence": 1.0,
                "catalog_exact_match": 1.0 if catalog_match.exact else 0.0,
            },
            geo_query=normalized_text,
        )

    async def _resolve_provider_candidates(
        self,
        data: EventCandidate,
        normalized_text: str,
    ) -> list[GeocodingCandidate]:
        queries = self._build_queries(data, normalized_text)
        for query in queries:
            cache_key = normalize_location_text(query)
            cached = self._venue_cache.get(cache_key) or self._venue_cache.get(query)
            if cached is not None:
                candidates = self._normalize_provider_response(cached, query=query)
                if candidates:
                    return candidates

            response = await self._invoke_geocoder(query)
            candidates = self._normalize_provider_response(response, query=query)
            if candidates:
                return candidates
        return []

    async def _invoke_geocoder(self, query: str) -> Any:
        if hasattr(self._geocoding_client, "search"):
            candidates = await self._geocoding_client.search(
                query,
                country_code=self._allowed_country_code(),
                limit=5,
            )
            return [
                candidate.model_dump() if hasattr(candidate, "model_dump") else candidate
                for candidate in candidates
            ]
        if hasattr(self._geocoding_client, "geocode"):
            return await self._geocoding_client.geocode(query=query)
        return {}

    def _normalize_provider_response(
        self,
        response: object,
        *,
        query: str,
    ) -> list[GeocodingCandidate]:
        if isinstance(response, list):
            candidates: list[GeocodingCandidate] = []
            for item in response:
                candidate = self._candidate_from_response_item(item, query=query)
                if candidate is not None:
                    candidates.append(candidate)
            return candidates
        if isinstance(response, dict):
            if "candidates" in response and isinstance(response.get("candidates"), list):
                return self._normalize_provider_response(response["candidates"], query=query)
            candidate = self._candidate_from_response_item(response, query=query)
            return [candidate] if candidate is not None else []
        return []

    def _candidate_from_response_item(
        self, item: object, *, query: str
    ) -> GeocodingCandidate | None:
        if isinstance(item, GeocodingCandidate):
            return item.model_copy(update={"query": query})
        if not isinstance(item, dict):
            return None

        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            return None
        display_name = str(item.get("display_name") or item.get("normalized_name") or query)
        provider = str(item.get("provider") or "unknown")
        normalized_name = str(item.get("normalized_name") or normalize_location_text(display_name))
        return GeocodingCandidate(
            provider=provider,
            display_name=display_name,
            normalized_name=normalized_name,
            latitude=float(lat),
            longitude=float(lon),
            country_code=self._normalize_optional_str(item.get("country_code")),
            state=self._normalize_optional_str(item.get("state")),
            city=self._normalize_optional_str(item.get("city")),
            postcode=self._normalize_optional_str(item.get("postcode")),
            precision=self._normalize_optional_str(item.get("precision"))
            or self._normalize_optional_str(item.get("geo_precision")),
            provider_importance=self._normalize_float(
                item.get("provider_importance") or item.get("importance") or item.get("score")
            ),
            provider_confidence=self._normalize_float(
                item.get("provider_confidence")
                or item.get("confidence")
                or item.get("score")
                or item.get("importance")
            ),
            raw_reference=self._normalize_optional_str(item.get("raw_reference")) or display_name,
            query=query,
            metadata={k: str(v) for k, v in (item.get("metadata") or {}).items()}
            if isinstance(item.get("metadata"), dict)
            else {},
        )

    def _score_candidate(
        self,
        *,
        original_text: str,
        normalized_text: str,
        candidate: GeocodingCandidate,
    ) -> tuple[float, dict[str, Any], GeocodingCandidate]:
        text_similarity = self._combined_text_similarity(normalized_text, candidate.normalized_name)
        coordinate_in_allowed_area = (
            1.0 if self._in_allowed_area(candidate.latitude, candidate.longitude) else 0.0
        )
        city_match = self._match_city(candidate.city) or coordinate_in_allowed_area
        state_match = self._match_state(candidate.state) or coordinate_in_allowed_area
        country_match = self._match_country(candidate.country_code) or coordinate_in_allowed_area
        provider_confidence = self._normalize_float(
            candidate.provider_confidence or candidate.provider_importance
        )
        catalog_match = self._catalog.search(candidate.display_name) or self._catalog.search(
            original_text
        )
        catalog_exact_match = 1.0 if catalog_match and catalog_match.exact else 0.0
        matched_catalog_entry = catalog_match.entry.name if catalog_match else None

        confidence = self._compose_confidence(
            text_similarity=text_similarity,
            city_match=city_match,
            state_match=state_match,
            country_match=country_match,
            coordinate_in_allowed_area=coordinate_in_allowed_area,
            provider_confidence=provider_confidence,
            catalog_exact_match=catalog_exact_match,
        )
        reasons: list[str] = []
        if catalog_exact_match:
            reasons.append("catalog_match")
        if country_match < 1.0:
            reasons.append("country_mismatch")
        if coordinate_in_allowed_area < 1.0:
            reasons.append("outside_allowed_area")

        breakdown: dict[str, float | str | list[str]] = {
            "text_similarity": text_similarity,
            "city_match": city_match,
            "state_match": state_match,
            "country_match": country_match,
            "coordinate_in_allowed_area": coordinate_in_allowed_area,
            "provider_confidence": provider_confidence,
            "catalog_exact_match": catalog_exact_match,
            "matched_catalog_entry": matched_catalog_entry or "",
            "reasons": reasons,
        }
        return confidence, breakdown, candidate

    def _breakdown_reasons(self, breakdown: Mapping[str, Any]) -> list[str]:
        reasons = breakdown.get("reasons")
        if isinstance(reasons, list) and all(isinstance(reason, str) for reason in reasons):
            return list(reasons)
        return []

    def _compose_confidence(
        self,
        *,
        text_similarity: float,
        city_match: float,
        state_match: float,
        country_match: float,
        coordinate_in_allowed_area: float,
        provider_confidence: float,
        catalog_exact_match: float,
    ) -> float:
        confidence = (
            text_similarity * self._weights.text_similarity
            + city_match * self._weights.city_match
            + state_match * self._weights.state_match
            + country_match * self._weights.country_match
            + coordinate_in_allowed_area * self._weights.coordinate_in_allowed_area
            + provider_confidence * self._weights.provider_confidence
            + catalog_exact_match * self._weights.catalog_exact_match
        )
        return max(0.0, min(1.0, confidence))

    def _decision_from_confidence(self, confidence: float) -> GeoDecision:
        if confidence >= self._threshold_auto:
            return "accepted"
        if confidence >= self._threshold_review:
            return "provisional"
        if confidence >= self._threshold_reject:
            return "manual_review"
        return "rejected"

    def _combined_text_similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        scores = (
            fuzz.WRatio(left, right),
            fuzz.token_set_ratio(left, right),
            fuzz.token_sort_ratio(left, right),
        )
        return max(scores) / 100.0

    def _match_city(self, city: str | None) -> float:
        if not city:
            return 0.0
        normalized = normalize_location_text(city)
        if normalized == "posadas":
            return 1.0
        if "posadas" in normalized:
            return 0.9
        return 0.0

    def _match_state(self, state: str | None) -> float:
        if not state:
            return 0.0
        normalized = normalize_location_text(state)
        if normalized == "misiones":
            return 1.0
        if "misiones" in normalized:
            return 0.9
        return 0.0

    def _match_country(self, country_code: str | None) -> float:
        if not country_code:
            return 0.0
        return 1.0 if country_code.casefold() == self._allowed_country_code() else 0.0

    def _in_allowed_area(self, latitude: float | None, longitude: float | None) -> bool:
        if latitude is None or longitude is None:
            return False
        settings = get_settings()
        if settings.has_geo_allowed_bbox:
            min_lat = settings.geo_allowed_min_latitude
            max_lat = settings.geo_allowed_max_latitude
            min_lon = settings.geo_allowed_min_longitude
            max_lon = settings.geo_allowed_max_longitude
            assert min_lat is not None
            assert max_lat is not None
            assert min_lon is not None
            assert max_lon is not None
            return min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon
        distance = _haversine_km(latitude, longitude, self._base_latitude, self._base_longitude)
        return distance is not None and distance <= self._search_radius_km

    def _allowed_country_code(self) -> str:
        return get_settings().geocoding_allowed_country_code.casefold()

    def _build_queries(self, data: EventCandidate, normalized_text: str) -> list[str]:
        candidates = [
            data.address,
            data.venue_name,
            data.geo_query,
            data.evidence.get("address"),
            data.evidence.get("venue_name"),
        ]
        expanded = [value for value in candidates if isinstance(value, str) and value.strip()]
        if data.venue_name:
            expanded.extend(
                [
                    f"{data.venue_name}, Posadas, Misiones, Argentina",
                    f"{data.venue_name}, Misiones, Argentina",
                ]
            )
        if normalized_text:
            expanded.append(normalized_text)
        seen: set[str] = set()
        unique: list[str] = []
        for query in expanded:
            normalized = normalize_location_text(query)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(query)
        return unique

    def _original_text(self, data: EventCandidate) -> str:
        pieces = [
            piece
            for piece in (
                data.address,
                data.venue_name,
                data.geo_query,
                data.evidence.get("address"),
                data.evidence.get("venue_name"),
                data.evidence.get("geo_query"),
            )
            if isinstance(piece, str) and piece.strip()
        ]
        if pieces:
            return ", ".join(dict.fromkeys(pieces))
        return ""

    def _normalize_optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _normalize_float(self, value: object) -> float:
        if isinstance(value, int | float):
            return max(0.0, min(1.0, float(value)))
        return 0.0

    def _with_evidence(self, data: EventCandidate, **extra: object) -> dict[str, str]:
        evidence = dict(data.evidence)
        for key, value in extra.items():
            if value is not None:
                evidence[key] = str(value)
        return evidence
