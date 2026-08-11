"""`/health` y `/ready` (sección 12.1 del plan, fuera del prefijo `/api/v1`)."""

from __future__ import annotations

from fastapi import APIRouter
from tortoise import connections
from tortoise.exceptions import DBConnectionError

router = APIRouter(tags=["health"])


@router.get("/health", summary="Estado básico del proceso")
async def health() -> dict:
    """No depende de la base de datos: solo confirma que el proceso responde."""

    return {"status": "ok"}


@router.get("/ready", summary="Verifica dependencias críticas (PostgreSQL)")
async def ready() -> dict:
    """Ejecuta un `SELECT 1` contra la conexión por defecto de Tortoise.

    Devuelve 200 con `{"status": "ok"}` si la base responde, o 200 con
    `{"status": "degraded", ...}` describiendo el fallo si no. La decisión de
    exponer 200 vs 503 en caso de falla queda documentada como pendiente P1
    (ver informe de inicialización); por ahora se devuelve el detalle para
    que el equipo decida la política de orquestación/health-checks.
    """

    try:
        conn = connections.get("default")
        await conn.execute_query("SELECT 1")
        return {"status": "ok", "database": "up"}
    except (DBConnectionError, Exception) as exc:  # noqa: BLE001
        return {"status": "degraded", "database": "down", "detail": str(exc)}
