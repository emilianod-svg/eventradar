"""Geocodificación, catálogo local y proveedores de fallback."""

from app.services.geocoding.base import (
    FallbackGeocodingClient,
    GeocodingClient,
    NotConfiguredGeocodingClient,
    ProviderGeocodingClient,
    get_geocoding_client,
)
from app.services.geocoding.catalog import (
    CatalogMatch,
    LocationCatalog,
    LocationCatalogEntry,
    load_catalog,
)
from app.services.geocoding.normalization import (
    build_query_variants,
    normalize_location_text,
    strip_accents,
)
from app.services.geocoding.providers import (
    GeoapifyGeocodingProvider,
    GeocodingProviderChain,
    LocationIQGeocodingProvider,
    NominatimGeocodingProvider,
)
from app.services.geocoding.types import GeocodingCandidate, GeocodingProvider

__all__ = [
    "CatalogMatch",
    "FallbackGeocodingClient",
    "GeoapifyGeocodingProvider",
    "GeocodingCandidate",
    "GeocodingClient",
    "GeocodingProvider",
    "GeocodingProviderChain",
    "LocationCatalog",
    "LocationCatalogEntry",
    "LocationIQGeocodingProvider",
    "NominatimGeocodingProvider",
    "NotConfiguredGeocodingClient",
    "ProviderGeocodingClient",
    "build_query_variants",
    "get_geocoding_client",
    "load_catalog",
    "normalize_location_text",
    "strip_accents",
]
