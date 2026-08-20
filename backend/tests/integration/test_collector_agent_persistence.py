"""CollectorAgent: idempotencia por hash contra `raw_contents` (sección 13)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.agents.collector import CollectorAgent
from app.domain.entities import RawContentCandidate, SourceDefinition
from app.models.raw_content import RawContent
from app.models.source import Source


class FakeAdapter:
    def __init__(self, candidates: list[RawContentCandidate]) -> None:
        self._candidates = candidates
        self.calls = 0

    async def fetch(self, source: SourceDefinition) -> list[RawContentCandidate]:
        self.calls += 1
        return self._candidates


def _candidate(source_id, content_hash: str) -> RawContentCandidate:
    return RawContentCandidate(
        source_id=source_id,
        url="https://example.com/nota",
        raw_text="Festival del Litoral el sabado",
        fetched_at=datetime.now(UTC),
        content_hash=content_hash,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_collector_persists_new_content_and_skips_known_hash(tortoise_connection) -> None:
    source = await Source.create(
        name="Misiones Online", base_url="https://misionesonline.net/feed/", adapter_type="rss"
    )
    source_def = SourceDefinition(
        id=source.id, name=source.name, base_url=source.base_url, adapter_type="rss_feed"
    )
    candidate = _candidate(source.id, content_hash="abc123")
    adapter = FakeAdapter([candidate])
    agent = CollectorAgent(rss_adapter=adapter)

    first_run = await agent.execute(source_def)

    assert len(first_run) == 1
    assert first_run[0].id is not None
    assert await RawContent.filter(source_id=source.id, content_hash="abc123").count() == 1

    second_run = await agent.execute(source_def)

    assert second_run == []
    assert await RawContent.filter(source_id=source.id, content_hash="abc123").count() == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_collector_persists_unrelated_new_content_alongside_known_hash(
    tortoise_connection,
) -> None:
    source = await Source.create(
        name="Misiones Cuatro",
        base_url="https://misionescuatro.com/espectaculos/feed/",
        adapter_type="rss",
    )
    source_def = SourceDefinition(
        id=source.id, name=source.name, base_url=source.base_url, adapter_type="rss_feed"
    )
    known = _candidate(source.id, content_hash="known-hash")
    await RawContent.create(
        source_id=source.id,
        url=known.url,
        raw_text=known.raw_text,
        fetched_at=known.fetched_at,
        content_hash=known.content_hash,
    )
    new = _candidate(uuid4(), content_hash="new-hash").model_copy(update={"source_id": source.id})
    adapter = FakeAdapter([known, new])
    agent = CollectorAgent(rss_adapter=adapter)

    result = await agent.execute(source_def)

    assert [c.content_hash for c in result] == ["new-hash"]
