"""Fixtures compartidas.

Las pruebas de integración que requieren PostgreSQL real se marcan con
`@pytest.mark.integration` y se saltan automáticamente si `TEST_DATABASE_URL`
no está definida (ver README, sección "Tests").

Las pruebas "smoke real" (sección 18.2 del plan: "fuera del CI obligatorio")
que llaman a un LLM real se marcan con `@pytest.mark.llm_smoke` y se saltan
salvo que se pida explícitamente con `RUN_LLM_SMOKE_TESTS=1`.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    skip_integration = pytest.mark.skip(
        reason="TEST_DATABASE_URL no está definida: se omiten pruebas de integración."
    )
    skip_llm_smoke = pytest.mark.skip(
        reason="RUN_LLM_SMOKE_TESTS no está definida: se omiten smoke tests contra el LLM real."
    )
    for item in items:
        # `item.keywords` mezcla markers con nombres de directorio/módulo del
        # nodeid (ej. la carpeta `tests/integration/` aporta la key literal
        # "integration"), así que un simple `in` da falsos positivos para
        # tests sin marcar que solo viven en esa carpeta. `get_closest_marker`
        # chequea el marker real.
        if item.get_closest_marker("integration") and not os.environ.get("TEST_DATABASE_URL"):
            item.add_marker(skip_integration)
        if item.get_closest_marker("llm_smoke") and not os.environ.get("RUN_LLM_SMOKE_TESTS"):
            item.add_marker(skip_llm_smoke)
