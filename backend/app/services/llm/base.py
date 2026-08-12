"""Interfaz del cliente LLM (sección 3.1 y 9 del plan).

`app.agents.analyzer.AnalyzerAgent` debe depender únicamente de `LLMClient`
para poder cambiar de proveedor sin modificarse. `get_llm_client()` es la
única fábrica: si el proveedor no está configurado, devuelve un cliente que
falla explícitamente al usarse (no al importarse), evitando errores
silenciosos en producción.
"""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings
from app.domain.errors import ExternalServiceNotConfiguredError


class LLMClient(Protocol):
    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        """Debe devolver un dict compatible con el schema de la sección 9.1."""
        ...


class NotConfiguredLLMClient:
    """Falla explícitamente: no hay proveedor/modelo Llama configurado todavía."""

    async def extract_event(self, *, text: str, extraction_date_iso: str) -> dict:
        raise ExternalServiceNotConfiguredError(
            "No hay proveedor LLM configurado (LLM_PROVIDER/LLM_MODEL). "
            "Ver sección 3.1 del plan: decisión pendiente del equipo."
        )


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if not settings.llm_provider or not settings.llm_model:
        return NotConfiguredLLMClient()
    if settings.llm_provider.lower() == "ollama":
        from app.services.llm.ollama import OllamaLLMClient

        return OllamaLLMClient()
    raise NotImplementedError(
        f"Proveedor LLM '{settings.llm_provider}' declarado pero sin "
        "implementación de cliente todavía."
    )
