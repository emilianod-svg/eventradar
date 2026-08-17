"""Pruebas del cliente Ollama."""

from __future__ import annotations

import json

import httpx
import pytest
from app.services.llm.ollama import OllamaLLMClient


@pytest.mark.asyncio
async def test_extract_event_parses_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        payload = json.loads(request.content)
        assert payload["format"] == "json"
        return httpx.Response(200, json={"response": '{"is_event": true, "confidence": 0.88}'})

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    result = await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")
    assert result["is_event"] is True
    assert result["confidence"] == 0.88


@pytest.mark.asyncio
async def test_extract_event_retries_once_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            httpx.Response(200, json={"response": "esto no es JSON"}),
            httpx.Response(200, json={"response": '{"is_event": true, "confidence": 0.8}'}),
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["format"] == "json"
        return next(responses)

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    result = await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")

    assert result == {"is_event": True, "confidence": 0.8}


@pytest.mark.asyncio
async def test_extract_event_raises_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["format"] == "json"
        return httpx.Response(200, json={"response": "esto no es JSON"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    with pytest.raises(ValueError):
        await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")


@pytest.mark.asyncio
async def test_extract_event_recovers_json_from_fenced_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["format"] == "json"
        return httpx.Response(
            200,
            json={
                "response": "Aquí va la respuesta:\n```json\n{\"is_event\": true, \"confidence\": 0.91}\n```\nGracias",
            },
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    result = await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")

    assert result == {"is_event": True, "confidence": 0.91}


def test_get_llm_client_returns_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()

    from app.services.llm.base import get_llm_client

    client = get_llm_client()
    assert client.__class__.__name__ == "OllamaLLMClient"
