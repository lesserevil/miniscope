"""Pydantic configuration for Auntie bot."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class BotSettings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required fields
    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram bot token from @BotFather")
    CHAT_ID_WHITELIST: str = Field(..., description="Comma-separated list of allowed chat IDs")

    # Optional fields with defaults
    DEBUG: bool = Field(default=False, description="Enable debug mode for verbose logging")
    LOG_LEVEL: str = Field(
        default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    CONVERSATION_RETENTION_DAYS: int = Field(
        default=30, description="Days to retain conversations before archiving"
    )
    ENABLE_BOOKMARK_SKILL: bool = Field(default=True, description="Enable the bookmark skill")
    DATABASE_PATH: str = Field(default="auntie.db", description="Path to SQLite database file")

    @field_validator("TELEGRAM_BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Ensure bot token is not empty."""
        if not v or v.strip() == "":
            raise ValueError("TELEGRAM_BOT_TOKEN must not be empty")
        return v.strip()

    @field_validator("CHAT_ID_WHITELIST")
    @classmethod
    def validate_chat_id_whitelist(cls, v: str) -> str:
        """Ensure chat ID whitelist is not empty."""
        if not v or v.strip() == "":
            raise ValueError("CHAT_ID_WHITELIST must not be empty")
        return v.strip()

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v_upper

    @field_validator("CONVERSATION_RETENTION_DAYS")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        """Ensure retention days is positive."""
        if v < 1:
            raise ValueError("CONVERSATION_RETENTION_DAYS must be at least 1")
        return v

    def get_allowed_chat_ids(self) -> list[str]:
        """Parse CHAT_ID_WHITELIST into list of chat IDs."""
        return [chat_id.strip() for chat_id in self.CHAT_ID_WHITELIST.split(",") if chat_id.strip()]

    def is_chat_allowed(self, chat_id: str | int) -> bool:
        """Check if a chat ID is in the whitelist."""
        chat_id_str = str(chat_id)
        return chat_id_str in self.get_allowed_chat_ids()
