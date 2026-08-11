"""Pruebas unitarias de configuración (Fase 3 del prompt de inicialización)."""

from __future__ import annotations

import pytest
from app.config import Environment, Settings


def test_default_settings_load_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.environment == Environment.LOCAL
    assert settings.cors_origins_list == ["http://localhost:5173"]


def test_resolved_database_url_uses_explicit_override() -> None:
    settings = Settings(_env_file=None, database_url="postgres://x:y@z:5432/db")
    assert settings.resolved_database_url == "postgres://x:y@z:5432/db"


def test_resolved_database_url_builds_from_parts() -> None:
    settings = Settings(
        _env_file=None,
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5432,
        postgres_db="d",
    )
    assert settings.resolved_database_url == "postgres://u:p@h:5432/d"


def test_production_requires_admin_api_key() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment=Environment.PRODUCTION, admin_api_key=None)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            admin_api_key="secret",
            cors_allowed_origins="*",
            postgres_password="not-the-default",
        )


def test_cors_wildcard_allowed_outside_production() -> None:
    settings = Settings(_env_file=None, cors_allowed_origins="*")
    assert settings.cors_origins_list == ["*"]
