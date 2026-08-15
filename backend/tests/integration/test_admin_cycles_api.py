"""`/api/v1/internal/cycles` y `/reviews` conectados al Orquestador real (12.2).

No fakea `CollectorAgent`/`AnalyzerAgent` (el endpoint construye
`OrchestratorAgent` con sus defaults, sin puntos de inyección desde la
capa HTTP): la lógica del ciclo en sí ya está cubierta con fakes en
`test_orchestrator_agent.py`. Acá solo se valida el cableado HTTP —
autenticación, forma de la respuesta, listado y detalle — usando una fuente
con URL inalcanzable para que el aislamiento por fuente (sección 6.2)
absorba el fallo de red sin romper el request.
"""

from __future__ import annotations

import pytest
from app.config import get_settings
from app.main import create_app
from app.models.execution import Execution
from app.models.source import Source
from httpx import ASGITransport, AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_cycle_requires_admin_key(tortoise_connection) -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        app.router.lifespan_context(app),
    ):
        response = await client.post("/api/v1/internal/cycles")

    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_cycle_runs_orchestrator_and_lists_it(tortoise_connection) -> None:
    await Source.create(
        name="fuente inalcanzable",
        base_url="https://source-does-not-exist.invalid/feed/",
        adapter_type="rss",
    )

    app = create_app()
    transport = ASGITransport(app=app)
    admin_key = get_settings().admin_api_key
    headers = {"X-Admin-Api-Key": admin_key}

    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        app.router.lifespan_context(app),
    ):
        response = await client.post("/api/v1/internal/cycles", headers=headers)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] in ("COMPLETED", "PARTIAL", "FAILED")
        execution_id = body["id"]

        list_response = await client.get("/api/v1/internal/cycles", headers=headers)
        assert list_response.status_code == 200
        assert any(item["id"] == execution_id for item in list_response.json())

        detail_response = await client.get(
            f"/api/v1/internal/cycles/{execution_id}", headers=headers
        )
        assert detail_response.status_code == 200
        assert "sources" in detail_response.json()

        reviews_response = await client.get("/api/v1/internal/reviews", headers=headers)
        assert reviews_response.status_code == 200

    execution = await Execution.get(id=execution_id)
    assert execution.triggered_by == "manual_api"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_cycle_returns_409_when_already_running(tortoise_connection) -> None:
    from app.domain.enums import ExecutionStatus

    await Execution.create(status=ExecutionStatus.RUNNING, triggered_by="manual")

    app = create_app()
    transport = ASGITransport(app=app)
    admin_key = get_settings().admin_api_key
    headers = {"X-Admin-Api-Key": admin_key}

    async with (
        AsyncClient(transport=transport, base_url="http://test") as client,
        app.router.lifespan_context(app),
    ):
        response = await client.post("/api/v1/internal/cycles", headers=headers)

    assert response.status_code == 409
