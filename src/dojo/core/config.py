"""Application settings management."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed configuration for the Dojo application.

    Attributes
    ----------
    db_path : Path
        Path to the DuckDB ledger file.
    testing : bool
        Flag to enable/disable testing-specific functionality.
    api_host : str
        Default host bound by API servers.
    api_port : int
        Default port bound by API servers.
    """

    db_path: Path = Field(
        default=Path("data/ledger.duckdb"),
        description="Path to the DuckDB ledger file.",
    )
    testing: bool = Field(
        default=False,
        description="Flag to enable/disable testing-specific functionality.",
    )
    api_host: str = Field(default="0.0.0.0", description="Default host bound by API servers.")
    api_port: int = Field(default=8000, description="Default port bound by API servers.")
    run_startup_migrations: bool = Field(
        default=False,
        description=(
            "Whether the app applies migrations on startup. "
            "Keep true for dev/test, false for prod when a preflight runs."
        ),
    )

    # Aspire migration / onboarding
    google_oauth_client_id: str | None = Field(
        default=None,
        validation_alias="GOOGLE_CLIENT_ID",
        description="Google OAuth client id (Sheets read-only).",
    )
    google_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias="GOOGLE_CLIENT_SECRET",
        description="Google OAuth client secret (Sheets read-only).",
    )
    google_oauth_redirect_uri: str | None = Field(
        default=None,
        validation_alias="GOOGLE_REDIRECT_URI",
        description="Optional explicit redirect URI for Google OAuth callback.",
    )

    aspire_migration_allow_partial_mapping: bool = Field(
        default=False,
        description="Dev/test helper: allow advancing with partial mapping/decisions.",
    )

    aspire_migration_session_ttl_days: int = Field(
        default=14,
        description="TTL for abandoned Aspire migration sessions (best-effort cleanup).",
    )

    model_config = SettingsConfigDict(
        env_prefix="dojo_",
        env_file=".env",
        env_file_encoding="utf-8",
        # Why: Enable case-insensitive matching for environment variable names,
        # allowing flexibility in deployment environments.
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Load and cache settings for reuse across the process.

    This function uses `lru_cache` to ensure that settings are loaded only once
    per process, improving performance and consistency.

    Returns
    -------
    Settings
        The application settings instance.
    """

    return Settings()
