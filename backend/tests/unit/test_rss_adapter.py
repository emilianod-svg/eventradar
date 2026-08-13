"""Pruebas del adaptador RSS (segundo y tercer adaptador, sección 8.4)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.entities import SourceDefinition
from app.sources.rss_adapter import RssAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "rss"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_feed_misionesonline_produces_raw_content_candidates() -> None:
    xml_text = _read_fixture("misionesonline.xml")
    source = SourceDefinition(
        id=uuid4(),
        name="Misiones Online",
        base_url="https://misionesonline.net/feed/",
        adapter_type="rss",
    )

    adapter = RssAdapter()
    candidates = adapter.parse_feed(source=source, xml_text=xml_text)

    assert len(candidates) == 3
    first = candidates[0]
    assert first.source_id == source.id
    assert first.url == (
        "https://misionesonline.net/2026/08/12/cuti-romero-es-nuevo-jugador-del-atletico-de-madrid/"
    )
    assert "Cuti Romero" in first.raw_text
    assert "<img" not in first.raw_text
    assert first.content_hash
    assert first.published_at is not None
    assert first.adapter_metadata["adapter"] == "rss"
    assert first.adapter_metadata["source_name"] == "Misiones Online"


def test_parse_feed_misionescuatro_espectaculos_uses_full_body_when_available() -> None:
    xml_text = _read_fixture("misionescuatro_espectaculos.xml")
    source = SourceDefinition(
        id=uuid4(),
        name="Misiones Cuatro",
        base_url="https://misionescuatro.com/espectaculos/feed/",
        adapter_type="rss",
    )

    adapter = RssAdapter()
    candidates = adapter.parse_feed(source=source, xml_text=xml_text)

    assert len(candidates) == 2
    first = candidates[0]
    assert "Oreja Perpleja" in first.raw_text
    # content:encoded trae el cuerpo completo, más largo que el excerpt.
    assert len(first.raw_text) > 500
    assert "Música" in first.adapter_metadata["categories"]


def test_parse_feed_is_deterministic_for_same_input() -> None:
    xml_text = _read_fixture("misionesonline.xml")
    source = SourceDefinition(
        id=uuid4(),
        name="Misiones Online",
        base_url="https://misionesonline.net/feed/",
        adapter_type="rss",
    )
    adapter = RssAdapter()

    first_run = adapter.parse_feed(source=source, xml_text=xml_text)
    second_run = adapter.parse_feed(source=source, xml_text=xml_text)

    assert [c.content_hash for c in first_run] == [c.content_hash for c in second_run]


def test_parse_feed_skips_items_without_link() -> None:
    xml_text = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>Sin link</title></item>
      <item><title>Con link</title><link>https://example.com/a</link></item>
    </channel></rss>"""
    source = SourceDefinition(
        id=uuid4(), name="Fuente Test", base_url="https://example.com/feed/", adapter_type="rss"
    )

    candidates = RssAdapter().parse_feed(source=source, xml_text=xml_text)

    assert len(candidates) == 1
    assert candidates[0].url == "https://example.com/a"
