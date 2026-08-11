"""`GET /api/v1/categories` (sección 12.1).

La taxonomía de categorías es extensible y no tiene una tabla propia en esta
inicialización (sección 2.1 del plan: "no está limitado"). Se derivan los
valores distintos ya presentes en `events`.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.domain.enums import EventStatus
from app.models.event import Event

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", summary="Categorías activas (derivadas de eventos existentes)")
async def list_categories() -> dict:
    rows = (
        await Event.filter(status=EventStatus.ACTIVE, category__not_isnull=True)
        .distinct()
        .values_list("category", flat=True)
    )
    return {"items": sorted({c for c in rows if c})}
