"""Pruebas de `/health` y `/ready` (Fase 3 del prompt de inicialización).

`/health` no depende de la base de datos y corre siempre. `/ready` sí
depende de PostgreSQL: en este entorno de inicialización (sin Docker/red) se
marca como integración y se omite si no hay `TEST_DATABASE_URL` configurada
(ver conftest.py).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_health_does_not_require_database() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # /health se registra antes de que Tortoise esté inicializado, y no
        # abre conexión: no requiere el lifespan de la app.
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ready_reports_database_up() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "up"
