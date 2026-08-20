"""Bootstrap idempotente de `sources` contra Postgres real."""

from __future__ import annotations

import asyncio

import pytest
from app.models.source import Source
from app.services.sources.bootstrap import SourceBootstrapService
from app.services.sources.catalog import SourceCatalog, SourceCatalogEntry
from app.services.sources.normalization import normalize_source_url


def _catalog(*entries: SourceCatalogEntry) -> SourceCatalog:
    return SourceCatalog(entries=list(entries))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_inserts_all_sources(tortoise_connection) -> None:
    from app.services.sources.catalog import load_source_catalog

    catalog = load_source_catalog()
    report = await SourceBootstrapService().bootstrap(catalog)

    assert report.inserted == len(catalog.entries)
    assert await Source.all().count() == len(catalog.entries)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_second_bootstrap_does_not_duplicate_sources(tortoise_connection) -> None:
    from app.services.sources.catalog import load_source_catalog

    catalog = load_source_catalog()
    service = SourceBootstrapService()

    first = await service.bootstrap(catalog)
    second = await service.bootstrap(catalog)

    assert first.inserted == len(catalog.entries)
    assert second.unchanged == len(catalog.entries)
    assert await Source.all().count() == len(catalog.entries)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_existing_source_keeps_id_and_updates_managed_fields(tortoise_connection) -> None:
    catalog = _catalog(
        SourceCatalogEntry(
            name="Test",
            base_url="https://example.com/feed/",
            adapter_type="rss",
            active=True,
            reliability_score=0.9,
        )
    )
    source = await Source.create(
        name="Old",
        base_url="https://example.com/feed",
        canonical_base_url=normalize_source_url("https://example.com/feed"),
        adapter_type="rss",
        active=False,
        reliability_score=0.5,
    )

    report = await SourceBootstrapService().bootstrap(catalog)
    updated = await Source.get(id=source.id)

    assert report.updated == 1
    assert updated.id == source.id
    assert updated.name == "Test"
    assert float(updated.reliability_score) == pytest.approx(0.9, abs=1e-3)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trailing_slash_equivalence_does_not_duplicate(tortoise_connection) -> None:
    catalog = _catalog(
        SourceCatalogEntry(
            name="Slash",
            base_url="https://example.com/feed/",
            adapter_type="rss",
            active=True,
            reliability_score=0.8,
        )
    )
    await Source.create(
        name="Slash old",
        base_url="https://example.com/feed",
        canonical_base_url=normalize_source_url("https://example.com/feed"),
        adapter_type="rss",
        active=True,
        reliability_score=0.8,
    )

    await SourceBootstrapService().bootstrap(catalog)

    assert await Source.all().count() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_functional_query_parameter_is_preserved(tortoise_connection) -> None:
    catalog = _catalog(
        SourceCatalogEntry(
            name="Ticket Misiones",
            base_url="https://ticketmisiones.com/eventos-por-ciudad?ciudad=Posadas",
            adapter_type="scrapy",
            active=True,
            reliability_score=0.8,
        )
    )

    await SourceBootstrapService().bootstrap(catalog)
    source = await Source.get()

    assert source.base_url.endswith("?ciudad=Posadas")
    assert source.canonical_base_url.endswith("?ciudad=Posadas")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_bootstrap_runs_are_idempotent(tortoise_connection) -> None:
    catalog = _catalog(
        SourceCatalogEntry(
            name="Concurrent",
            base_url="https://example.com/feed/",
            adapter_type="rss",
            active=True,
            reliability_score=0.8,
        )
    )
    service = SourceBootstrapService()

    results = await asyncio.gather(service.bootstrap(catalog), service.bootstrap(catalog))

    assert sum(report.inserted for report in results) == 1
    assert await Source.all().count() == 1
