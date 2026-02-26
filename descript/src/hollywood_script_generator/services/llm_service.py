"""LLM service for script generation.

This module provides the LLMService class for generating Hollywood-style scripts
from video transcripts using OpenAI-compatible APIs (Ollama).
"""

import time
from typing import Any, Dict, List, Optional

import httpx
from openai import APIError, OpenAI, RateLimitError

from hollywood_script_generator.core.config import Settings


class ScriptGenerationPrompt:
    """Prompt template for Hollywood script generation.

    This class provides structured prompts that guide the LLM to generate
    properly formatted Hollywood-style scripts from video transcripts.
    """

    system_prompt: str = """You are a professional screenplay writer specializing in converting video transcripts into Hollywood-standard script format.

Your task is to transform transcribed video content into a properly formatted screenplay that includes:

1. SCENE HEADINGS (Sluglines): INT./EXT. LOCATION - TIME OF DAY
2. ACTION DESCRIPTIONS: Visual details, camera movements, character actions
3. CHARACTER NAMES: In ALL CAPS when introducing or speaking
4. DIALOGUE: Properly formatted with character names and spoken lines
5. PARENTHETICALS: Brief directions within dialogue (e.g., (sarcastic), (whispering))

RULES:
- Identify and describe sets/locations based on audio context and dialogue
- Infer camera movements and shots from the flow of conversation and action
- Create character descriptions based on dialogue patterns and context
- Format all dialogue in standard screenplay format
- Use proper spacing and formatting consistent with industry standards
- Do not include scene numbers unless explicitly provided
- Focus on creating a readable, professional script

The output should be a complete, production-ready screenplay in standard format."""

    user_prompt_template: str = """Please convert the following video transcript into a Hollywood-standard screenplay:

VIDEO CONTEXT:
{context}

TRANSCRIPT:
{transcript}

Please provide the script in standard screenplay format with scene headings, action descriptions, character names, and dialogue."""

    def render(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Render the prompt template into OpenAI message format.

        Args:
            transcript: The transcribed video content.
            context: Optional dictionary with video metadata (title, duration, etc.).

        Returns:
            List of message dictionaries in OpenAI format.
        """
        context_str = ""
        if context:
            context_parts = []
            if "title" in context:
                context_parts.append(f"Title: {context['title']}")
            if "duration" in context:
                context_parts.append(f"Duration: {context['duration']} seconds")
            if "description" in context:
                context_parts.append(f"Description: {context['description']}")
            context_str = (
                "\n".join(context_parts)
                if context_parts
                else "No additional context provided."
            )
        else:
            context_str = "No additional context provided."

        user_message = self.user_prompt_template.format(
            transcript=transcript, context=context_str
        )

        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]


class LLMService:
    """Service for interacting with LLM APIs for script generation.

    This service provides a client for OpenAI-compatible APIs (like Ollama)
    to generate Hollywood-style scripts from video transcripts.

    Attributes:
        settings: Application settings containing LLM configuration.
        client: OpenAI client instance (lazy-loaded).
        prompt_template: Template for generating prompts.
    """

    def __init__(self, settings: Settings):
        """Initialize the LLM service.

        Args:
            settings: Application settings with LLM configuration.
        """
        self.settings = settings
        self._client: Optional[OpenAI] = None
        self.prompt_template = ScriptGenerationPrompt()

    @property
    def client(self) -> OpenAI:
        """Get or create the OpenAI client.

        Returns:
            OpenAI client instance configured for Ollama/local LLM.
        """
        if self._client is None:
            self._client = OpenAI(
                base_url=self.settings.LLM_BASE_URL,
                api_key="ollama",  # Ollama doesn't require a real API key
                timeout=httpx.Timeout(300.0, connect=10.0),
            )
        return self._client

    def generate_script(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a Hollywood-style script from a transcript.

        This method sends the transcript to the LLM with a structured prompt
        and returns the generated script in screenplay format.

        Args:
            transcript: The transcribed video content to convert to script.
            context: Optional video metadata (title, duration, etc.).
            temperature: Override the default temperature (0.0-2.0).
            max_tokens: Override the default max tokens.

        Returns:
            The generated script in Hollywood screenplay format.

        Raises:
            Exception: If script generation fails after retries.
        """
        messages = self.prompt_template.render(transcript=transcript, context=context)

        temp = temperature if temperature is not None else self.settings.LLM_TEMPERATURE
        tokens = max_tokens if max_tokens is not None else self.settings.LLM_MAX_TOKENS

        # Retry logic for transient failures
        max_retries = 3
        retry_delay = 1.0
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.LLM_MODEL,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                )

                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    return content if content is not None else ""
                else:
                    return ""

            except (RateLimitError, httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                continue
            except APIError as e:
                # Don't retry on other API errors
                raise Exception(f"Script generation failed: {e}") from e

        # If we get here, all retries failed
        raise Exception(
            f"Script generation failed after {max_retries} attempts: {last_error}"
        )

    def health_check(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if the LLM API is reachable, False otherwise.
        """
        try:
            # Try a simple request to check connectivity
            self.client.models.list()
            return True
        except Exception:
            return False
