"""Validación externa y descubrimiento opcional de fuentes."""

from __future__ import annotations

import ipaddress
import logging
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import httpx

from app.config import get_settings
from app.models.source import Source
from app.repositories.source import SourceRepository
from app.services.sources.normalization import normalize_adapter_type, normalize_source_url

logger = logging.getLogger("eventradar.sources")

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_FEED_PATHS = ("/feed/", "/rss", "/rss.xml", "/feed.xml", "/atom.xml")


@dataclass(slots=True)
class SourceCheckResult:
    name: str
    base_url: str
    adapter_type: str
    ok: bool
    status: str
    final_url: str | None = None
    content_type: str | None = None
    error: str | None = None
    discovered_urls: list[str] = field(default_factory=list)
    entries_count: int = 0


class _FeedLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.casefold(): (value or "") for key, value in attrs}
        if tag == "link":
            rel = attr_map.get("rel", "").casefold()
            feed_type = attr_map.get("type", "").casefold()
            href = attr_map.get("href", "").strip()
            if (
                href
                and "alternate" in rel
                and feed_type
                in {
                    "application/rss+xml",
                    "application/atom+xml",
                }
            ):
                self.links.append(href)
        elif tag == "a":
            href = attr_map.get("href", "").strip()
            if href and any(token in href.casefold() for token in ("rss", "feed", "atom")):
                self.links.append(href)


