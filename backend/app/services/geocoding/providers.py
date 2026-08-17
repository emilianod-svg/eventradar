"""Proveedores de geocodificación y cadena de fallback."""

from __future__ import annotations

from collections.abc import Callable, Sequence

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
    def __init__(self, providers: Sequence[GeocodingProvider]) -> None:
        self.providers = list(providers)

    async def search(
        self,
        query: str,
        *,
        country_code: str | None = None,
        limit: int = 5,
    ) -> list[GeocodingCandidate]:
        for provider in self.providers:
            candidates = await provider.search(query, country_code=country_code, limit=limit)
            if candidates:
                return candidates
        return []
