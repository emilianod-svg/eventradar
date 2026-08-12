"""Pruebas del cliente Ollama."""

from __future__ import annotations

import httpx
import pytest

from app.services.llm.ollama import OllamaLLMClient


@pytest.mark.asyncio
async def test_extract_event_parses_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        return httpx.Response(200, json={"response": '{"is_event": true, "confidence": 0.88}'})

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MAX_TOKENS", "256")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "5")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient()

    client = OllamaLLMClient(transport=transport)
    result = await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")
    assert result["is_event"] is True
    assert result["confidence"] == 0.88


def test_get_llm_client_returns_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()

    from app.services.llm.base import get_llm_client

    client = get_llm_client()
    assert client.__class__.__name__ == "OllamaLLMClient"
