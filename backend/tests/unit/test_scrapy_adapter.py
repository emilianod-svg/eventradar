"""Pruebas del primer adaptador estático."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.entities import SourceDefinition
from app.sources.scrapy_adapter import ScrapyAdapter


def test_parse_html_fixture_to_raw_content_candidates() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "scrapy" / "ticketmisiones.html"
    html = fixture_path.read_text(encoding="utf-8")

    source = SourceDefinition(
        id=uuid4(),
        name="Ticket Misiones",
        base_url="https://ticketmisiones.com",
        adapter_type="scrapy",
    )

    adapter = ScrapyAdapter()
    candidates = adapter.parse_html(
        source=source,
        html=html,
        page_url=source.base_url,
    )

    assert len(candidates) == 2
    assert candidates[0].source_id == source.id
    assert candidates[0].url == "https://ticketmisiones.com/eventos/feria-artesanal-2026"
    assert "Feria Artesanal de Invierno" in candidates[0].raw_text
    assert candidates[0].content_hash
    assert candidates[0].adapter_metadata["adapter"] == "scrapy"
    assert candidates[0].adapter_metadata["source_name"] == "Ticket Misiones"
    assert candidates[0].published_at is not None
