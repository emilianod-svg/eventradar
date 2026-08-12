"""Adaptador para fuentes web estáticas (sección 8.4).

La primera vertical se implementa como parser HTML puro para poder testearla
con fixtures locales. Luego se puede reemplazar el transporte por Scrapy sin
romper el contrato de salida (`RawContentCandidate`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from hashlib import sha256
from urllib.parse import urljoin
from urllib.request import urlopen

from app.domain.entities import RawContentCandidate, SourceDefinition


class ScrapyAdapter:
    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        html = self._download(source.base_url)
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
        fetched_at = fetched_at or datetime.now(timezone.utc)

        candidates: list[RawContentCandidate] = []
        for item in extracted:
            raw_text = "\n".join(part for part in [item["title"], item["published_at_text"], item["description"]] if part)
            content_hash = sha256(f"{source.id}:{item['url']}:{raw_text}".encode("utf-8")).hexdigest()
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

    def _download(self, url: str) -> str:
        with urlopen(url, timeout=20) as response:  # nosec - entrada controlada por configuración
            return response.read().decode("utf-8", errors="replace")


class _EventCardParser(HTMLParser):
    """Parser mínimo para fixtures y primeras fuentes estáticas."""

    def __init__(self, *, page_url: str) -> None:
        super().__init__()
        self.page_url = page_url
        self._cards: list[dict[str, object]] = []
        self._current: dict[str, object] | None = None
        self._current_text_field: str | None = None
        self._buffer: list[str] = []

    def parse(self, html: str) -> list[dict[str, object]]:
        self.feed(html)
        self.close()
        return [card for card in self._cards if card.get("url") and card.get("title")]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        class_names = attr_map.get("class", "")

        if self._current is None and tag in {"article", "div", "li"} and _looks_like_card(class_names):
            self._current = {
                "title": "",
                "description": "",
                "url": "",
                "published_at": None,
                "published_at_text": "",
            }
            return

        if self._current is None:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._current_text_field = "title"
            self._buffer = []
        elif tag == "p":
            self._current_text_field = "description"
            self._buffer = []
        elif tag == "a" and attr_map.get("href"):
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
            self._current[self._current_text_field] = " ".join(part for part in [existing, text] if part).strip()
            self._current_text_field = None
            self._buffer = []
            return

        if tag in {"article", "div", "li"}:
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
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
