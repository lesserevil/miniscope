"""Unit tests for the LLM service.

This module tests the LLM service functionality including:
- Client initialization with OpenAI SDK
- Prompt template rendering
- Script generation with proper error handling
- Retry logic for transient failures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Generator

from hollywood_script_generator.services.llm_service import (
    LLMService,
    ScriptGenerationPrompt,
)
from hollywood_script_generator.core.config import Settings


class TestScriptGenerationPrompt:
    """Tests for the ScriptGenerationPrompt template."""

    def test_prompt_template_exists(self):
        """Verify the prompt template class exists and has required attributes."""
        prompt = ScriptGenerationPrompt()
        assert hasattr(prompt, "system_prompt")
        assert hasattr(prompt, "user_prompt_template")
        assert isinstance(prompt.system_prompt, str)
        assert isinstance(prompt.user_prompt_template, str)

    def test_system_prompt_contains_required_elements(self):
        """Verify system prompt enforces Hollywood script format."""
        prompt = ScriptGenerationPrompt()
        system = prompt.system_prompt.lower()

        # Check for key elements in the system prompt
        assert "script" in system or "screenplay" in system
        assert "set" in system or "location" in system
        assert "character" in system
        assert "dialog" in system or "dialogue" in system

    def test_user_prompt_template_has_placeholders(self):
        """Verify user prompt template has required placeholders."""
        prompt = ScriptGenerationPrompt()
        template = prompt.user_prompt_template

        # Check for required placeholders
        assert "{transcript}" in template or "{context}" in template

    def test_render_prompt_with_context(self):
        """Verify prompt rendering with transcript context."""
        prompt = ScriptGenerationPrompt()
        transcript = "Character A: Hello there. Character B: Hi!"
        context = {"title": "Test Video", "duration": 120}

        result = prompt.render(transcript=transcript, context=context)

        assert isinstance(result, list)
        assert len(result) >= 2  # At least system and user messages
        assert any(msg["role"] == "system" for msg in result)
        assert any(msg["role"] == "user" for msg in result)


class TestLLMServiceInitialization:
    """Tests for LLM service initialization."""

    def test_service_can_be_instantiated(self):
        """Verify service can be created with Settings."""
        settings = Settings(
            LLM_BASE_URL="http://localhost:11434/v1",
            LLM_MODEL="llama3.1:70b",
            LLM_TEMPERATURE=0.7,
            LLM_MAX_TOKENS=4096,
        )
        service = LLMService(settings=settings)

        assert service is not None
        assert service.settings == settings

    def test_service_uses_settings_values(self):
        """Verify service uses configuration from Settings."""
        settings = Settings(
            LLM_BASE_URL="http://custom:11434/v1",
            LLM_MODEL="custom-model",
            LLM_TEMPERATURE=0.5,
            LLM_MAX_TOKENS=2048,
        )
        service = LLMService(settings=settings)

        assert service.settings.LLM_BASE_URL == "http://custom:11434/v1"
        assert service.settings.LLM_MODEL == "custom-model"
        assert service.settings.LLM_TEMPERATURE == 0.5
        assert service.settings.LLM_MAX_TOKENS == 2048

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_client_initialization_with_ollama_url(self, mock_openai):
        """Verify OpenAI client is initialized with Ollama URL."""
        settings = Settings(
            LLM_BASE_URL="http://localhost:11434/v1",
            LLM_MODEL="llama3.1:70b",
        )

        service = LLMService(settings=settings)
        _ = service.client  # Access client property

        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs
        assert call_kwargs["base_url"] == "http://localhost:11434/v1"


class TestLLMServiceGenerateScript:
    """Tests for script generation functionality."""

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_generate_script_success(self, mock_openai_class):
        """Verify successful script generation."""
        # Setup mock
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "FADE IN:\n\nINT. COFFEE SHOP - DAY\n\nCharacter A sits at a table.\n\nCHARACTER A\nHello there.\n\nFADE OUT."
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Character A: Hello there. Character B: Hi!"
        result = service.generate_script(transcript)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify the API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == settings.LLM_MODEL
        assert call_kwargs["temperature"] == settings.LLM_TEMPERATURE
        assert call_kwargs["max_tokens"] == settings.LLM_MAX_TOKENS

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_generate_script_with_custom_params(self, mock_openai_class):
        """Verify script generation with custom temperature and max_tokens."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Test script content"
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"
        result = service.generate_script(
            transcript=transcript, temperature=0.9, max_tokens=2048
        )

        # Verify custom params were used
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 2048

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_generate_script_api_error(self, mock_openai_class):
        """Verify error handling when API call fails."""
        from openai import APIError

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            message="API Error", request=MagicMock(), body={}
        )
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"

        with pytest.raises(Exception) as exc_info:
            service.generate_script(transcript)

        assert (
            "script generation failed" in str(exc_info.value).lower()
            or "api" in str(exc_info.value).lower()
        )

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_generate_script_empty_response(self, mock_openai_class):
        """Verify handling of empty response from LLM."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"
        result = service.generate_script(transcript)

        assert result == ""


class TestLLMServiceRetryLogic:
    """Tests for retry logic on transient failures."""

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    @patch("time.sleep")  # Don't actually sleep in tests
    def test_retry_on_rate_limit(self, mock_sleep, mock_openai_class):
        """Verify retry logic on rate limit errors."""
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429

        # First two calls fail with rate limit, third succeeds
        mock_choice = MagicMock()
        mock_choice.message.content = "Success after retry"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client.chat.completions.create.side_effect = [
            RateLimitError(message="Rate limited", response=mock_response, body={}),
            RateLimitError(message="Rate limited", response=mock_response, body={}),
            mock_completion,
        ]
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"
        result = service.generate_script(transcript)

        assert result == "Success after retry"
        assert mock_client.chat.completions.create.call_count == 3

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    @patch("time.sleep")
    def test_retry_exhaustion(self, mock_sleep, mock_openai_class):
        """Verify failure after max retries exceeded."""
        from openai import RateLimitError

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limited", response=mock_response, body={}
        )
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"

        with pytest.raises(Exception) as exc_info:
            service.generate_script(transcript)

        assert (
            mock_client.chat.completions.create.call_count >= 2
        )  # At least initial + retry

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    @patch("time.sleep")
    def test_retry_on_connection_error(self, mock_sleep, mock_openai_class):
        """Verify retry logic on connection errors."""
        import httpx

        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Success after connection retry"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client.chat.completions.create.side_effect = [
            httpx.ConnectError("Connection refused"),
            mock_completion,
        ]
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript"
        result = service.generate_script(transcript)

        assert result == "Success after connection retry"
        assert mock_client.chat.completions.create.call_count == 2


class TestLLMServiceMessages:
    """Tests for message formatting."""

    @patch("hollywood_script_generator.services.llm_service.OpenAI")
    def test_messages_format(self, mock_openai_class):
        """Verify messages are formatted correctly for OpenAI API."""
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Script content"
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        settings = Settings()
        service = LLMService(settings=settings)

        transcript = "Test transcript with context"
        service.generate_script(transcript)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # Verify message structure
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert all("role" in msg and "content" in msg for msg in messages)
        assert any(msg["role"] == "system" for msg in messages)
        assert any(msg["role"] == "user" for msg in messages)


class TestLLMServiceTypeAnnotations:
    """Tests for type annotations and signatures."""

    def test_generate_script_has_type_hints(self):
        """Verify generate_script method has proper type annotations."""
        import inspect

        settings = Settings()
        service = LLMService(settings=settings)

        sig = inspect.signature(service.generate_script)
        params = sig.parameters

        # Check transcript parameter
        assert "transcript" in params
        assert params["transcript"].annotation == str

        # Check optional parameters
        assert "temperature" in params
        assert "max_tokens" in params

        # Check return type
        assert sig.return_annotation == str
