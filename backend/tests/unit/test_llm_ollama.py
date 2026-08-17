"""Pruebas del cliente Ollama."""

from __future__ import annotations

import httpx
import pytest
from app.services.llm.ollama import OllamaLLMClient


@pytest.mark.asyncio
async def test_extract_event_strips_json_code_fence_with_language_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": '```json\n{"is_event": true, "confidence": 0.85}\n```',
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

    assert result == {"is_event": True, "confidence": 0.85}


@pytest.mark.asyncio
async def test_extract_event_strips_bare_code_fence(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": '```\n{"is_event": true, "confidence": 0.85}\n```'},
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    result = await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")

    assert result == {"is_event": True, "confidence": 0.85}


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
async def test_extract_event_retries_after_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"response": '{"is_event": true, "confidence": 0.8}'})

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
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_extract_event_raises_after_exhausting_retries_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.domain.errors import ExternalServiceNotConfiguredError

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    transport = httpx.MockTransport(handler)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MAX_RETRIES", "1")
    from app.config import get_settings

    get_settings.cache_clear()

    client = OllamaLLMClient(transport=transport)
    with pytest.raises(ExternalServiceNotConfiguredError):
        await client.extract_event(text="texto", extraction_date_iso="2026-08-12T00:00:00Z")


def test_get_llm_client_returns_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "minimax-m3:cloud")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    from app.config import get_settings

    get_settings.cache_clear()

    from app.services.llm.base import get_llm_client

    client = get_llm_client()
    assert client.__class__.__name__ == "OllamaLLMClient"
