"""Proveedores de geocodificación y cadena de fallback."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from math import sqrt

import httpx

from app.services.geocoding.cache import GeocodingCache, InMemoryGeocodingCache
from app.services.geocoding.normalization import normalize_location_text
from app.services.geocoding.resilience import AsyncRateLimiter, CircuitBreaker, jitter
from app.services.geocoding.types import GeocodingCandidate, GeocodingProvider


def _mapping_or_empty(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _haversine_m(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    from math import asin, cos, radians, sin

    radius_m = 6_371_000.0
    lat1 = radians(latitude_a)
    lon1 = radians(longitude_a)
    lat2 = radians(latitude_b)
    lon2 = radians(longitude_b)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    hav = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 2 * radius_m * asin(sqrt(hav))


class _HttpGeocodingProvider:
    provider_name = "provider"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        enabled: bool,
        cache: GeocodingCache | None,
        min_interval_seconds: float,
        failure_threshold: int,
        reset_seconds: float,
        max_attempts: int,
        backoff_base_seconds: float,
        backoff_jitter_seconds: float,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.cache = cache or InMemoryGeocodingCache()
        self.rate_limiter = AsyncRateLimiter(min_interval_seconds)
        self.circuit_breaker = CircuitBreaker(failure_threshold, reset_seconds)
        self.max_attempts = max_attempts
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_jitter_seconds = backoff_jitter_seconds
        self.client_factory = client_factory

    async def search(
        self,
        query: str,
        *,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[GeocodingCandidate]:
        if not self.enabled or not self.circuit_breaker.allow_request():
            return []

        cache_key = self._cache_key(query, country_code=country_code, limit=limit)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return list(cached.candidates)

        await self.rate_limiter.wait()
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                async with self.client_factory(timeout=self.timeout_seconds) as client:
                    response = await client.get(
                        self.request_url,
                        params=self.request_params(query, country_code=country_code, limit=limit),
                        headers=self.request_headers,
                    )
                if response.status_code in {400, 401, 403}:
                    self.circuit_breaker.record_failure()
                    return []
                if response.status_code == 429 or response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                    last_error = httpx.HTTPStatusError(
                        f"HTTP {response.status_code}", request=response.request, response=response
                    )
                    if attempt < self.max_attempts - 1:
                        import asyncio

                        await asyncio.sleep(
                            jitter(self.backoff_base_seconds, self.backoff_jitter_seconds, attempt)
                        )
                        continue
                    break
                response.raise_for_status()
                candidates = self.normalize_response(response.json(), query=query)
                self.circuit_breaker.record_success()
                self._cache_result(cache_key, candidates)
                return candidates
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                self.circuit_breaker.record_failure()
                if attempt < self.max_attempts - 1:
                    import asyncio

                    await asyncio.sleep(
                        jitter(self.backoff_base_seconds, self.backoff_jitter_seconds, attempt)
                    )
                    continue
                break

        if last_error is not None:
            self._cache_result(cache_key, [], negative=True)
        return []

    def _cache_key(self, query: str, *, country_code: str | None, limit: int) -> str:
        return "|".join(
            (
                self.provider_name,
                normalize_location_text(query),
                (country_code or "").casefold(),
                str(limit),
            )
        )

    def _cache_result(
        self,
        key: str,
        candidates: list[GeocodingCandidate],
        *,
        negative: bool = False,
    ) -> None:
        from app.config import get_settings

        settings = get_settings()
        ttl = (
            settings.geocoding_negative_cache_ttl_seconds
            if negative
            else settings.geocoding_cache_ttl_seconds
        )
        self.cache.set(key, candidates, ttl_seconds=ttl, negative=negative)

    @property
    def request_url(self) -> str:
        return f"{self.base_url}{self.request_path}"

    @property
    def request_path(self) -> str:
        return "/search"

    @property
    def request_headers(self) -> dict[str, str]:
        return {}

    def request_params(
        self,
        query: str,
        *,
        country_code: str | None,
        limit: int,
    ) -> dict[str, str | int | float]:
        raise NotImplementedError

    def normalize_response(self, payload: object, *, query: str) -> list[GeocodingCandidate]:
        raise NotImplementedError


class NominatimGeocodingProvider(_HttpGeocodingProvider):
    provider_name = "nominatim"

    @property
    def request_headers(self) -> dict[str, str]:
        from app.config import get_settings

        settings = get_settings()
        return {"User-Agent": settings.nominatim_user_agent}

    def request_params(
        self,
        query: str,
        *,
        country_code: str | None,
        limit: int,
    ) -> dict[str, str | int | float]:
        from app.config import get_settings

        settings = get_settings()
        params: dict[str, str | int | float] = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "accept-language": "es",
            "limit": limit,
        }
        if country_code:
            params["countrycodes"] = country_code
        if settings.nominatim_contact_email:
            params["email"] = settings.nominatim_contact_email
        return params

    def normalize_response(self, payload: object, *, query: str) -> list[GeocodingCandidate]:
        if not isinstance(payload, list):
            return []
        candidates: list[GeocodingCandidate] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            address = _mapping_or_empty(item.get("address"))
            lat = _float_or_none(item.get("lat") or item.get("latitude"))
            lon = _float_or_none(item.get("lon") or item.get("longitude"))
            if lat is None or lon is None:
                continue
            city = None
            city = address.get("city") or address.get("town") or address.get("village")
            display_name = str(item.get("display_name") or query)
            country_code = _string_or_none(address.get("country_code"))
            candidates.append(
                GeocodingCandidate(
                    provider=self.provider_name,
                    display_name=display_name,
                    normalized_name=normalize_location_text(display_name),
                    latitude=lat,
                    longitude=lon,
                    country_code=(country_code.casefold() if country_code else None),
                    state=_string_or_none(address.get("state")),
                    city=_string_or_none(city),
                    postcode=_string_or_none(address.get("postcode")),
                    precision=str(
                        item.get("type")
                        or item.get("class")
                        or item.get("precision")
                        or "estimated"
                    ),
                    provider_importance=_float_or_none(item.get("importance")),
                    provider_confidence=_float_or_none(item.get("importance")),
                    raw_reference=str(item.get("place_id") or item.get("osm_id") or display_name),
                    query=query,
                    metadata={"source": "nominatim"},
                )
            )
        return candidates


class LocationIQGeocodingProvider(_HttpGeocodingProvider):
    provider_name = "locationiq"

    def request_params(
        self,
        query: str,
        *,
        country_code: str | None,
        limit: int,
    ) -> dict[str, str | int | float]:
        from app.config import get_settings

        settings = get_settings()
        params: dict[str, str | int | float] = {
            "q": query,
            "key": settings.locationiq_api_key or "",
            "format": "json",
            "addressdetails": 1,
            "accept-language": "es",
            "limit": limit,
        }
        if country_code:
            params["countrycodes"] = country_code
        return params

    def normalize_response(self, payload: object, *, query: str) -> list[GeocodingCandidate]:
        if not isinstance(payload, list):
            return []
        candidates: list[GeocodingCandidate] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            address = _mapping_or_empty(item.get("address"))
            lat = _float_or_none(item.get("lat") or item.get("latitude"))
            lon = _float_or_none(item.get("lon") or item.get("longitude"))
            if lat is None or lon is None:
                continue
            display_name = str(item.get("display_name") or query)
            country_code = _string_or_none(address.get("country_code"))
            location_name = _string_or_none(
                address.get("city") or address.get("town") or address.get("village")
            )
            candidates.append(
                GeocodingCandidate(
                    provider=self.provider_name,
                    display_name=display_name,
                    normalized_name=normalize_location_text(display_name),
                    latitude=lat,
                    longitude=lon,
                    country_code=(country_code.casefold() if country_code else None),
                    state=_string_or_none(address.get("state")),
                    city=location_name,
                    postcode=_string_or_none(address.get("postcode")),
                    precision=str(
                        item.get("type")
                        or item.get("class")
                        or item.get("precision")
                        or "estimated"
                    ),
                    provider_importance=_float_or_none(item.get("importance")),
                    provider_confidence=_float_or_none(item.get("importance")),
                    raw_reference=str(item.get("place_id") or display_name),
                    query=query,
                    metadata={"source": "locationiq"},
                )
            )
        return candidates


class GeoapifyGeocodingProvider(_HttpGeocodingProvider):
    provider_name = "geoapify"

    @property
    def request_path(self) -> str:
        return "/geocode/search"

    def request_params(
        self,
        query: str,
        *,
        country_code: str | None,
        limit: int,
    ) -> dict[str, str | int | float]:
        from app.config import get_settings

        settings = get_settings()
        params: dict[str, str | int | float] = {
            "text": query,
            "apiKey": settings.geoapify_api_key or "",
            "limit": limit,
            "lang": "es",
        }
        if country_code:
            params["filter"] = f"countrycode:{country_code}"
        return params

    def normalize_response(self, payload: object, *, query: str) -> list[GeocodingCandidate]:
        if not isinstance(payload, dict):
            return []
        features = payload.get("features")
        if not isinstance(features, list):
            return []
        candidates: list[GeocodingCandidate] = []
        for item in features:
            if not isinstance(item, dict):
                continue
            props = _mapping_or_empty(item.get("properties"))
            geometry = _mapping_or_empty(item.get("geometry"))
            coords = geometry.get("coordinates")
            if not isinstance(coords, list) or len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]
            lat_value = _float_or_none(lat)
            lon_value = _float_or_none(lon)
            if lat_value is None or lon_value is None:
                continue
            rank = _mapping_or_empty(props.get("rank"))
            precision = rank.get("precision") or props.get("result_type") or "estimated"
            country_code = _string_or_none(props.get("country_code"))
            location_name = _string_or_none(
                props.get("city") or props.get("town") or props.get("village")
            )
            candidates.append(
                GeocodingCandidate(
                    provider=self.provider_name,
                    display_name=str(props.get("formatted") or props.get("name") or query),
                    normalized_name=normalize_location_text(
                        str(props.get("formatted") or props.get("name") or query)
                    ),
                    latitude=lat_value,
                    longitude=lon_value,
                    country_code=(country_code.casefold() if country_code else None),
                    state=_string_or_none(props.get("state")),
                    city=location_name,
                    postcode=_string_or_none(props.get("postcode")),
                    precision=str(precision),
                    provider_importance=_float_or_none(rank.get("importance")),
                    provider_confidence=_float_or_none(rank.get("confidence")),
                    raw_reference=str(props.get("place_id") or props.get("result_type") or query),
                    query=query,
                    metadata={"source": "geoapify"},
                )
            )
        return candidates


class GeocodingProviderChain:
    def __init__(
        self,
        providers: Sequence[GeocodingProvider],
        *,
        consensus_min_providers: int | None = None,
        consensus_max_distance_meters: float | None = None,
    ) -> None:
        from app.config import get_settings

        settings = get_settings()
        self.providers = list(providers)
        self._consensus_min_providers = (
            settings.geocoding_consensus_min_providers
            if consensus_min_providers is None
            else consensus_min_providers
        )
        self._consensus_max_distance_meters = (
            settings.geocoding_consensus_max_distance_meters
            if consensus_max_distance_meters is None
            else consensus_max_distance_meters
        )

    async def search(
        self,
        query: str,
        *,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[GeocodingCandidate]:
        collected: list[GeocodingCandidate] = []
        for provider in self.providers:
            candidates = await provider.search(query, country_code=country_code, limit=limit)
            if candidates:
                collected.extend(candidates)

        if not collected:
            return []

        provider_names = {candidate.provider for candidate in collected}
        if len(provider_names) <= 1:
            return collected

        clusters = self._cluster_candidates(collected)
        representatives = [self._represent_cluster(cluster, query=query) for cluster in clusters]
        representatives.sort(key=self._cluster_sort_key, reverse=True)

        best = representatives[0]
        if (
            self._cluster_provider_count(best) >= self._consensus_min_providers
            and self._cluster_max_distance_m(best) <= self._consensus_max_distance_meters
        ):
            return [best]

        return representatives

    def _cluster_candidates(
        self, candidates: Sequence[GeocodingCandidate]
    ) -> list[list[GeocodingCandidate]]:
        ordered = sorted(candidates, key=self._candidate_score, reverse=True)
        clusters: list[list[GeocodingCandidate]] = []
        for candidate in ordered:
            placed = False
            for cluster in clusters:
                if any(
                    _haversine_m(
                        candidate.latitude,
                        candidate.longitude,
                        member.latitude,
                        member.longitude,
                    )
                    <= self._consensus_max_distance_meters
                    for member in cluster
                ):
                    cluster.append(candidate)
                    placed = True
                    break
            if not placed:
                clusters.append([candidate])
        return clusters

    def _represent_cluster(
        self,
        cluster: list[GeocodingCandidate],
        *,
        query: str,
    ) -> GeocodingCandidate:
        best = max(cluster, key=self._candidate_score)
        scores = [self._candidate_score(candidate) for candidate in cluster]
        weights = [score if score > 0.0 else 1.0 for score in scores]
        weight_total = sum(weights) or float(len(cluster))
        latitude = (
            sum(
                candidate.latitude * weight
                for candidate, weight in zip(cluster, weights, strict=False)
            )
            / weight_total
        )
        longitude = (
            sum(
                candidate.longitude * weight
                for candidate, weight in zip(cluster, weights, strict=False)
            )
            / weight_total
        )

        cluster_metadata = {
            "geo_cluster_provider_count": str(len({candidate.provider for candidate in cluster})),
            "geo_cluster_candidate_count": str(len(cluster)),
            "geo_cluster_providers": ",".join(
                sorted({candidate.provider for candidate in cluster})
            ),
            "geo_cluster_min_latitude": f"{min(candidate.latitude for candidate in cluster):.6f}",
            "geo_cluster_max_latitude": f"{max(candidate.latitude for candidate in cluster):.6f}",
            "geo_cluster_min_longitude": f"{min(candidate.longitude for candidate in cluster):.6f}",
            "geo_cluster_max_longitude": f"{max(candidate.longitude for candidate in cluster):.6f}",
            "geo_cluster_max_distance_m": f"{self._cluster_max_distance(cluster):.1f}",
            "geo_cluster_consensus": "true"
            if len({candidate.provider for candidate in cluster}) >= self._consensus_min_providers
            and self._cluster_max_distance(cluster) <= self._consensus_max_distance_meters
            else "false",
        }

        if cluster_metadata["geo_cluster_consensus"] == "true":
            return best.model_copy(
                update={
                    "provider": "consensus",
                    "display_name": best.display_name,
                    "normalized_name": best.normalized_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "precision": "consensus",
                    "provider_confidence": max(scores),
                    "provider_importance": max(scores),
                    "query": query,
                    "metadata": {**best.metadata, **cluster_metadata},
                }
            )

        return best.model_copy(
            update={"metadata": {**best.metadata, **cluster_metadata}, "query": query}
        )

    def _candidate_score(self, candidate: GeocodingCandidate) -> float:
        return candidate.provider_confidence or candidate.provider_importance or 0.0

    def _cluster_max_distance(self, cluster: Sequence[GeocodingCandidate]) -> float:
        if len(cluster) < 2:
            return 0.0
        max_distance = 0.0
        for index, left in enumerate(cluster):
            for right in cluster[index + 1 :]:
                max_distance = max(
                    max_distance,
                    _haversine_m(left.latitude, left.longitude, right.latitude, right.longitude),
                )
        return max_distance

    def _cluster_provider_count(self, candidate: GeocodingCandidate) -> int:
        value = candidate.metadata.get("geo_cluster_provider_count")
        return int(value) if isinstance(value, str) and value.isdigit() else 1

    def _cluster_max_distance_m(self, candidate: GeocodingCandidate) -> float:
        value = candidate.metadata.get("geo_cluster_max_distance_m")
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _cluster_sort_key(self, candidate: GeocodingCandidate) -> tuple[float, float, float]:
        return (
            float(self._cluster_provider_count(candidate)),
            self._candidate_score(candidate),
            -self._cluster_max_distance_m(candidate),
        )
