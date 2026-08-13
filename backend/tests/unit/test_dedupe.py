"""Idempotencia por hash a través de las 3 fuentes estáticas (sección 13)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.dedupe import dedupe_by_hash
from app.domain.entities import SourceDefinition
from app.sources.rss_adapter import RssAdapter
from app.sources.scrapy_adapter import ScrapyAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# IDs fijos: en un ciclo real las fuentes ya existen en la tabla `sources` y
# se les asigna el mismo UUID en cada corrida. Generarlos de nuevo en cada
# llamada (como con `uuid4()` por corrida) invalidaría el hash entre pasadas
# y no reflejaría el comportamiento real.
_TICKET_MISIONES = SourceDefinition(
    id=uuid4(),
    name="Ticket Misiones",
    base_url="https://ticketmisiones.com",
    adapter_type="scrapy",
)
_MISIONES_ONLINE = SourceDefinition(
    id=uuid4(),
    name="Misiones Online",
    base_url="https://misionesonline.net/feed/",
    adapter_type="rss",
)
_MISIONES_CUATRO = SourceDefinition(
    id=uuid4(),
    name="Misiones Cuatro",
    base_url="https://misionescuatro.com/espectaculos/feed/",
    adapter_type="rss",
)


def _collect_three_sources() -> list:
    ticket_misiones = _TICKET_MISIONES
    misiones_online = _MISIONES_ONLINE
    misiones_cuatro = _MISIONES_CUATRO

    scrapy_html = (FIXTURES_DIR / "scrapy" / "ticketmisiones.html").read_text(encoding="utf-8")
    scrapy_candidates = ScrapyAdapter().parse_html(
        source=ticket_misiones, html=scrapy_html, page_url=ticket_misiones.base_url
    )

    rss_adapter = RssAdapter()
    mo_xml = (FIXTURES_DIR / "rss" / "misionesonline.xml").read_text(encoding="utf-8")
    mo_candidates = rss_adapter.parse_feed(source=misiones_online, xml_text=mo_xml)
    mc_xml = (FIXTURES_DIR / "rss" / "misionescuatro_espectaculos.xml").read_text(encoding="utf-8")
    mc_candidates = rss_adapter.parse_feed(source=misiones_cuatro, xml_text=mc_xml)

    return scrapy_candidates + mo_candidates + mc_candidates


def test_first_pass_across_three_sources_has_no_internal_duplicates() -> None:
    all_candidates = _collect_three_sources()

    deduped, seen_hashes = dedupe_by_hash(all_candidates)

    assert len(deduped) == len(all_candidates)
    assert len(seen_hashes) == len(all_candidates)
    assert len({c.content_hash for c in all_candidates}) == len(all_candidates)


def test_second_pass_with_identical_content_yields_no_new_candidates() -> None:
    first_pass = _collect_three_sources()
    _, seen_hashes = dedupe_by_hash(first_pass)

    # Simula una segunda corrida del mismo ciclo: mismas 3 fuentes, mismo
    # contenido crudo (nada cambió en los sitios de origen).
    second_pass = _collect_three_sources()
    new_candidates, updated_hashes = dedupe_by_hash(second_pass, seen_hashes=seen_hashes)

    assert new_candidates == []
    assert updated_hashes == seen_hashes


def test_dedupe_filters_repeated_item_within_same_batch() -> None:
    source = SourceDefinition(
        id=uuid4(), name="Fuente Test", base_url="https://example.com/feed/", adapter_type="rss"
    )
    xml_text = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>Repetido</title><link>https://example.com/a</link></item>
      <item><title>Repetido</title><link>https://example.com/a</link></item>
    </channel></rss>"""
    candidates = RssAdapter().parse_feed(source=source, xml_text=xml_text)
    assert len(candidates) == 2  # el parser no dedupea; eso es trabajo de dedupe_by_hash

    deduped, _ = dedupe_by_hash(candidates)

    assert len(deduped) == 1
