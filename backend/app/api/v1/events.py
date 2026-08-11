"""`GET /api/v1/events` y `GET /api/v1/events/{id-or-slug}` (sección 12.1).

Esta es la primera vertical técnica ejecutable: lista y detalle reales contra
PostgreSQL. No incluye todavía filtros geográficos por distancia (requieren
el Clasificador Geográfico, fuera de alcance de esta inicialización) ni
`sort=distance`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.domain.enums import EventStatus
from app.domain.errors import NotFoundError
from app.models.event import Event

router = APIRouter(prefix="/events", tags=["events"])


class EventOut(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str | None
    start_at: datetime
    end_at: datetime | None
    venue_name: str
    address: str | None
    latitude: float | None
    longitude: float | None
    price_text: str | None
    category: str | None
    image_url: str | None
    status: EventStatus

    model_config = {"from_attributes": True}


class PaginatedEvents(BaseModel):
    items: list[EventOut]
    page: int
    page_size: int
    total: int


@router.get("", response_model=PaginatedEvents, summary="Lista paginada de eventos activos")
async def list_events(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    category: str | None = None,
    query: str | None = Query(default=None, description="Búsqueda textual en el título"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedEvents:
    qs = Event.filter(status=EventStatus.ACTIVE)
    if date_from is not None:
        qs = qs.filter(start_at__gte=date_from)
    if date_to is not None:
        qs = qs.filter(start_at__lte=date_to)
    if category:
        qs = qs.filter(category=category)
    if query:
        qs = qs.filter(title__icontains=query)

    total = await qs.count()
    items = await qs.offset((page - 1) * page_size).limit(page_size)
    return PaginatedEvents(
        items=[EventOut.model_validate(e) for e in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{id_or_slug}", response_model=EventOut, summary="Detalle de un evento")
async def get_event(id_or_slug: str) -> EventOut:
    event = None
    try:
        event = await Event.get_or_none(id=UUID(id_or_slug))
    except ValueError:
        event = await Event.get_or_none(slug=id_or_slug)
    if event is None:
        raise NotFoundError(f"Evento '{id_or_slug}' no encontrado.")
    return EventOut.model_validate(event)
