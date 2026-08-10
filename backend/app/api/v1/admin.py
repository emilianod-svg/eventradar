"""Rutas internas `/api/v1/internal/*` (sección 12.2).

Requieren `X-Admin-Api-Key` (ver `app/security/admin_auth.py`). Los
endpoints de fuentes son CRUD real y mínimo. Los endpoints de ciclos y
revisión dependen del Orquestador/Evaluador, que están fuera de alcance de
esta inicialización: responden `501 not_implemented` de forma explícita en
vez de simular un resultado (regla obligatoria del prompt de
inicialización).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.domain.errors import NotFoundError, NotImplementedYetError
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


@router.post("/cycles", summary="Inicia ciclo manual", status_code=501)
async def start_cycle() -> None:
    raise NotImplementedYetError(
        "El Orquestador todavía no está implementado en esta inicialización."
    )


@router.get("/cycles", summary="Lista ejecuciones", status_code=501)
async def list_cycles() -> None:
    raise NotImplementedYetError(
        "El Orquestador todavía no está implementado en esta inicialización."
    )


@router.get("/reviews", summary="Cola de revisión", status_code=501)
async def list_reviews() -> None:
    raise NotImplementedYetError(
        "El Evaluador y la cola de revisión todavía no están implementados."
    )
