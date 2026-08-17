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


def test_resolved_database_url_builds_from_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
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


def test_source_bootstrap_defaults_are_enabled() -> None:
    settings = Settings(_env_file=None)

    assert settings.source_bootstrap_enabled is True
    assert settings.source_validate_on_startup is False
    assert settings.source_discovery_enabled is False
    assert settings.source_request_timeout_seconds == 10.0
    assert settings.source_max_redirects == 3


def test_decision_thresholds_default_to_plan_values() -> None:
    settings = Settings(_env_file=None)

    assert settings.confidence_review_threshold == 0.50
    assert settings.confidence_accept_threshold == 0.70
    assert settings.duplicate_candidate_threshold == 0.50
    assert settings.duplicate_review_threshold == 0.75
    assert settings.duplicate_auto_merge_threshold == 0.90
    assert settings.geo_catalog_match_threshold == 0.85


def test_decision_thresholds_are_configurable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIDENCE_REVIEW_THRESHOLD", "0.40")
    monkeypatch.setenv("CONFIDENCE_ACCEPT_THRESHOLD", "0.60")
    monkeypatch.setenv("DUPLICATE_AUTO_MERGE_THRESHOLD", "0.95")

    settings = Settings(_env_file=None)

    assert settings.confidence_review_threshold == 0.40
    assert settings.confidence_accept_threshold == 0.60
    assert settings.duplicate_auto_merge_threshold == 0.95


def test_confidence_review_above_accept_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            confidence_review_threshold=0.80,
            confidence_accept_threshold=0.70,
        )


def test_duplicate_thresholds_out_of_order_are_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            duplicate_candidate_threshold=0.80,
            duplicate_review_threshold=0.75,
        )
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            duplicate_review_threshold=0.95,
            duplicate_auto_merge_threshold=0.90,
        )


def test_decision_thresholds_out_of_range_are_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, confidence_accept_threshold=1.5)
    with pytest.raises(ValueError):
        Settings(_env_file=None, duplicate_review_threshold=-0.1)
