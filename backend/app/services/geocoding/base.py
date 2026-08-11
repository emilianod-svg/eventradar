"""Interfaz de geocodificación (sección 8.6 del plan).

Nominatim es una API pública que no requiere API key, pero sí exige una
política de uso responsable: un `User-Agent`/contacto identificable y un
rate limit razonable (sección 3, checklist de recursos). Por eso el cliente
falla explícitamente si no hay un contacto configurado, aunque técnicamente
no haga falta ningún secreto.
"""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError


class GeocodingResult(Protocol):
    latitude: float
    longitude: float
    precision: str


class GeocodingClient(Protocol):
    async def geocode(self, *, query: str) -> dict: ...


class NotConfiguredGeocodingClient:
    async def geocode(self, *, query: str) -> dict:
        raise ExternalServiceNotConfiguredError(
            "NOMINATIM_CONTACT_EMAIL no está configurado. La política de uso "
            "de Nominatim exige un contacto identificable antes de emitir "
            "consultas (ver checklist de recursos externos)."
        )


def get_geocoding_client() -> GeocodingClient:
    settings = get_settings()
    if not settings.nominatim_contact_email:
        return NotConfiguredGeocodingClient()
    # TODO: implementar el cliente HTTP real con caché de venues y rate
    # limiting (sección 8.6). Pendiente de esta inicialización.
    raise NotImplementedError(
        "Cliente Nominatim: contacto configurado pero lógica de "
        "geocodificación todavía no implementada."
    )
