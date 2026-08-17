"""Bootstrap idempotente del catálogo de fuentes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from tortoise.transactions import in_transaction

from app.config import get_settings
from app.models.source import Source
from app.repositories.source import SourceRepository
from app.services.sources.catalog import SourceCatalog, SourceCatalogEntry, load_source_catalog
from app.services.sources.normalization import normalize_adapter_type, normalize_source_url

logger = logging.getLogger("eventradar.sources")

_BOOTSTRAP_LOCK_KEY = 314159265


@dataclass(slots=True)
class SourceBootstrapReport:
    configured: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    invalid: int = 0


class SourceBootstrapService:
    def __init__(
        self,
        repository: SourceRepository | None = None,
        catalog_path: str | None = None,
    ) -> None:
        self._repository = repository or SourceRepository()
        self._catalog_path = catalog_path or get_settings().source_catalog_path

    async def bootstrap(self, catalog: SourceCatalog | None = None) -> SourceBootstrapReport:
        source_catalog = catalog or load_source_catalog(self._catalog_path)
        report = SourceBootstrapReport(configured=len(source_catalog.entries))

        async with in_transaction() as conn:
            await conn.execute_query(f"SELECT pg_advisory_xact_lock({_BOOTSTRAP_LOCK_KEY})")
            for entry in source_catalog.entries:
                await self._upsert_entry(entry, report)

        logger.info(
            "source_bootstrap_completed",
            extra={
                "configured": report.configured,
                "inserted": report.inserted,
                "updated": report.updated,
                "unchanged": report.unchanged,
                "deactivated": report.deactivated,
                "invalid": report.invalid,
            },
        )
        return report

    async def _upsert_entry(self, entry: SourceCatalogEntry, report: SourceBootstrapReport) -> None:
        canonical_base_url = normalize_source_url(entry.base_url)
        if canonical_base_url is None:
            report.invalid += 1
            logger.warning(
                "source_bootstrap_invalid_url",
                extra={"name": entry.name, "base_url": entry.base_url},
            )
            return

        adapter_type = normalize_adapter_type(entry.adapter_type)
        existing = await self._repository.get_by_canonical_base_url(canonical_base_url)

        if existing is None:
            await Source.create(
                name=entry.name.strip(),
                base_url=entry.base_url.strip(),
                canonical_base_url=canonical_base_url,
                adapter_type=adapter_type,
                active=entry.active,
                reliability_score=float(entry.reliability_score),
                contact_notes=entry.notes.strip() if entry.notes else None,
            )
            report.inserted += 1
            return

        changes: dict[str, Any] = {}
        if existing.name != entry.name.strip():
            changes["name"] = entry.name.strip()
        if existing.base_url != entry.base_url.strip():
            changes["base_url"] = entry.base_url.strip()
        if existing.canonical_base_url != canonical_base_url:
            changes["canonical_base_url"] = canonical_base_url
        if existing.adapter_type != adapter_type:
            changes["adapter_type"] = adapter_type
        if existing.active != entry.active:
            changes["active"] = entry.active
        if float(existing.reliability_score) != float(entry.reliability_score):
            changes["reliability_score"] = float(entry.reliability_score)

        if changes:
            if existing.active and not entry.active:
                report.deactivated += 1
            for field_name, value in changes.items():
                setattr(existing, field_name, value)
            await existing.save()
            report.updated += 1
            return

        report.unchanged += 1
