"""Contrato genérico de agentes y tipos de intercambio entre etapas.

Ver sección 8 del plan ("Contratos entre agentes"). Estos tipos son
deliberadamente mínimos en esta inicialización: describen la forma de los
datos que viajarán entre agentes, sin implementar la lógica de negocio (que
queda fuera de alcance de esta primera vertical, según el prompt de
inicialización).
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

InputT = TypeVar("InputT", contravariant=True)
OutputT = TypeVar("OutputT", covariant=True)


class Agent(Protocol, Generic[InputT, OutputT]):
    """Contrato común que deben cumplir todos los agentes (sección 8.1).

    - Recibe un objeto tipado y devuelve un resultado tipado.
    - No conoce detalles internos de otros agentes.
    - Debe ser ejecutable de forma aislada en tests.
    """

    async def execute(self, data: InputT) -> OutputT: ...


class AgentRunMetadata(BaseModel):
    """Metadatos que cada agente debe registrar al ejecutarse (sección 8.1)."""

    agent: str
    duration_ms: float
    status: str
    error_code: str | None = None
    correlation_id: str | None = None
    execution_id: UUID | None = None


class SourceDefinition(BaseModel):
    """Entrada del Agente Recolector (sección 8.4)."""

    id: UUID
    name: str
    base_url: str
    adapter_type: str
    reliability_score: float = Field(ge=0.0, le=1.0, default=0.5)
    active: bool = True


class RawContentCandidate(BaseModel):
    """Salida del Agente Recolector / entrada del Agente Analizador (8.4-8.5)."""

    source_id: UUID
    url: str
    raw_text: str
    image_urls: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime
    content_hash: str
    adapter_metadata: dict = Field(default_factory=dict)


class EventCandidate(BaseModel):
    """Salida del Agente Analizador (sección 9.1 — schema del LLM)."""

    is_event: bool
    confidence: float = Field(ge=0.0, le=1.0)
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    recurrence_text: str | None = None
    venue_name: str | None = None
    address: str | None = None
    price_text: str | None = None
    description: str | None = None
    category: str | None = None
    special_requirements: str | None = None
    evidence: dict[str, str] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Salida del Agente Evaluador (sección 8.7)."""

    decision: str  # ACCEPT | REJECT | REVIEW | MERGE
    reasons: list[str] = Field(default_factory=list)
    duplicate_of: UUID | None = None
    score: float | None = None
