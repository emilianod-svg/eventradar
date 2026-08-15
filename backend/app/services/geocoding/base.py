"""Interfaz de geocodificación (sección 8.6 del plan).

Nominatim es una API pública que no requiere API key, pero sí exige una
política de uso responsable: un `User-Agent`/contacto identificable y un
rate limit razonable (sección 3, checklist de recursos). Por eso el cliente
falla explícitamente si no hay un contacto configurado, aunque técnicamente
no haga falta ningún secreto.

Si `GOOGLE_GEOCODING_ENABLED=true`, se usa Google como fallback cuando
Nominatim no devuelve un resultado útil o falla la consulta.
"""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

import httpx

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError


class GeocodingResult(Protocol):
    latitude: float
    longitude: float
    precision: str


class GeocodingClient(Protocol):
    async def geocode(self, *, query: str) -> dict: ...


def _is_precise_result(result: dict) -> bool:
    return (
        result.get("latitude") is not None
        and result.get("longitude") is not None
        and not result.get("candidates")
    )


class NominatimGeocodingClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.nominatim_base_url.rstrip("/")
        self._user_agent = settings.nominatim_user_agent
        self._contact_email = settings.nominatim_contact_email or ""
        self._rate_limit_seconds = max(settings.nominatim_rate_limit_seconds, 0.0)
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def geocode(self, *, query: str) -> dict:
        await self._respect_rate_limit()
        headers = {"User-Agent": self._user_agent}
        params: dict[str, str | int] = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
        }
        if self._contact_email:
            params["email"] = self._contact_email

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(f"{self._base_url}/search", params=params)
            response.raise_for_status()
            results = response.json()

        if not results:
            return {}

        parsed = sorted(
            (self._normalize_result(item) for item in results if isinstance(item, dict)),
            key=lambda item: float(item.get("score", 0.0)),
            reverse=True,
        )
        if not parsed:
            return {}
        if len(parsed) == 1:
            return parsed[0]
        return {"provider": "nominatim", "query": query, "candidates": parsed}

    async def _respect_rate_limit(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request_at
            wait_seconds = self._rate_limit_seconds - elapsed
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_request_at = time.monotonic()

    def _normalize_result(self, item: dict) -> dict:
        latitude = item.get("lat") or item.get("latitude")
        longitude = item.get("lon") or item.get("longitude")
        return {
            "latitude": float(latitude) if latitude is not None else None,
            "longitude": float(longitude) if longitude is not None else None,
            "precision": item.get("type") or item.get("class") or "unknown",
            "display_name": item.get("display_name"),
            "score": float(item.get("importance", 0.0) or 0.0),
            "provider": "nominatim",
            "raw": item,
        }


class GoogleGeocodingClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.google_geocoding_base_url.rstrip("/")
        self._api_key = settings.google_geocoding_api_key or ""

    async def geocode(self, *, query: str) -> dict:
        if not self._api_key:
            raise ExternalServiceNotConfiguredError(
                "GOOGLE_GEOCODING_API_KEY no está configurado. Si activás el "
                "fallback de Google, necesitás una API key válida."
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self._base_url,
                params={"address": query, "key": self._api_key},
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "OK":
            return {}

        results = payload.get("results", [])
        if not isinstance(results, list) or not results:
            return {}

        parsed = sorted(
            (self._normalize_result(item) for item in results if isinstance(item, dict)),
            key=lambda item: float(item.get("score", 0.0)),
            reverse=True,
        )
        if not parsed:
            return {}
        if len(parsed) == 1:
            return parsed[0]
        return {"provider": "google", "query": query, "candidates": parsed}

    def _normalize_result(self, item: dict) -> dict:
        geometry = item.get("geometry") if isinstance(item.get("geometry"), dict) else {}
        location = geometry.get("location", {}) if isinstance(geometry, dict) else {}
        location_type = geometry.get("location_type") if isinstance(geometry, dict) else None
        score_map = {
            "ROOFTOP": 0.98,
            "RANGE_INTERPOLATED": 0.85,
            "GEOMETRIC_CENTER": 0.70,
            "APPROXIMATE": 0.55,
        }
        score = score_map.get(str(location_type).upper(), 0.50)
        if item.get("partial_match"):
            score -= 0.10
        return {
            "latitude": float(location["lat"]) if location.get("lat") is not None else None,
            "longitude": float(location["lng"]) if location.get("lng") is not None else None,
            "precision": str(location_type or "unknown").lower(),
            "display_name": item.get("formatted_address"),
            "score": max(0.0, min(1.0, score)),
            "provider": "google",
            "raw": item,
        }


class FallbackGeocodingClient:
    def __init__(self, primary: GeocodingClient, fallback: GeocodingClient) -> None:
        self._primary = primary
        self._fallback = fallback

    async def geocode(self, *, query: str) -> dict:
        try:
            primary_result = await self._primary.geocode(query=query)
        except Exception:
            primary_result = {}

        if _is_precise_result(primary_result):
            return primary_result

        fallback_result = await self._fallback.geocode(query=query)
        if fallback_result:
            return fallback_result
        return primary_result


class NotConfiguredGeocodingClient:
    async def geocode(self, *, query: str) -> dict:
        raise ExternalServiceNotConfiguredError(
            "NOMINATIM_CONTACT_EMAIL no está configurado. La política de uso "
            "de Nominatim exige un contacto identificable antes de emitir "
            "consultas (ver checklist de recursos externos)."
        )


def get_geocoding_client() -> GeocodingClient:
    settings = get_settings()
    google_enabled = settings.google_geocoding_enabled and bool(settings.google_geocoding_api_key)
    nominatim_enabled = bool(settings.nominatim_contact_email)

    if nominatim_enabled and google_enabled:
        return FallbackGeocodingClient(NominatimGeocodingClient(), GoogleGeocodingClient())
    if nominatim_enabled:
        return NominatimGeocodingClient()
    if google_enabled:
        return GoogleGeocodingClient()
    return NotConfiguredGeocodingClient()
