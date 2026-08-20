"""Configuración tipada de la aplicación.

Todas las variables se leen desde el entorno (ver `.env.example` en la raíz del
repositorio). Las variables obligatorias se validan al iniciar el proceso: si
falta alguna, la aplicación debe fallar de forma explícita en el arranque, no
en tiempo de request.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuración central de EventRadar backend.

    Cada campo documenta su propósito. Los valores por defecto solo se usan
    para desarrollo local; en `staging`/`production` las variables sensibles
    son obligatorias (ver `validate_production_requirements`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Identidad de la aplicación ---
    app_name: str = Field(default="eventradar-backend")
    environment: Environment = Field(default=Environment.LOCAL)
    log_level: str = Field(default="INFO")

    # --- PostgreSQL ---
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="eventradar")
    postgres_user: str = Field(default="eventradar")
    postgres_password: str = Field(default="eventradar")
    database_url: str | None = Field(
        default=None,
        description="Si se define, tiene prioridad sobre los campos postgres_*.",
    )

    # --- CORS ---
    cors_allowed_origins: str = Field(
        default="http://localhost:5173",
        description="Lista separada por comas. Nunca '*' en producción.",
    )

    # --- URLs públicas ---
    backend_public_url: AnyHttpUrl | None = Field(default=None)
    frontend_public_url: AnyHttpUrl | None = Field(default=None)

    # --- Seguridad interna ---
    admin_api_key: str | None = Field(
        default=None,
        description="Credencial requerida en el header X-Admin-Api-Key para /api/v1/internal/*.",
    )

    # --- Zona horaria y scheduler ---
    timezone: str = Field(default="America/Argentina/Cordoba")
    scheduler_enabled: bool = Field(default=False)
    scheduler_cron: str = Field(
        default="0 9 * * 1,5",
        description="Cron para el ciclo (por defecto lunes y viernes 09:00).",
    )
    execution_timeout_minutes: int = Field(
        default=60,
        ge=1,
        description=(
            "Minutos sin finalizar tras los cuales el watchdog marca una "
            "ejecución RUNNING como abandonada (FAILED)."
        ),
    )

    # --- Geografía base (Posadas, Misiones) ---
    base_latitude: float = Field(default=-27.3671)
    base_longitude: float = Field(default=-55.8961)
    search_radius_km: float = Field(default=15.0)

    # --- LLM (familia Llama; proveedor exacto pendiente de decisión) ---
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
    llm_base_url: str | None = Field(default=None)
    llm_api_key: str | None = Field(default=None)
    llm_max_tokens: int = Field(default=8192)
    llm_timeout_seconds: float = Field(default=60.0)
    llm_max_retries: int = Field(default=1)

    # --- Google Vision (OCR) ---
    google_vision_credentials_json: str | None = Field(
        default=None,
        description=(
            "Ruta a un archivo de credenciales de servicio, NO el contenido en texto plano."
        ),
    )
    ocr_enabled: bool = Field(default=False)

    # --- Bootstrap de fuentes ---
    source_catalog_path: str = Field(default="data/source_catalog.json")
    source_bootstrap_enabled: bool = Field(default=True)
    source_validate_on_startup: bool = Field(default=False)
    source_discovery_enabled: bool = Field(default=False)
    source_request_timeout_seconds: float = Field(default=10.0)
    source_max_redirects: int = Field(default=3)
    source_max_response_bytes: int = Field(default=2_000_000)
    source_discovery_max_urls_per_domain: int = Field(default=5)
    source_user_agent: str = Field(default="EventRadar/0.1 (source bootstrap)")

    # --- Nominatim / OpenStreetMap ---
    nominatim_base_url: str = Field(default="https://nominatim.openstreetmap.org")
    nominatim_user_agent: str = Field(default="EventRadar/0.1 (contacto pendiente)")
    nominatim_contact_email: str | None = Field(default=None)
    nominatim_enabled: bool = Field(default=True)
    nominatim_rate_limit_seconds: float = Field(default=1.0)

    # --- Geocodificación (free tier / fallback) ---
    locationiq_enabled: bool = Field(default=False)
    locationiq_api_key: str | None = Field(default=None)
    locationiq_base_url: str = Field(default="https://us1.locationiq.com/v1")
    geoapify_enabled: bool = Field(default=False)
    geoapify_api_key: str | None = Field(default=None)
    geoapify_base_url: str = Field(default="https://api.geoapify.com/v1")
    geocoding_provider_order: str = Field(default="nominatim,locationiq,geoapify")
    geocoding_timeout_seconds: float = Field(default=5.0)
    geocoding_cache_ttl_seconds: int = Field(default=30 * 24 * 3600)
    geocoding_negative_cache_ttl_seconds: int = Field(default=3600)
    geocoding_max_attempts: int = Field(default=3)
    geocoding_backoff_base_seconds: float = Field(default=0.5)
    geocoding_backoff_jitter_seconds: float = Field(default=0.2)
    geocoding_circuit_breaker_threshold: int = Field(default=3)
    geocoding_circuit_breaker_reset_seconds: float = Field(default=60.0)
    geocoding_allowed_country_code: str = Field(default="ar")
    geocoding_catalog_path: str = Field(default="data/geocoding_catalog.json")
    geocoding_consensus_min_providers: int = Field(
        default=2,
        ge=1,
        description="Cantidad mínima de proveedores que deben coincidir para aceptar un consenso.",
    )
    geocoding_consensus_max_distance_meters: float = Field(
        default=300.0,
        ge=0.0,
        description=(
            "Distancia máxima entre proveedores para considerar que apuntan al mismo lugar."
        ),
    )

    # --- Umbrales geográficos ---
    geo_confidence_reject_threshold: float = Field(default=0.50)
    geo_confidence_review_threshold: float = Field(default=0.75)
    geo_confidence_auto_threshold: float = Field(default=0.90)
    geo_catalog_match_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description=(
            "Score de coincidencia contra el catálogo de ubicaciones para dar el lugar "
            "por 'match exacto'."
        ),
    )
    geo_allowed_min_latitude: float | None = Field(default=None)
    geo_allowed_max_latitude: float | None = Field(default=None)
    geo_allowed_min_longitude: float | None = Field(default=None)
    geo_allowed_max_longitude: float | None = Field(default=None)

    # --- Umbrales de decisión (Analizador / Evaluador, ver app/domain/decisions.py) ---
    confidence_review_threshold: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description=(
            "Confianza mínima del LLM para no descartar el candidato (por debajo, se rechaza)."
        ),
    )
    confidence_accept_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description=(
            "Confianza mínima para aceptar sin marcarlo a revisión manual "
            "(entre REVIEW y ACCEPT queda en pending_review)."
        ),
    )
    duplicate_candidate_threshold: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description=(
            "Similitud de título mínima para considerar dos eventos 'candidatos' "
            "a duplicado (no implica fusión)."
        ),
    )
    duplicate_review_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Score de duplicado a partir del cual se manda a revisión manual.",
    )
    duplicate_auto_merge_threshold: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description=(
            "Score de duplicado a partir del cual se fusiona automáticamente "
            "(requiere además compatibilidad de fecha y ubicación)."
        ),
    )

    # --- Google Geocoding (fallback futuro) ---
    google_geocoding_base_url: str = Field(
        default="https://maps.googleapis.com/maps/api/geocode/json"
    )
    google_geocoding_api_key: str | None = Field(default=None)
    google_geocoding_enabled: bool = Field(default=False)

    # --- Presupuesto y límites de IA ---
    ai_monthly_budget_usd: float = Field(default=20.0)

    # --- Evaluador ---
    evaluation_future_horizon_days: int = Field(default=365)
    evaluation_allowed_source_hosts: str = Field(default="")

    # --- Flags experimentales ---
    enable_experimental_adapters: bool = Field(default=False)
    enable_facebook_adapter: bool = Field(default=False)

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_by_default(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_decision_thresholds(self) -> Settings:
        if self.confidence_review_threshold > self.confidence_accept_threshold:
            raise ValueError(
                "CONFIDENCE_REVIEW_THRESHOLD no puede ser mayor que CONFIDENCE_ACCEPT_THRESHOLD "
                f"({self.confidence_review_threshold} > {self.confidence_accept_threshold})."
            )
        if self.duplicate_candidate_threshold > self.duplicate_review_threshold:
            raise ValueError(
                "DUPLICATE_CANDIDATE_THRESHOLD no puede ser mayor que DUPLICATE_REVIEW_THRESHOLD "
                f"({self.duplicate_candidate_threshold} > {self.duplicate_review_threshold})."
            )
        if self.duplicate_review_threshold > self.duplicate_auto_merge_threshold:
            raise ValueError(
                "DUPLICATE_REVIEW_THRESHOLD no puede ser mayor que DUPLICATE_AUTO_MERGE_THRESHOLD "
                f"({self.duplicate_review_threshold} > {self.duplicate_auto_merge_threshold})."
            )
        return self

    @model_validator(mode="after")
    def validate_production_requirements(self) -> Settings:
        if self.environment == Environment.PRODUCTION:
            missing: list[str] = []
            if self.admin_api_key in (None, ""):
                missing.append("ADMIN_API_KEY")
            if self.cors_allowed_origins.strip() == "*":
                raise ValueError("CORS_ALLOWED_ORIGINS no puede ser '*' en producción.")
            if not self.database_url and self.postgres_password == "eventradar":
                missing.append("POSTGRES_PASSWORD (valor por defecto inseguro)")
            if missing:
                raise ValueError(
                    "Faltan variables obligatorias en producción: " + ", ".join(missing)
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def geocoding_provider_order_list(self) -> list[str]:
        return [
            provider.strip().casefold()
            for provider in self.geocoding_provider_order.split(",")
            if provider.strip()
        ]

    @property
    def has_geo_allowed_bbox(self) -> bool:
        return all(
            value is not None
            for value in (
                self.geo_allowed_min_latitude,
                self.geo_allowed_max_latitude,
                self.geo_allowed_min_longitude,
                self.geo_allowed_max_longitude,
            )
        )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgres://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (una sola lectura del entorno)."""

    return Settings()


def build_tortoise_orm_config(database_url: str | None = None) -> dict:
    """Config de Tortoise ORM compatible con Aerich.

    Se expone como función (y como constante `TORTOISE_ORM` más abajo) para que
    Aerich pueda importar `app.config.TORTOISE_ORM` sin depender de variables
    de entorno adicionales.
    """

    settings = get_settings()
    return {
        "connections": {"default": database_url or settings.resolved_database_url},
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "default",
            }
        },
        "timezone": "UTC",
        "use_tz": True,
    }


# Punto de entrada que usa Aerich (`aerich.ini` -> `app.config.TORTOISE_ORM`).
TORTOISE_ORM = build_tortoise_orm_config()
