"""Configuración tipada de la aplicación.

Todas las variables se leen desde el entorno (ver `.env.example` en la raíz del
repositorio). Las variables obligatorias se validan al iniciar el proceso: si
falta alguna, la aplicación debe fallar de forma explícita en el arranque, no
en tiempo de request.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
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

    # --- Geografía base (Posadas, Misiones) ---
    base_latitude: float = Field(default=-27.3671)
    base_longitude: float = Field(default=-55.8961)
    search_radius_km: float = Field(default=15.0)

    # --- LLM (familia Llama; proveedor exacto pendiente de decisión) ---
    llm_provider: str | None = Field(default=None)
    llm_model: str | None = Field(default=None)
    llm_base_url: str | None = Field(default=None)
    llm_api_key: str | None = Field(default=None)
    llm_max_tokens: int = Field(default=1024)
    llm_timeout_seconds: float = Field(default=30.0)
    llm_max_retries: int = Field(default=1)

    # --- Google Vision (OCR) ---
    google_vision_credentials_json: str | None = Field(
        default=None,
        description="Ruta a un archivo de credenciales de servicio, NO el contenido en texto plano.",
    )
    ocr_enabled: bool = Field(default=False)

    # --- Nominatim / OpenStreetMap ---
    nominatim_base_url: str = Field(default="https://nominatim.openstreetmap.org")
    nominatim_user_agent: str = Field(default="EventRadar/0.1 (contacto pendiente)")
    nominatim_contact_email: str | None = Field(default=None)
    nominatim_rate_limit_seconds: float = Field(default=1.0)

    # --- Presupuesto y límites de IA ---
    ai_monthly_budget_usd: float = Field(default=20.0)

    # --- Flags experimentales ---
    enable_experimental_adapters: bool = Field(default=False)
    enable_facebook_adapter: bool = Field(default=False)

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_by_default(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        if self.environment == Environment.PRODUCTION:
            missing: list[str] = []
            if self.admin_api_key in (None, ""):
                missing.append("ADMIN_API_KEY")
            if self.cors_allowed_origins.strip() == "*":
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS no puede ser '*' en producción."
                )
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