class SourceValidationService:
    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        max_redirects: int | None = None,
        max_response_bytes: int | None = None,
        user_agent: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        repository: SourceRepository | None = None,
    ) -> None:
        settings = get_settings()
        self._timeout_seconds = timeout_seconds or settings.source_request_timeout_seconds
        self._max_redirects = max_redirects or settings.source_max_redirects
        self._max_response_bytes = max_response_bytes or settings.source_max_response_bytes
        self._user_agent = user_agent or settings.source_user_agent
        self._transport = transport
        self._repository = repository or SourceRepository()

    async def validate_source(self, source: Source) -> SourceCheckResult:
        return await self._validate_by_metadata(
            name=source.name,
            base_url=source.base_url,
            adapter_type=source.adapter_type,
        )

    async def validate_catalog_entry(self, entry: object) -> SourceCheckResult:
        name = str(getattr(entry, "name", "<sin nombre>"))
        base_url = str(getattr(entry, "base_url", ""))
        adapter_type = str(getattr(entry, "adapter_type", ""))
        return await self._validate_by_metadata(
            name=name, base_url=base_url, adapter_type=adapter_type
        )

    async def discover_feeds(self, source: Source) -> SourceCheckResult:
        base_result = await self._fetch(source.base_url)
        if not base_result.ok:
            return SourceCheckResult(
                name=source.name,
                base_url=source.base_url,
                adapter_type=source.adapter_type,
                ok=False,
                status=base_result.status,
                final_url=base_result.final_url,
                content_type=base_result.content_type,
                error=base_result.error,
            )

        html = base_result.body.decode("utf-8", errors="replace")
        discovered = self._discover_feed_urls(base_result.final_url or source.base_url, html)
        return SourceCheckResult(
            name=source.name,
            base_url=source.base_url,
            adapter_type=source.adapter_type,
            ok=True,
            status="ok",
            final_url=base_result.final_url,
            content_type=base_result.content_type,
            discovered_urls=discovered,
        )

    async def persist_validation(self, source: Source, result: SourceCheckResult) -> None:
        now = _utcnow()
        source_obj = cast(Any, source)
        source_obj.validation_status = result.status
        source_obj.validation_checked_at = now
        source_obj.validation_error = result.error
        source_obj.validation_final_url = result.final_url
        source_obj.last_reviewed_at = now
        await source.save(
            update_fields=[
                "validation_status",
                "validation_checked_at",
                "validation_error",
                "validation_final_url",
                "last_reviewed_at",
            ]
        )

    async def persist_discovered_urls(
        self,
        source: Source,
        discovered_urls: list[str],
    ) -> int:
        created = 0
        for discovered_url in discovered_urls[
            : get_settings().source_discovery_max_urls_per_domain
        ]:
            canonical = normalize_source_url(discovered_url)
            if canonical is None:
                continue
            existing = await self._repository.get_by_canonical_base_url(canonical)
            if existing is not None:
                if not existing.active and existing.discovered_from_url is None:
                    existing.discovered_from_url = source.base_url
                    if existing.validation_status == "catalog":
                        existing.validation_status = "discovered"
                    await existing.save(update_fields=["discovered_from_url", "validation_status"])
                continue

            await Source.create(
                name=_discovered_name(canonical),
                base_url=discovered_url,
                canonical_base_url=canonical,
                adapter_type="rss",
                active=False,
                reliability_score=0.5,
                validation_status="discovered",
                discovered_from_url=source.base_url,
            )
            created += 1
        return created

    async def _validate_by_metadata(
        self,
        *,
        name: str,
        base_url: str,
        adapter_type: str,
    ) -> SourceCheckResult:
        normalized_adapter_type = normalize_adapter_type(adapter_type)
        fetch_result = await self._fetch(base_url)
        if not fetch_result.ok:
            return SourceCheckResult(
                name=name,
                base_url=base_url,
                adapter_type=normalized_adapter_type,
                ok=False,
                status=fetch_result.status,
                final_url=fetch_result.final_url,
                content_type=fetch_result.content_type,
                error=fetch_result.error,
            )

        text = fetch_result.body.decode("utf-8", errors="replace")
        if normalized_adapter_type == "rss":
            return self._validate_rss(
                name=name,
                base_url=base_url,
                adapter_type=normalized_adapter_type,
                final_url=fetch_result.final_url,
                content_type=fetch_result.content_type,
                text=text,
            )

        return self._validate_html(
            name=name,
            base_url=base_url,
            adapter_type=normalized_adapter_type,
            final_url=fetch_result.final_url,
            content_type=fetch_result.content_type,
            text=text,
        )

    def _validate_rss(
        self,
        *,
        name: str,
        base_url: str,
        adapter_type: str,
        final_url: str | None,
        content_type: str | None,
        text: str,
    ) -> SourceCheckResult:
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            return SourceCheckResult(
                name=name,
                base_url=base_url,
                adapter_type=adapter_type,
                ok=False,
                status="invalid",
                final_url=final_url,
                content_type=content_type,
                error=f"invalid_xml:{exc}",
            )

        entries_count = 0
        if root.tag.lower().endswith("rss"):
            entries_count = sum(
                1 for item in root.findall("./channel/item") if _rss_item_has_data(item)
            )
        elif root.tag.lower().endswith("feed"):
            entries_count = sum(
                1 for item in root.findall(".//{*}entry") if _atom_entry_has_data(item)
            )

        if entries_count == 0:
            return SourceCheckResult(
                name=name,
                base_url=base_url,
                adapter_type=adapter_type,
                ok=False,
                status="invalid",
                final_url=final_url,
                content_type=content_type,
                error="no_entries_with_title_and_link",
            )

        return SourceCheckResult(
            name=name,
            base_url=base_url,
            adapter_type=adapter_type,
            ok=True,
            status="valid",
            final_url=final_url,
            content_type=content_type,
            entries_count=entries_count,
        )

    def _validate_html(
        self,
        *,
        name: str,
        base_url: str,
        adapter_type: str,
        final_url: str | None,
        content_type: str | None,
        text: str,
    ) -> SourceCheckResult:
        if not _looks_like_html(content_type, text):
            return SourceCheckResult(
                name=name,
                base_url=base_url,
                adapter_type=adapter_type,
                ok=False,
                status="invalid",
                final_url=final_url,
                content_type=content_type,
                error="not_html",
            )

        discovered = self._discover_feed_urls(final_url or base_url, text)
        return SourceCheckResult(
            name=name,
            base_url=base_url,
            adapter_type=adapter_type,
            ok=True,
            status="valid",
            final_url=final_url,
            content_type=content_type,
            discovered_urls=discovered,
        )

    def _discover_feed_urls(self, page_url: str, html: str) -> list[str]:
        parser = _FeedLinkParser()
        parser.feed(html)
        parser.close()

        parsed_page = urlparse(page_url)
        base_origin = f"{parsed_page.scheme}://{parsed_page.netloc}"
        derived = [urljoin(f"{base_origin}/", suffix) for suffix in _FEED_PATHS]
        derived.extend(
            urljoin(f"{page_url.rstrip('/')}/", suffix.lstrip("/")) for suffix in _FEED_PATHS
        )

        candidates: list[str] = []
        for raw_url in [*parser.links, *derived]:
            normalized = normalize_source_url(urljoin(page_url, raw_url))
            if normalized is None:
                continue
            if not _is_safe_url(normalized):
                continue
            if normalized not in candidates:
                candidates.append(normalized)
        return candidates[: get_settings().source_discovery_max_urls_per_domain]

    async def _fetch(self, url: str) -> _FetchResult:
        current_url = normalize_source_url(url)
        if current_url is None:
            return _FetchResult(ok=False, status="invalid_url", error="invalid_url")

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=self._timeout_seconds,
            transport=self._transport,
            headers={"User-Agent": self._user_agent},
        ) as client:
            for redirect_count in range(self._max_redirects + 1):
                if not _is_safe_url(current_url):
                    return _FetchResult(ok=False, status="blocked", error="unsafe_url")

                try:
                    async with client.stream("GET", current_url) as response:
                        if response.status_code in _REDIRECT_STATUSES:
                            location = response.headers.get("location")
                            if not location:
                                return _FetchResult(
                                    ok=False,
                                    status="invalid",
                                    final_url=str(response.url),
                                    content_type=response.headers.get("content-type"),
                                    error="redirect_without_location",
                                )
                            if redirect_count >= self._max_redirects:
                                return _FetchResult(
                                    ok=False,
                                    status="too_many_redirects",
                                    final_url=str(response.url),
                                    content_type=response.headers.get("content-type"),
                                    error="too_many_redirects",
                                )
                            next_url = normalize_source_url(urljoin(current_url, location))
                            if next_url is None or not _is_safe_url(next_url):
                                return _FetchResult(
                                    ok=False, status="blocked", error="unsafe_redirect"
                                )
                            current_url = next_url
                            continue

                        if response.status_code >= 400:
                            return _FetchResult(
                                ok=False,
                                status="invalid",
                                final_url=str(response.url),
                                content_type=response.headers.get("content-type"),
                                error=f"http_{response.status_code}",
                            )

                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self._max_response_bytes:
                                return _FetchResult(
                                    ok=False,
                                    status="too_large",
                                    final_url=str(response.url),
                                    content_type=response.headers.get("content-type"),
                                    error="response_too_large",
                                )

                        return _FetchResult(
                            ok=True,
                            status="ok",
                            final_url=str(response.url),
                            content_type=response.headers.get("content-type"),
                            body=bytes(body),
                        )
                except httpx.TimeoutException:
                    return _FetchResult(ok=False, status="timeout", error="timeout")
                except httpx.HTTPError as exc:
                    return _FetchResult(ok=False, status="invalid", error=exc.__class__.__name__)

        return _FetchResult(ok=False, status="invalid", error="unreachable")


