"""Adaptador para fuentes web estáticas (sección 8.4).

La primera vertical se implementa como parser HTML puro para poder testearla
con fixtures locales. Luego se puede reemplazar el transporte por Scrapy sin
romper el contrato de salida (`RawContentCandidate`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
from typing import Literal, TypedDict, cast
from urllib.parse import urljoin

import httpx

from app.domain.entities import RawContentCandidate, SourceDefinition
from app.domain.errors import SourceFetchError

_DEFAULT_USER_AGENT = "EventRadar/0.1 (+https://eventradar.net.ar; bot@eventradar.net.ar)"


class ScrapyAdapter:
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
        html = await self._download(source.base_url)
        return self.parse_html(source=source, html=html, page_url=source.base_url)

    def parse_html(
        self,
        *,
        source: SourceDefinition,
        html: str,
        page_url: str,
        fetched_at: datetime | None = None,
    ) -> list[RawContentCandidate]:
        extracted = _EventCardParser(page_url=page_url).parse(html)
        fetched_at = fetched_at or datetime.now(UTC)

        candidates: list[RawContentCandidate] = []
        for item in extracted:
            raw_text_parts: list[str] = [
                item["title"],
                item["published_at_text"],
                item["description"],
            ]
            raw_text = "\n".join(part for part in raw_text_parts if part)
            content_hash = sha256(f"{source.id}:{item['url']}:{raw_text}".encode()).hexdigest()
            candidates.append(
                RawContentCandidate(
                    source_id=source.id,
                    url=item["url"],
                    raw_text=raw_text,
                    image_urls=[],
                    published_at=item["published_at"],
                    fetched_at=fetched_at,
                    content_hash=content_hash,
                    adapter_metadata={
                        "adapter": "scrapy",
                        "source_name": source.name,
                        "page_url": page_url,
                        "title": item["title"],
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
            raise SourceFetchError(f"No se pudo descargar la página en {url}.") from exc
        return response.text


class _EventCardParser(HTMLParser):
    """Parser mínimo para fixtures y primeras fuentes estáticas."""

    _CONTAINER_TAGS = {"article", "div", "li"}

    def __init__(self, *, page_url: str) -> None:
        super().__init__()
        self.page_url = page_url
        self._cards: list[_ParsedCard] = []
        self._current: _ParsedCard | None = None
        self._current_text_field: str | None = None
        self._buffer: list[str] = []
        self._card_depth = 0

    def parse(self, html: str) -> list[_ParsedCard]:
        self.feed(html)
        self.close()
        return [card for card in self._cards if card.get("url") and card.get("title")]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        class_names = attr_map.get("class", "")

        if self._current is None and tag in self._CONTAINER_TAGS and _looks_like_card(class_names):
            self._current = {
                "title": "",
                "description": "",
                "url": "",
                "published_at": None,
                "published_at_text": "",
            }
            self._card_depth = 0
            return

        if self._current is None:
            return

        if tag in self._CONTAINER_TAGS:
            # Un contenedor anidado dentro de la tarjeta (wrapper de imagen,
            # layout interno, etc.) no debe cerrarla al llegar su end tag.
            self._card_depth += 1

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._current_text_field = "title"
            self._buffer = []
        elif tag == "p":
            self._current_text_field = "description"
            self._buffer = []
        elif tag == "a" and attr_map.get("href") and not self._current["url"]:
            self._current["url"] = urljoin(self.page_url, attr_map["href"])
        elif tag == "time":
            self._current_text_field = "published_at_text"
            self._buffer = []
            datetime_value = attr_map.get("datetime")
            if datetime_value:
                self._current["published_at"] = _parse_datetime(datetime_value)

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "time"} and self._current_text_field:
            text = " ".join(part.strip() for part in self._buffer if part.strip())
            existing = str(self._current.get(self._current_text_field, "")).strip()
            field_name = cast(
                "Literal['title', 'description', 'url', 'published_at', 'published_at_text']",
                self._current_text_field,
            )
            self._current[field_name] = " ".join(part for part in [existing, text] if part).strip()
            self._current_text_field = None
            self._buffer = []
            return

        if tag in self._CONTAINER_TAGS:
            if self._card_depth > 0:
                self._card_depth -= 1
                return
            card = self._current
            if card.get("url") and card.get("title"):
                self._cards.append(card)
            self._current = None
            self._current_text_field = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._current_text_field:
            self._buffer.append(data)


def _looks_like_card(class_names: str) -> bool:
    return any(token in class_names.lower() for token in ("event", "card", "item", "post"))


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


class _ParsedCard(TypedDict):
    title: str
    description: str
    url: str
    published_at: datetime | None
    published_at_text: str
