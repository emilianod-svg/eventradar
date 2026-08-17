"""Gestión de catálogo, bootstrap y validación de fuentes."""

from app.services.sources.bootstrap import SourceBootstrapReport, SourceBootstrapService
from app.services.sources.catalog import SourceCatalog, SourceCatalogEntry, load_source_catalog
from app.services.sources.normalization import normalize_adapter_type, normalize_source_url
from app.services.sources.validation import SourceCheckResult, SourceValidationService

__all__ = [
    "SourceBootstrapReport",
    "SourceBootstrapService",
    "SourceCatalog",
    "SourceCatalogEntry",
    "SourceCheckResult",
    "SourceValidationService",
    "load_source_catalog",
    "normalize_adapter_type",
    "normalize_source_url",
]
