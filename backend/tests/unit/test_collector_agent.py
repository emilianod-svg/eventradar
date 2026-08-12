"""Pruebas del Agente Recolector."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.agents.collector import CollectorAgent
from app.domain.entities import SourceDefinition


class FakeScrapyAdapter:
    def __init__(self) -> None:
        self.called = False

    async def fetch(self, source: SourceDefinition) -> list[object]:
        self.called = True
        return []


@pytest.mark.asyncio
async def test_collector_agent_uses_scrapy_adapter_for_static_sources() -> None:
    adapter = FakeScrapyAdapter()
    agent = CollectorAgent(scrapy_adapter=adapter)
    source = SourceDefinition(
        id=uuid4(),
        name="Ticket Misiones",
        base_url="https://ticketmisiones.com",
        adapter_type="scrapy_static",
    )

    result = await agent.execute(source)

    assert adapter.called is True
    assert result == []
