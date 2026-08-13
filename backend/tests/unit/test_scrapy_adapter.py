"""Pruebas del primer adaptador estático."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.domain.entities import SourceDefinition
from app.sources.scrapy_adapter import ScrapyAdapter


def test_parse_html_fixture_to_raw_content_candidates() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "scrapy" / "ticketmisiones.html"
    )
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


def test_parse_html_survives_nested_containers_inside_card() -> None:
    # Markup real de portales de noticias tipo WordPress (visto en Misiones
    # Cuatro): la tarjeta envuelve el título en un <div> intermedio y trae un
    # <a> extra para la imagen. Antes del fix, el </div> intermedio cerraba
    # la tarjeta antes de tiempo y el <a> de la imagen pisaba la URL real.
    html = """
    <article class="post-123 post type-post status-publish hentry category-espectaculos">
        <div class="post-data">
            <h1><a href="/notas/evento-real">Evento real con div anidado</a></h1>
        </div>
        <figure>
            <a href="/notas/evento-real">
                <picture><img src="/img.jpg" /></picture>
            </a>
        </figure>
    </article>
    """
    source = SourceDefinition(
        id=uuid4(),
        name="Misiones Cuatro",
        base_url="https://misionescuatro.com",
        adapter_type="scrapy",
    )

    candidates = ScrapyAdapter().parse_html(source=source, html=html, page_url=source.base_url)

    assert len(candidates) == 1
    assert candidates[0].url == "https://misionescuatro.com/notas/evento-real"
    assert "Evento real con div anidado" in candidates[0].raw_text
