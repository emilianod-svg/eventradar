"""Punto de entrada de FastAPI (sección 6 y 12 del plan)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import RegisterTortoise

from app.api import health as health_api
from app.api.v1 import router as v1_router
from app.config import get_settings
from app.domain.errors import AppError, error_envelope
from app.observability import configure_logging, new_correlation_id, set_correlation_id
from app.services.sources.bootstrap import SourceBootstrapService
from app.services.sources.normalization import normalize_adapter_type
from app.services.sources.validation import SourceValidationService

logger = logging.getLogger("eventradar")


async def _run_source_background_tasks(app: FastAPI) -> None:
    settings = get_settings()
    validator = SourceValidationService()
    validated_ok = 0
    validated_invalid = 0
    discovered_candidates_count = 0
    discovered_inserted = 0
    try:
        from app.models.source import Source

        sources = await Source.filter(active=True)
        for source in sources:
            try:
                if settings.source_validate_on_startup:
                    validation = await validator.validate_source(source)
                    if validation.ok:
                        validated_ok += 1
                    else:
                        validated_invalid += 1
                    await validator.persist_validation(source, validation)

                if (
                    settings.source_discovery_enabled
                    and normalize_adapter_type(source.adapter_type) == "scrapy"
                ):
                    discovery = await validator.discover_feeds(source)
                    if discovery.ok and discovery.discovered_urls:
                        validated_candidates: list[str] = []
                        for candidate_url in discovery.discovered_urls:
                            discovered_candidates_count += 1
                            candidate = await validator.validate_catalog_entry(
                                SimpleNamespace(
                                    name=source.name,
                                    base_url=candidate_url,
                                    adapter_type="rss",
                                )
                            )
                            if candidate.ok:
                                validated_candidates.append(candidate_url)
                        if validated_candidates:
                            discovered_inserted += await validator.persist_discovered_urls(
                                source, validated_candidates
                            )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "source_background_task_failed",
                    extra={"source_id": str(source.id), "source_name": source.name},
                )
    except Exception:  # noqa: BLE001
        logger.exception("source_background_task_failed")
    else:
        logger.info(
            "source_background_tasks_completed",
            extra={
                "validated_ok": validated_ok,
                "validated_invalid": validated_invalid,
                "discovered_candidates": discovered_candidates_count,
                "discovered_inserted": discovered_inserted,
            },
        )


async def _cancel_source_background_task(app: FastAPI) -> None:
    task = getattr(app.state, "source_background_task", None)
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    async with RegisterTortoise(
        app=app,
        db_url=settings.resolved_database_url,
        modules={"models": ["app.models"]},
        generate_schemas=False,
        add_exception_handlers=False,
    ):
        if settings.source_bootstrap_enabled:
            await SourceBootstrapService().bootstrap()
        if settings.source_validate_on_startup or settings.source_discovery_enabled:
            app.state.source_background_task = asyncio.create_task(
                _run_source_background_tasks(app)
            )
        logger.info("EventRadar backend iniciado (environment=%s)", settings.environment)
        yield
        await _cancel_source_background_task(app)
    logger.info("EventRadar backend detenido")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="EventRadar API",
        version="0.1.0",
        description=(
            "Centralización y recomendación de eventos locales — Posadas, "
            "Misiones. Ver EventRadar_Plan_Completo-v1.md para el contrato "
            "funcional completo."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_origins_list != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        incoming = request.headers.get("x-correlation-id")
        correlation_id = incoming or new_correlation_id()
        set_correlation_id(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        correlation_id = request.headers.get("x-correlation-id") or "unknown"
        logger.warning(
            "AppError code=%s status=%s message=%s", exc.code, exc.status_code, exc.message
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                correlation_id=correlation_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = request.headers.get("x-correlation-id") or "unknown"
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_envelope(
                code="internal_error",
                message="Ocurrió un error interno inesperado.",
                details={},
                correlation_id=correlation_id,
            ),
        )

    app.include_router(health_api.router)
    app.include_router(v1_router)

    return app


app = create_app()
