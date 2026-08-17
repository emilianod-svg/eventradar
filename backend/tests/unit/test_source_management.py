"""Pruebas de bootstrap, normalización y validación de fuentes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from types import SimpleNamespace

import app.main as main_module
import httpx
import pytest
from app.services.sources.bootstrap import SourceBootstrapService
from app.services.sources.catalog import SourceCatalog, SourceCatalogEntry
from app.services.sources.normalization import normalize_adapter_type, normalize_source_url
from app.services.sources.validation import SourceValidationService
from fastapi import FastAPI


def test_normalize_source_url_preserves_functional_query_params() -> None:
    assert (
        normalize_source_url(" https://example.com/feed/?utm_source=x&ciudad=Posadas#top ")
        == "https://example.com/feed?ciudad=Posadas"
    )


def test_normalize_adapter_type_maps_legacy_values() -> None:
    assert normalize_adapter_type("RSS_FEED") == "rss"
    assert normalize_adapter_type("SCRAPY_STATIC") == "scrapy"


@dataclass
class _FakeSource:
    id: str
    name: str
    base_url: str
    canonical_base_url: str | None
    adapter_type: str
    active: bool
    reliability_score: float
    contact_notes: str | None = None
    validation_status: str = "catalog"
    validation_checked_at: object | None = None
    validation_error: str | None = None
    validation_final_url: str | None = None
    discovered_from_url: str | None = None

    async def save(self, update_fields: list[str] | None = None) -> None:
        return None


class _FakeRepository:
    def __init__(self, existing: dict[str, _FakeSource] | None = None) -> None:
        self.existing = existing or {}

    async def get_by_canonical_base_url(self, canonical_base_url: str) -> _FakeSource | None:
        return self.existing.get(canonical_base_url)


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_and_updates_managed_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[dict[str, object]] = []
    repo = _FakeRepository()

    @asynccontextmanager
    async def fake_in_transaction():
        class _Conn:
            async def execute_query(self, query: str) -> None:
                return None

        yield _Conn()

    async def fake_create(**kwargs: object) -> _FakeSource:
        created.append(kwargs)
        source = _FakeSource(id="new", **kwargs)  # type: ignore[arg-type]
        repo.existing[str(kwargs["canonical_base_url"])] = source
        return source

    monkeypatch.setattr("app.services.sources.bootstrap.in_transaction", fake_in_transaction)
    monkeypatch.setattr("app.services.sources.bootstrap.Source.create", fake_create)

    catalog = SourceCatalog(
        entries=[
            SourceCatalogEntry(
                name="Ejemplo",
                base_url="https://example.com/feed/?utm_source=abc",
                adapter_type="rss",
                active=True,
                reliability_score=0.9,
            )
        ]
    )
    service = SourceBootstrapService(repository=repo, catalog_path="data/source_catalog.json")

    first = await service.bootstrap(catalog)
    second = await service.bootstrap(catalog)

    assert first.inserted == 1
    assert first.updated == 0
    assert second.inserted == 0
    assert second.unchanged == 1
    assert len(created) == 1
    assert created[0]["canonical_base_url"] == "https://example.com/feed"


def _rss_payload() -> bytes:
    return (
        b"<?xml version='1.0' encoding='UTF-8'?>"
        b"<rss version='2.0'><channel><title>t</title>"
        b"<item><title>Evento</title><link>https://example.com/e</link></item>"
        b"</channel></rss>"
    )


def _html_payload() -> bytes:
    return (
        b"<!doctype html><html><head>"
        b"<link rel='alternate' type='application/rss+xml' href='/feed/' />"
        b"</head><body><a href='/feed.xml'>feed</a></body></html>"
    )


def _transport_for_validation(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/rss-valid"):
        return httpx.Response(
            200, headers={"content-type": "application/rss+xml"}, content=_rss_payload()
        )
    if url.endswith("/rss-invalid"):
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml"},
            content=b"<rss><channel></channel>",
        )
    if url.endswith("/html-with-feed"):
        return httpx.Response(200, headers={"content-type": "text/html"}, content=_html_payload())
    if url.endswith("/html-no-feed"):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><body>sin feed</body></html>",
        )
    if url.endswith("/redirect-ok"):
        return httpx.Response(302, headers={"location": "/rss-valid"})
    if url.endswith("/redirect-private"):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/rss-valid"})
    if url.endswith("/timeout"):
        raise httpx.ReadTimeout("timeout", request=request)
    return httpx.Response(404, content=b"not found")


@pytest.mark.asyncio
async def test_validation_accepts_valid_rss_and_rejects_invalid_xml() -> None:
    transport = httpx.MockTransport(_transport_for_validation)
    service = SourceValidationService(transport=transport)

    valid = await service.validate_catalog_entry(
        SimpleNamespace(name="rss", base_url="https://example.com/rss-valid", adapter_type="rss")
    )
    invalid = await service.validate_catalog_entry(
        SimpleNamespace(name="bad", base_url="https://example.com/rss-invalid", adapter_type="rss")
    )

    assert valid.ok is True
    assert valid.entries_count == 1
    assert invalid.ok is False
    assert invalid.status == "invalid"


@pytest.mark.asyncio
async def test_validation_handles_timeout_and_redirects() -> None:
    transport = httpx.MockTransport(_transport_for_validation)
    service = SourceValidationService(transport=transport)

    timeout = await service.validate_catalog_entry(
        SimpleNamespace(name="timeout", base_url="https://example.com/timeout", adapter_type="rss")
    )
    redirected = await service.validate_catalog_entry(
        SimpleNamespace(
            name="redir", base_url="https://example.com/redirect-ok", adapter_type="rss"
        )
    )
    blocked = await service.validate_catalog_entry(
        SimpleNamespace(
            name="blocked", base_url="https://example.com/redirect-private", adapter_type="rss"
        )
    )

    assert timeout.status == "timeout"
    assert redirected.ok is True
    assert redirected.final_url == "https://example.com/rss-valid"
    assert blocked.ok is False
    assert blocked.status == "blocked"


@pytest.mark.asyncio
async def test_validation_discovers_alternate_feed_links_and_html_without_feed() -> None:
    transport = httpx.MockTransport(_transport_for_validation)
    service = SourceValidationService(transport=transport)

    discovered = await service.validate_catalog_entry(
        SimpleNamespace(
            name="html", base_url="https://example.com/html-with-feed", adapter_type="scrapy"
        )
    )
    no_feed = await service.validate_catalog_entry(
        SimpleNamespace(
            name="html", base_url="https://example.com/html-no-feed", adapter_type="scrapy"
        )
    )

    assert discovered.ok is True
    assert any(
        url.endswith("/feed") or url.endswith("/feed.xml") for url in discovered.discovered_urls
    )
    assert no_feed.ok is True
    assert no_feed.discovered_urls


@pytest.mark.asyncio
async def test_background_validation_failure_does_not_abort_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_settings = SimpleNamespace(
        source_validate_on_startup=True,
        source_discovery_enabled=False,
        source_discovery_max_urls_per_domain=5,
    )

    async def fake_filter(*args: object, **kwargs: object) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id="source-1",
                name="Fuente",
                base_url="https://example.com/feed/",
                adapter_type="rss",
                active=True,
            )
        ]

    async def fake_validate(self: object, source: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "get_settings", lambda: fake_settings)
    monkeypatch.setattr("app.models.source.Source.filter", fake_filter)
    monkeypatch.setattr(SourceValidationService, "validate_source", fake_validate)

    await main_module._run_source_background_tasks(FastAPI())
