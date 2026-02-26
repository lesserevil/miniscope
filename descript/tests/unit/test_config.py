"""Tests for configuration settings."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from hollywood_script_generator.core.config import Settings


class TestSettings:
    """Test suite for Settings configuration class."""

    def test_settings_default_values(self):
        """Test that Settings loads with default values."""
        # Clear env vars to test defaults
        for key in list(os.environ.keys()):
            if key.startswith(
                (
                    "APP_",
                    "HOST",
                    "PORT",
                    "VIDEO_",
                    "CHUNK_",
                    "DATABASE_",
                    "LLM_",
                    "WHISPER_",
                    "BLACK_",
                    "SILENCE_",
                    "MAX_",
                    "JOB_",
                    "OUTPUT_",
                    "TEST_",
                    "E2E_",
                    "DEBUG",
                    "LOG_LEVEL",
                )
            ):
                del os.environ[key]

        settings = Settings()

        # Application defaults
        assert settings.APP_NAME == "Hollywood Script Generator"
        assert settings.APP_ENV == "development"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "INFO"

        # Server defaults
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 8000

        # Video defaults
        assert settings.VIDEO_DIR == Path("/path/to/your/videos")
        assert settings.CHUNK_DURATION_SECONDS == 30
        assert settings.CHUNK_OVERLAP_SECONDS == 5

        # Database defaults
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///./data/hollywood.db"

        # LLM defaults
        assert settings.LLM_BASE_URL == "http://localhost:11434/v1"
        assert settings.LLM_MODEL == "llama3.1:70b"
        assert settings.LLM_TEMPERATURE == 0.7
        assert settings.LLM_MAX_TOKENS == 4096

        # Whisper defaults
        assert settings.WHISPER_MODEL == "base"
        assert settings.WHISPER_DEVICE == "cpu"

        # Video processing defaults
        assert settings.BLACK_FRAME_THRESHOLD == 20
        assert settings.BLACK_FRAME_MIN_DURATION == 2.0
        assert settings.SILENCE_THRESHOLD == -40
        assert settings.SILENCE_MIN_DURATION == 3.0

        # Job processing defaults
        assert settings.MAX_CONCURRENT_JOBS == 2
        assert settings.JOB_TIMEOUT == 3600

        # Output defaults
        assert settings.OUTPUT_DIR == Path("./output")

        # Testing defaults
        assert settings.TEST_DATABASE_URL == "sqlite+aiosqlite:///./data/test.db"
        assert settings.E2E_BASE_URL == "http://127.0.0.1:8000"

    def test_settings_from_environment(self, monkeypatch):
        """Test that Settings reads from environment variables."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("APP_ENV", "testing")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("HOST", "0.0.0.0")
        monkeypatch.setenv("PORT", "9000")
        monkeypatch.setenv("VIDEO_DIR", "/test/videos")
        monkeypatch.setenv("CHUNK_DURATION_SECONDS", "60")
        monkeypatch.setenv("CHUNK_OVERLAP_SECONDS", "10")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("LLM_BASE_URL", "http://test:11434/v1")
        monkeypatch.setenv("LLM_MODEL", "test-model")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
        monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
        monkeypatch.setenv("WHISPER_MODEL", "small")
        monkeypatch.setenv("WHISPER_DEVICE", "cuda")
        monkeypatch.setenv("BLACK_FRAME_THRESHOLD", "30")
        monkeypatch.setenv("BLACK_FRAME_MIN_DURATION", "3.0")
        monkeypatch.setenv("SILENCE_THRESHOLD", "-50")
        monkeypatch.setenv("SILENCE_MIN_DURATION", "5.0")
        monkeypatch.setenv("MAX_CONCURRENT_JOBS", "4")
        monkeypatch.setenv("JOB_TIMEOUT", "7200")
        monkeypatch.setenv("OUTPUT_DIR", "/test/output")
        monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///test_test.db")
        monkeypatch.setenv("E2E_BASE_URL", "http://test:9000")

        settings = Settings()

        assert settings.APP_NAME == "Test App"
        assert settings.APP_ENV == "testing"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 9000
        assert settings.VIDEO_DIR == Path("/test/videos")
        assert settings.CHUNK_DURATION_SECONDS == 60
        assert settings.CHUNK_OVERLAP_SECONDS == 10
        assert settings.DATABASE_URL == "sqlite:///test.db"
        assert settings.LLM_BASE_URL == "http://test:11434/v1"
        assert settings.LLM_MODEL == "test-model"
        assert settings.LLM_TEMPERATURE == 0.5
        assert settings.LLM_MAX_TOKENS == 2048
        assert settings.WHISPER_MODEL == "small"
        assert settings.WHISPER_DEVICE == "cuda"
        assert settings.BLACK_FRAME_THRESHOLD == 30
        assert settings.BLACK_FRAME_MIN_DURATION == 3.0
        assert settings.SILENCE_THRESHOLD == -50
        assert settings.SILENCE_MIN_DURATION == 5.0
        assert settings.MAX_CONCURRENT_JOBS == 4
        assert settings.JOB_TIMEOUT == 7200
        assert settings.OUTPUT_DIR == Path("/test/output")
        assert settings.TEST_DATABASE_URL == "sqlite:///test_test.db"
        assert settings.E2E_BASE_URL == "http://test:9000"

    def test_settings_path_types(self):
        """Test that path settings are converted to Path objects."""
        settings = Settings()

        assert isinstance(settings.VIDEO_DIR, Path)
        assert isinstance(settings.OUTPUT_DIR, Path)

    def test_settings_integer_validation(self, monkeypatch):
        """Test that integer fields validate correctly."""
        monkeypatch.setenv("PORT", "invalid")

        with pytest.raises(ValidationError):
            Settings()

    def test_settings_float_validation(self, monkeypatch):
        """Test that float fields validate correctly."""
        monkeypatch.setenv("LLM_TEMPERATURE", "invalid")

        with pytest.raises(ValidationError):
            Settings()

    def test_settings_boolean_validation(self, monkeypatch):
        """Test that boolean fields parse correctly from env vars."""
        # Test various boolean representations
        for val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            monkeypatch.setenv("DEBUG", val)
            settings = Settings()
            assert settings.DEBUG is True, f"Failed for value: {val}"

        for val in ["false", "False", "FALSE", "0", "no", "No"]:
            monkeypatch.setenv("DEBUG", val)
            settings = Settings()
            assert settings.DEBUG is False, f"Failed for value: {val}"

    def test_chunk_overlap_less_than_duration(self, monkeypatch):
        """Test validation that overlap < duration."""
        monkeypatch.setenv("CHUNK_DURATION_SECONDS", "10")
        monkeypatch.setenv("CHUNK_OVERLAP_SECONDS", "15")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "overlap" in str(exc_info.value).lower()

    def test_all_env_vars_from_example(self):
        """Test that all env vars from .env.example are defined in Settings."""
        settings = Settings()

        # List of all env vars from .env.example
        expected_vars = [
            "APP_NAME",
            "APP_ENV",
            "DEBUG",
            "LOG_LEVEL",
            "HOST",
            "PORT",
            "VIDEO_DIR",
            "CHUNK_DURATION_SECONDS",
            "CHUNK_OVERLAP_SECONDS",
            "DATABASE_URL",
            "LLM_BASE_URL",
            "LLM_MODEL",
            "LLM_TEMPERATURE",
            "LLM_MAX_TOKENS",
            "WHISPER_MODEL",
            "WHISPER_DEVICE",
            "BLACK_FRAME_THRESHOLD",
            "BLACK_FRAME_MIN_DURATION",
            "SILENCE_THRESHOLD",
            "SILENCE_MIN_DURATION",
            "MAX_CONCURRENT_JOBS",
            "JOB_TIMEOUT",
            "OUTPUT_DIR",
            "TEST_DATABASE_URL",
            "E2E_BASE_URL",
        ]

        for var in expected_vars:
            assert hasattr(settings, var), f"Settings missing attribute: {var}"
