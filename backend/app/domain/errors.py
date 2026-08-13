"""Errores de aplicación y formato común de respuesta de error.

Toda respuesta de error de la API sigue el contrato:
`{"code": str, "message": str, "details": dict | None, "correlation_id": str}`
(sección 12.3 del plan).
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Excepción base de dominio. Las capas superiores la traducen a HTTP."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AppError):
    """Falta o es inválida una variable de configuración obligatoria."""

    code = "configuration_error"
    status_code = 500


class ExternalServiceNotConfiguredError(AppError):
    """Un adaptador externo (LLM, OCR, geocoding, fuente) no tiene credenciales.

    Se usa para fallar explícitamente en vez de simular una respuesta cuando
    todavía no existen credenciales o decisiones del equipo (regla obligatoria
    del prompt de inicialización: "deben fallar de manera explícita y
    entendible, no silenciosamente").
    """

    code = "external_service_not_configured"
    status_code = 503


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ValidationAppError(AppError):
    code = "validation_error"
    status_code = 422


class ConcurrentExecutionError(AppError):
    """Ya existe una ejecución `RUNNING` (sección 13 del plan)."""

    code = "execution_already_running"
    status_code = 409


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401


def error_envelope(
    *, code: str, message: str, details: dict[str, Any] | None, correlation_id: str
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "correlation_id": correlation_id,
    }


class SourceFetchError(AppError):
    """Un adaptador de fuente no pudo descargar/parsear contenido (sección 13).

    Debe usarse para aislar el fallo a una sola fuente: quien orqueste el
    ciclo captura esta excepción por fuente y continúa con las demás
    ("un fallo no cancela las otras fuentes").
    """

    code = "source_fetch_failed"
    status_code = 502


class NotImplementedYetError(AppError):
    """La funcionalidad existe como contrato pero su lógica aún no se implementó.

    Se usa en endpoints que dependen de agentes fuera de alcance de esta
    inicialización (orquestador, evaluador, etc.), para responder de forma
    explícita en vez de simular un resultado.
    """

    code = "not_implemented"
    status_code = 501