@dataclass(slots=True)
class _FetchResult:
    ok: bool
    status: str
    final_url: str | None = None
    content_type: str | None = None
    error: str | None = None
    body: bytes = b""


def _looks_like_html(content_type: str | None, text: str) -> bool:
    if content_type and "html" in content_type.casefold():
        return True
    lowered = text.lstrip().casefold()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html")


def _rss_item_has_data(item: ET.Element) -> bool:
    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()
    return bool(title and link)


def _atom_entry_has_data(item: ET.Element) -> bool:
    title = (item.findtext("{*}title") or item.findtext("title") or "").strip()
    link = ""
    for link_element in item.findall("{*}link") + item.findall("link"):
        href = link_element.attrib.get("href", "").strip()
        rel = link_element.attrib.get("rel", "alternate").casefold()
        if href and rel in {"alternate", "self", ""}:
            link = href
            break
    return bool(title and link)


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    host = parsed.hostname.casefold()
    if host in {"localhost", "metadata", "metadata.google.internal", "169.254.169.254"}:
        return False
    if host.endswith(".localhost"):
        return False

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True

    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    )


def _discovered_name(url: str) -> str:
    parsed = urlparse(url)
    slug = f"{parsed.netloc}{parsed.path}".strip("/") or parsed.netloc
    return f"Discovered feed - {slug[:180]}"


def _utcnow():
    from datetime import UTC, datetime

    return datetime.now(UTC)
