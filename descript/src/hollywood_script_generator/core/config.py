"""Application configuration settings.

This module provides the Settings class which loads configuration from
environment variables and .env files. It uses pydantic-settings for
validation and type coercion.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be configured via environment variables or a .env file.
    See .env.example for a complete list of available options.

    Attributes:
        # Application Settings
        APP_NAME: Application display name.
        APP_ENV: Environment (development, testing, production).
        DEBUG: Enable debug mode.
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        # Server Configuration
        HOST: Server bind address.
        PORT: Server port number.

        # Video Configuration
        VIDEO_DIR: Directory containing MP4 files to process.
        CHUNK_DURATION_SECONDS: Duration of each video chunk in seconds.
        CHUNK_OVERLAP_SECONDS: Overlap between consecutive chunks in seconds.

        # Database Configuration
        DATABASE_URL: Database connection URL.

        # LLM Configuration
        LLM_BASE_URL: Base URL for Ollama/OpenAI-compatible API.
        LLM_MODEL: Model name for script generation.
        LLM_TEMPERATURE: Sampling temperature (0.0-1.0).
        LLM_MAX_TOKENS: Maximum tokens per generation.

        # Whisper Configuration
        WHISPER_MODEL: Whisper model size (tiny, base, small, medium, large).
        WHISPER_DEVICE: Device for inference (cpu, cuda).

        # Video Processing Configuration
        BLACK_FRAME_THRESHOLD: Brightness threshold for black frame detection (0-255).
        BLACK_FRAME_MIN_DURATION: Minimum black frame duration to consider as credits/ads.
        SILENCE_THRESHOLD: dB threshold for silence detection.
        SILENCE_MIN_DURATION: Minimum silence duration to consider as credits/ads.

        # Job Processing Configuration
        MAX_CONCURRENT_JOBS: Maximum number of concurrent processing jobs.
        JOB_TIMEOUT: Job timeout in seconds.

        # Output Configuration
        OUTPUT_DIR: Directory for generated scripts.

        # Testing Configuration
        TEST_DATABASE_URL: Database URL for testing.
        E2E_BASE_URL: Base URL for E2E tests.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =============================================================================
    # Application Settings
    # =============================================================================
    APP_NAME: str = Field(
        default="Hollywood Script Generator", description="Application display name"
    )
    APP_ENV: Literal["development", "testing", "production"] = Field(
        default="development", description="Application environment"
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # =============================================================================
    # Server Configuration
    # =============================================================================
    HOST: str = Field(default="127.0.0.1", description="Server bind address")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Server port number")

    # =============================================================================
    # Video Configuration
    # =============================================================================
    VIDEO_DIR: Path = Field(
        default=Path("/path/to/your/videos"),
        description="Directory containing MP4 files to process",
    )
    CHUNK_DURATION_SECONDS: int = Field(
        default=30, ge=1, description="Duration of each video chunk in seconds"
    )
    CHUNK_OVERLAP_SECONDS: int = Field(
        default=5, ge=0, description="Overlap between consecutive chunks in seconds"
    )

    # =============================================================================
    # Database Configuration
    # =============================================================================
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/hollywood.db",
        description="Database connection URL",
    )

    # =============================================================================
    # LLM Configuration (Ollama)
    # =============================================================================
    LLM_BASE_URL: str = Field(
        default="http://localhost:11434/v1",
        description="Base URL for Ollama/OpenAI-compatible API",
    )
    LLM_MODEL: str = Field(
        default="llama3.1:70b", description="Model name for script generation"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0-1.0)"
    )
    LLM_MAX_TOKENS: int = Field(
        default=4096, ge=1, description="Maximum tokens per generation"
    )

    # =============================================================================
    # Whisper Configuration
    # =============================================================================
    WHISPER_MODEL: Literal["tiny", "base", "small", "medium", "large"] = Field(
        default="base", description="Whisper model size"
    )
    WHISPER_DEVICE: Literal["cpu", "cuda"] = Field(
        default="cpu", description="Device for inference"
    )

    # =============================================================================
    # Video Processing Configuration
    # =============================================================================
    BLACK_FRAME_THRESHOLD: int = Field(
        default=20,
        ge=0,
        le=255,
        description="Brightness threshold for black frame detection",
    )
    BLACK_FRAME_MIN_DURATION: float = Field(
        default=2.0,
        gt=0,
        description="Minimum black frame duration for credits/ads detection",
    )
    SILENCE_THRESHOLD: int = Field(
        default=-40, le=0, description="dB threshold for silence detection"
    )
    SILENCE_MIN_DURATION: float = Field(
        default=3.0,
        gt=0,
        description="Minimum silence duration for credits/ads detection",
    )

    # =============================================================================
    # Job Processing Configuration
    # =============================================================================
    MAX_CONCURRENT_JOBS: int = Field(
        default=2, ge=1, description="Maximum number of concurrent processing jobs"
    )
    JOB_TIMEOUT: int = Field(default=3600, ge=1, description="Job timeout in seconds")

    # =============================================================================
    # Output Configuration
    # =============================================================================
    OUTPUT_DIR: Path = Field(
        default=Path("./output"), description="Directory for generated scripts"
    )

    # =============================================================================
    # Testing Configuration
    # =============================================================================
    TEST_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/test.db",
        description="Database URL for testing",
    )
    E2E_BASE_URL: str = Field(
        default="http://127.0.0.1:8000", description="Base URL for E2E tests"
    )

    # =============================================================================
    # Validators
    # =============================================================================
    @field_validator("VIDEO_DIR", "OUTPUT_DIR", mode="before")
    @classmethod
    def parse_path(cls, v: Optional[str | Path]) -> Path:
        """Convert string paths to Path objects."""
        if v is None:
            return Path(".")
        if isinstance(v, str):
            return Path(v)
        return v

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        """Validate that overlap is less than chunk duration."""
        if self.CHUNK_OVERLAP_SECONDS >= self.CHUNK_DURATION_SECONDS:
            raise ValueError(
                f"CHUNK_OVERLAP_SECONDS ({self.CHUNK_OVERLAP_SECONDS}) "
                f"must be less than CHUNK_DURATION_SECONDS ({self.CHUNK_DURATION_SECONDS})"
            )
        return self

    def __repr__(self) -> str:
        """Return a string representation with sensitive data masked."""
        return (
            f"Settings("
            f"APP_NAME={self.APP_NAME!r}, "
            f"APP_ENV={self.APP_ENV!r}, "
            f"DEBUG={self.DEBUG}, "
            f"HOST={self.HOST!r}, "
            f"PORT={self.PORT}"
            f")"
        )


# Global settings instance (lazy-loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global Settings instance.

    Returns:
        Settings: The application settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful in testing).

    Returns:
        Settings: A fresh Settings instance.
    """
    global _settings
    _settings = Settings()
    return _settings
