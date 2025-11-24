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
    api_host: str = Field(
        default="0.0.0.0", description="Default host bound by API servers."
    )
    api_port: int = Field(
        default=8000, description="Default port bound by API servers."
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
