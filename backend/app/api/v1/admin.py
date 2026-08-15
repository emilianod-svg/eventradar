"""Rutas internas `/api/v1/internal/*` (sección 12.2).

Requieren `X-Admin-Api-Key` (ver `app/security/admin_auth.py`). Los
endpoints de fuentes son CRUD real y mínimo. `/cycles` ya invoca al
Orquestador real (sección 8.2); `/reviews` lista la cola de revisión real,
pero aprobar/rechazar un caso (`POST /reviews/{id}/approve|reject` de la
sección 12.2) todavía no está implementado — no forma parte de esta tarea
(PersistenceAgent + Orquestador) y no tiene fecha propia en el cronograma
10/08-20/08.

`POST /cycles` corre el ciclo de forma síncrona dentro del request: es un
endpoint interno de administración, no público, y el disparo periódico real
va a venir de APScheduler (sección 13, 17/08) llamando a `OrchestratorAgent`
directo, no por HTTP.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.orchestrator import OrchestratorAgent
from app.domain.errors import NotFoundError, NotImplementedYetError
from app.models.execution import Execution
from app.models.execution_source import ExecutionSource
from app.models.review_item import ReviewItem
from app.models.source import Source
from app.security.admin_auth import require_admin

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_admin)])


class SourceIn(BaseModel):
    name: str
    base_url: str
    adapter_type: str
    active: bool = True
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0)


class SourceOut(SourceIn):
    id: UUID

    model_config = {"from_attributes": True}


class SourcePatch(BaseModel):
    active: bool | None = None
    reliability_score: float | None = Field(default=None, ge=0.0, le=1.0)


@router.get("/sources", response_model=list[SourceOut], summary="Lista fuentes configuradas")
async def list_sources() -> list[SourceOut]:
    sources = await Source.all()
    return [SourceOut.model_validate(s) for s in sources]


@router.post("/sources", response_model=SourceOut, status_code=201, summary="Alta de fuente")
async def create_source(payload: SourceIn) -> SourceOut:
    source = await Source.create(**payload.model_dump())
    return SourceOut.model_validate(source)


@router.patch("/sources/{source_id}", response_model=SourceOut, summary="Modificación/activación")
async def patch_source(source_id: UUID, payload: SourcePatch) -> SourceOut:
    source = await Source.get_or_none(id=source_id)
    if source is None:
        raise NotFoundError(f"Fuente '{source_id}' no encontrada.")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(source, key, value)
    if updates:
        await source.save()
    return SourceOut.model_validate(source)


class ExecutionSourceOut(BaseModel):
    id: UUID
    source_id: UUID
    status: str
    items_collected: int
    items_accepted: int
    error_message: str | None
    duration_ms: float | None

    model_config = {"from_attributes": True}


class ExecutionOut(BaseModel):
    id: UUID
    status: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    metrics: dict
    error_message: str | None

    model_config = {"from_attributes": True}


class ExecutionDetailOut(ExecutionOut):
    sources: list[ExecutionSourceOut]


class ReviewItemOut(BaseModel):
    id: UUID
    classification_id: UUID
    status: str
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/cycles", response_model=ExecutionOut, status_code=201, summary="Inicia ciclo manual")
async def start_cycle() -> ExecutionOut:
    metadata = await OrchestratorAgent(triggered_by="manual_api").execute()
    execution = await Execution.get(id=metadata.execution_id)
    return ExecutionOut.model_validate(execution)


@router.get("/cycles", response_model=list[ExecutionOut], summary="Lista ejecuciones")
async def list_cycles(limit: int = 20, offset: int = 0) -> list[ExecutionOut]:
    executions = await Execution.all().offset(offset).limit(limit)
    return [ExecutionOut.model_validate(e) for e in executions]


@router.get(
    "/cycles/{execution_id}",
    response_model=ExecutionDetailOut,
    summary="Detalle y errores de una ejecución",
)
async def get_cycle(execution_id: UUID) -> ExecutionDetailOut:
    execution = await Execution.get_or_none(id=execution_id)
    if execution is None:
        raise NotFoundError(f"Ejecución '{execution_id}' no encontrada.")
    exec_sources = await ExecutionSource.filter(execution=execution)
    return ExecutionDetailOut(
        **ExecutionOut.model_validate(execution).model_dump(),
        sources=[ExecutionSourceOut.model_validate(s) for s in exec_sources],
    )


@router.get("/reviews", response_model=list[ReviewItemOut], summary="Cola de revisión")
async def list_reviews(limit: int = 50, offset: int = 0) -> list[ReviewItemOut]:
    items = await ReviewItem.filter(status="PENDING").offset(offset).limit(limit)
    return [ReviewItemOut.model_validate(i) for i in items]


@router.post("/reviews/{review_id}/approve", summary="Aprobar caso de revisión", status_code=501)
async def approve_review(review_id: UUID) -> None:
    raise NotImplementedYetError(
        "Aprobar un ReviewItem implica reconstruir un EventCandidate desde "
        "Classification.extracted_fields y correrlo por un camino de "
        "aceptación equivalente al del Evaluador — no forma parte de esta "
        "tarea (PersistenceAgent + Orquestador)."
    )


@router.post("/reviews/{review_id}/reject", summary="Rechazar caso de revisión", status_code=501)
async def reject_review(review_id: UUID) -> None:
    raise NotImplementedYetError(
        "Rechazar un ReviewItem todavía no está implementado — no forma "
        "parte de esta tarea (PersistenceAgent + Orquestador)."
    )
