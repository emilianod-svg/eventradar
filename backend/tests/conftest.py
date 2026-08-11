"""Fixtures compartidas.

Las pruebas de integración que requieren PostgreSQL real se marcan con
`@pytest.mark.integration` y se saltan automáticamente si `TEST_DATABASE_URL`
no está definida (ver README, sección "Tests").
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("TEST_DATABASE_URL"):
        return
    skip_integration = pytest.mark.skip(
        reason="TEST_DATABASE_URL no está definida: se omiten pruebas de integración."
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
