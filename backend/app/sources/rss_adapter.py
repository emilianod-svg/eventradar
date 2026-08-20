"""Adaptador RSS para fuentes que exponen feed WordPress (sección 8.4).

Alternativa a `ScrapyAdapter` para fuentes donde el scraping HTML directo no
es viable (ej. protección Cloudflare que bloquea `GET` a la página principal
pero no al feed) o donde el HTML de tarjetas es más frágil que el feed
estructurado que ya expone el sitio. No agrega dependencias nuevas: usa
`xml.etree.ElementTree` de la stdlib.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from xml.etree import ElementTree as ET

import httpx

from app.domain.entities import RawContentCandidate, SourceDefinition
from app.domain.errors import SourceFetchError

_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
_DEFAULT_USER_AGENT = "EventRadar/0.1 (+https://eventradar.net.ar; bot@eventradar.net.ar)"
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class RssAdapter:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20.0,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self._transport = transport
        self._timeout = timeout
        self._user_agent = user_agent

    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        xml_text = await self._download(source.base_url)
        return self.parse_feed(source=source, xml_text=xml_text)

    def parse_feed(
        self,
        *,
        source: SourceDefinition,
        xml_text: str,
        fetched_at: datetime | None = None,
    ) -> list[RawContentCandidate]:
        fetched_at = fetched_at or datetime.now(UTC)
        try:
            root = ET.fromstring(xml_text)  # nosec - fuente configurada por el equipo
        except ET.ParseError as exc:
            raise SourceFetchError(
                f"No se pudo parsear el feed RSS de '{source.name}': {exc}"
            ) from exc

        candidates: list[RawContentCandidate] = []
        for item in root.iterfind("./channel/item"):
            link = _text(item.find("link"))
            title = _text(item.find("title"))
            if not link or not title:
                continue

            body_html = _text(item.find(f"{_CONTENT_NS}encoded")) or _text(item.find("description"))
            raw_text = "\n".join(part for part in (title, _strip_html(body_html)) if part)
            published_at = _parse_rfc822(_text(item.find("pubDate")))
            guid = _text(item.find("guid"))
            categories = [c.text.strip() for c in item.findall("category") if c.text]

            content_hash = sha256(f"{source.id}:{link}:{raw_text}".encode()).hexdigest()
            candidates.append(
                RawContentCandidate(
                    source_id=source.id,
                    url=link,
                    raw_text=raw_text,
                    image_urls=[],
                    published_at=published_at,
                    fetched_at=fetched_at,
                    content_hash=content_hash,
                    adapter_metadata={
                        "adapter": "rss",
                        "source_name": source.name,
                        "title": title,
                        "guid": guid,
                        "categories": categories,
                    },
                )
            )
        return candidates

    async def _download(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
                headers={"User-Agent": self._user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"No se pudo descargar el feed RSS en {url}.") from exc
        return response.text


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _strip_html(html: str) -> str:
    without_tags = _HTML_TAG_RE.sub(" ", html)
    return _WHITESPACE_RE.sub(" ", without_tags).strip()


def _parse_rfc822(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
