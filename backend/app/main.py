"""Punto de entrada de FastAPI (sección 6 y 12 del plan)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tortoise.contrib.fastapi import RegisterTortoise

from app.api import health as health_api
from app.api.v1 import router as v1_router
from app.config import get_settings
from app.domain.errors import AppError, error_envelope
from app.observability import configure_logging, new_correlation_id, set_correlation_id

logger = logging.getLogger("eventradar")


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
        logger.info("EventRadar backend iniciado (environment=%s)", settings.environment)
        yield
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
