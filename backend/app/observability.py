"""Logging estructurado básico y utilidades de correlación (sección 17)."""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    return _correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    _correlation_id_ctx.set(value)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configura logging estructurado (texto plano con campos clave).

    Se evita una dependencia de formato JSON obligatoria para mantener la
    base simple; `python-json-logger` queda declarado en las dependencias
    por si el equipo decide adoptar salida JSON en un entorno productivo.
    """

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationIdFilter())
    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s level=%(levelname)s logger=%(name)s "
            "correlation_id=%(correlation_id)s message=%(message)s"
        )
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
