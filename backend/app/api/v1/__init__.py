"""Agregador de routers bajo el prefijo `/api/v1` (sección 12 del plan)."""

from fastapi import APIRouter

from app.api.v1 import admin, categories, events

router = APIRouter(prefix="/api/v1")
router.include_router(events.router)
router.include_router(categories.router)
router.include_router(admin.router)
