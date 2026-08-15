"""Agente Clasificador Geográfico (sección 8.6).

Orden de resolución: coordenadas explícitas -> dirección completa ->
`lugar + Posadas + Misiones + Argentina` -> caché de venues -> revisión
manual. Depende de `app.services.geocoding` (Nominatim) y de las
configuraciones base de Posadas para el filtro por radio.
"""

from __future__ import annotations

from collections.abc import Mapping
from math import asin, cos, radians, sin, sqrt
from typing import Any

from app.config import get_settings
from app.domain.entities import EventCandidate
from app.domain.enums import ProcessingStatus
from app.services.geocoding.base import GeocodingClient, get_geocoding_client


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


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.casefold().split())


class GeoClassifierAgent:
    def __init__(
        self,
        geocoding_client: GeocodingClient | None = None,
        venue_cache: Mapping[str, dict[str, Any]] | None = None,
        base_latitude: float | None = None,
        base_longitude: float | None = None,
        search_radius_km: float | None = None,
    ) -> None:
        settings = get_settings()
        self._geocoding_client = geocoding_client or get_geocoding_client()
        self._venue_cache = dict(venue_cache or {})
        self._base_latitude = settings.base_latitude if base_latitude is None else base_latitude
        self._base_longitude = settings.base_longitude if base_longitude is None else base_longitude
        self._search_radius_km = (
            settings.search_radius_km if search_radius_km is None else search_radius_km
        )

    async def execute(self, data: EventCandidate) -> EventCandidate:
        if data.latitude is not None and data.longitude is not None:
            return self._finalize(
                data,
                latitude=data.latitude,
                longitude=data.longitude,
                precision=data.geo_precision or "explicit",
                query=data.geo_query or "explicit_coordinates",
            )

        queries = self._build_queries(data)
        if not queries:
            return data.model_copy(
                update={
                    "processing_status": ProcessingStatus.REJECTED,
                    "evidence": self._with_evidence(data, geo_reason="missing_location"),
                }
            )

        for query in queries:
            cached = self._venue_cache.get(_normalize_key(query))
            if cached is not None:
                return self._handle_geocode_result(data, cached, query=query, from_cache=True)

            result = await self._geocoding_client.geocode(query=query)
            decision = self._handle_geocode_result(data, result, query=query, from_cache=False)
            if decision.processing_status == ProcessingStatus.GEOLOCATED:
                return decision
            if (
                decision.processing_status == ProcessingStatus.PENDING_REVIEW
                and decision.evidence.get("geo_reason") == "multiple_close_matches"
            ):
                return decision
            if decision.processing_status == ProcessingStatus.REJECTED:
                return decision

        return data.model_copy(
            update={
                "processing_status": ProcessingStatus.PENDING_REVIEW,
                "evidence": self._with_evidence(data, geo_reason="no_unambiguous_match"),
            }
        )

    def _build_queries(self, data: EventCandidate) -> list[str]:
        queries: list[str] = []
        address = _first_string(data.address, data.evidence.get("address"))
        venue_name = _first_string(data.venue_name, data.evidence.get("venue_name"))

        if address:
            queries.append(address)
        if venue_name:
            queries.append(f"{venue_name}, Posadas, Misiones, Argentina")
            queries.append(venue_name)

        seen: set[str] = set()
        unique_queries: list[str] = []
        for query in queries:
            normalized = _normalize_key(query)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_queries.append(query)
        return unique_queries

    def _handle_geocode_result(
        self,
        data: EventCandidate,
        result: dict[str, Any],
        *,
        query: str,
        from_cache: bool,
    ) -> EventCandidate:
        candidates = result.get("candidates")
        provider = _first_string(result.get("provider"), "nominatim") or "nominatim"
        if isinstance(candidates, list) and candidates:
            ordered = sorted(
                candidates,
                key=lambda item: float(item.get("score", 0.0)),
                reverse=True,
            )
            top = ordered[0]
            if (
                len(ordered) > 1
                and float(top.get("score", 0.0)) - float(ordered[1].get("score", 0.0)) < 0.1
            ):
                return data.model_copy(
                    update={
                        "processing_status": ProcessingStatus.PENDING_REVIEW,
                        "geo_query": query,
                        "evidence": self._with_evidence(
                            data,
                            geo_query=query,
                            geo_precision="ambiguous",
                            geo_reason="multiple_close_matches",
                            geo_source="cache" if from_cache else provider,
                        ),
                    }
                )
            return self._handle_geocode_result(
                data,
                top,
                query=query,
                from_cache=from_cache,
            )

        latitude = result.get("latitude")
        longitude = result.get("longitude")
        if latitude is None or longitude is None:
            return data.model_copy(
                update={
                    "processing_status": ProcessingStatus.PENDING_REVIEW,
                    "geo_query": query,
                    "evidence": self._with_evidence(
                        data,
                        geo_query=query,
                        geo_reason="no_coordinates_returned",
                        geo_source="cache" if from_cache else provider,
                    ),
                }
            )

        precision = (
            _first_string(result.get("precision"), result.get("geo_precision"), "estimated")
            or "estimated"
        )
        return self._finalize(
            data,
            latitude=float(latitude),
            longitude=float(longitude),
            precision=precision,
            query=query,
            source="cache" if from_cache else provider,
        )

    def _finalize(
        self,
        data: EventCandidate,
        *,
        latitude: float,
        longitude: float,
        precision: str,
        query: str,
        source: str = "nominatim",
    ) -> EventCandidate:
        distance = _haversine_km(latitude, longitude, self._base_latitude, self._base_longitude)
        if distance is not None and distance > self._search_radius_km:
            return data.model_copy(
                update={
                    "latitude": latitude,
                    "longitude": longitude,
                    "geo_precision": precision,
                    "geo_query": query,
                    "processing_status": ProcessingStatus.REJECTED,
                    "evidence": self._with_evidence(
                        data,
                        geo_query=query,
                        geo_precision=precision,
                        geo_source=source,
                        geo_reason=f"outside_radius_{distance:.2f}km",
                    ),
                }
            )

        return data.model_copy(
            update={
                "latitude": latitude,
                "longitude": longitude,
                "geo_precision": precision,
                "geo_query": query,
                "processing_status": ProcessingStatus.GEOLOCATED,
                "evidence": self._with_evidence(
                    data,
                    geo_query=query,
                    geo_precision=precision,
                    geo_source=source,
                ),
            }
        )

    def _with_evidence(self, data: EventCandidate, **extra: str) -> dict[str, str]:
        evidence = dict(data.evidence)
        for key, value in extra.items():
            evidence[key] = value
        return evidence
