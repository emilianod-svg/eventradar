"""Agente Recolector (sección 8.4).

Entrada: `SourceDefinition`. Salida: `list[RawContentCandidate]`. Depende de
los adaptadores en `app.sources` (Scrapy/Playwright/Facebook).

Persiste cada contenido nuevo en `raw_contents` y omite los que ya existen
por `(source_id, content_hash)` (sección 13: "contenidos repetidos se omiten
por hash" — la idempotencia tiene que resolverse acá, antes de gastar una
llamada al LLM en el Analizador, no al final del pipeline).

Usa `dedupe_by_hash` primero para colapsar repetidos dentro del mismo lote
(p. ej. un feed que lista el mismo ítem dos veces): sin ese paso, dos
candidatos con igual hash en la misma corrida romperían el `unique_together
(source, content_hash)` de `raw_contents` al segundo `create()`.
"""

from __future__ import annotations

from app.domain.dedupe import dedupe_by_hash
from app.domain.entities import RawContentCandidate, SourceDefinition
from app.models.raw_content import RawContent
from app.repositories.raw_content import RawContentRepository
from app.sources.rss_adapter import RssAdapter
from app.sources.scrapy_adapter import ScrapyAdapter


class CollectorAgent:
    def __init__(
        self,
        scrapy_adapter: ScrapyAdapter | None = None,
        rss_adapter: RssAdapter | None = None,
        raw_content_repository: RawContentRepository | None = None,
    ) -> None:
        self._scrapy_adapter = scrapy_adapter or ScrapyAdapter()
        self._rss_adapter = rss_adapter or RssAdapter()
        self._raw_content_repository = raw_content_repository or RawContentRepository()

    async def execute(self, data: SourceDefinition) -> list[RawContentCandidate]:
        adapter_type = data.adapter_type.strip().lower()
        if adapter_type in {"scrapy", "scrapy_static", "static", "html"}:
            fetched = await self._scrapy_adapter.fetch(data)
        elif adapter_type in {"rss", "rss_feed"}:
            fetched = await self._rss_adapter.fetch(data)
        else:
            raise NotImplementedError(
                f"CollectorAgent.execute: adaptador '{data.adapter_type}' aún no implementado."
            )

        return await self._persist_new(fetched)

    async def _persist_new(
        self, candidates: list[RawContentCandidate]
    ) -> list[RawContentCandidate]:
        deduped, _ = dedupe_by_hash(candidates)

        new_candidates: list[RawContentCandidate] = []
        for candidate in deduped:
            existing = await self._raw_content_repository.get_by_hash(
                source_id=candidate.source_id, content_hash=candidate.content_hash
            )
            if existing is not None:
                continue

            row = await RawContent.create(
                source_id=candidate.source_id,
                url=candidate.url,
                raw_text=candidate.raw_text,
                image_urls=candidate.image_urls,
                published_at=candidate.published_at,
                fetched_at=candidate.fetched_at,
                content_hash=candidate.content_hash,
                adapter_metadata=candidate.adapter_metadata,
            )
            new_candidates.append(candidate.model_copy(update={"id": row.id}))
        return new_candidates
