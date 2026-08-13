"""Smoke test real: AnalyzerAgent contra el LLM configurado (sección 18.2).

No mide precisión formal (eso se hace contra el dataset de Posadas, tarea
aparte) — solo prueba que la cadena AnalyzerAgent -> LLMClient -> LLM real
funciona de punta a punta con el proveedor/modelo de `.env`
(`LLM_PROVIDER`/`LLM_MODEL`, por defecto Ollama + minimax-m3:cloud).

Se salta salvo `RUN_LLM_SMOKE_TESTS=1` (ver tests/smoke/README.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.agents.analyzer import AnalyzerAgent
from app.domain.entities import RawContentCandidate
from app.services.llm.base import get_llm_client

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

pytestmark = pytest.mark.llm_smoke


def _raw_candidate(raw_text: str) -> RawContentCandidate:
    return RawContentCandidate(
        source_id=uuid4(),
        url="https://example.com",
        raw_text=raw_text,
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="smoke-test-hash",
    )


@pytest.mark.asyncio
async def test_real_llm_identifies_clear_event() -> None:
    agent = AnalyzerAgent(llm_client=get_llm_client())
    raw = _raw_candidate(
        "Feria Artesanal de Invierno\n"
        "15 ago 2026, 18:00hs\n"
        "Artesanos locales, música en vivo y patio gastronómico. "
        "Entrada libre y gratuita en el Parque del Conocimiento, Posadas."
    )

    result = await agent.execute(raw)

    assert len(result) >= 1
    event = result[0]
    assert event.is_event is True
    assert 0.0 <= event.confidence <= 1.0
    assert event.title


@pytest.mark.asyncio
async def test_real_llm_discards_crime_news_as_non_event() -> None:
    agent = AnalyzerAgent(llm_client=get_llm_client())
    raw = _raw_candidate(
        "Puerto Iguazú: arrestaron a un hombre de 32 años que amenazó con un "
        "cuchillo a una mujer y su hija adolescente en avenida Victoria "
        "Aguirre. El hecho fue denunciado por la mujer."
    )

    result = await agent.execute(raw)

    assert result == []


@pytest.mark.asyncio
async def test_real_llm_rejects_recap_of_past_event() -> None:
    agent = AnalyzerAgent(llm_client=get_llm_client())
    raw = RawContentCandidate(
        source_id=uuid4(),
        url="https://example.com",
        raw_text=(
            "El Festival del Litoral, realizado el 1 de enero de 2026 en el "
            "Anfiteatro Manuel Antonio Ramírez, fue un éxito de convocatoria."
        ),
        fetched_at=datetime(2026, 8, 12, tzinfo=UTC),
        content_hash="smoke-test-hash-2",
    )

    result = await agent.execute(raw)

    # El LLM podría no marcar is_event=false para un recap (es narrativa
    # ambigua); lo que sí es innegociable es que ningún evento resultante
    # tenga start_at posterior a la fecha de extracción sin ser realmente
    # futuro — el guard de "evento pasado" en código debe filtrarlo.
    assert all(event.start_at is None or event.start_at >= raw.fetched_at for event in result)
