"""Unit tests for the Script Assembler service.

This module tests the ScriptAssembler functionality including:
- Filtering transcribed text from filtered sections
- Combining remaining text into a single transcript
- Building context dict with video metadata
- Calling llm_service.generate_script() with proper parameters
- Handling empty transcripts gracefully
- LLM generation failures and retries
"""

import logging
from unittest.mock import Mock, MagicMock, patch

import pytest
from typing import List

from hollywood_script_generator.services.script_assembler import (
    ScriptAssembler,
)
from hollywood_script_generator.services.audio_transcriber import (
    TranscriptionResult,
    TranscriptionSegment,
)
from hollywood_script_generator.services.credits_filter import (
    FilteredSection,
    DetectionMethod,
)
from hollywood_script_generator.core.config import Settings


class TestScriptAssemblerInitialization:
    """Tests for ScriptAssembler initialization."""

    def test_service_can_be_instantiated(self):
        """Verify service can be created with llm_service and settings."""
        settings = Settings()
        llm_service = Mock()

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        assert assembler is not None
        assert assembler.llm_service == llm_service
        assert assembler.settings == settings

    def test_service_has_logger(self):
        """Verify service has a logger instance."""
        settings = Settings()
        llm_service = Mock()

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        assert hasattr(assembler, "logger")
        assert isinstance(assembler.logger, logging.Logger)


class TestScriptAssemblerBasicAssembly:
    """Tests for basic script assembly without filtered sections."""

    def test_assemble_script_no_filtered_sections(self):
        """Verify assembly works with no filtered sections."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "# Generated Script\n\nTest content"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Hello world this is chunk one",
                segments=[
                    TranscriptionSegment(
                        text="Hello world", start_time=0.0, end_time=2.0
                    ),
                    TranscriptionSegment(
                        text="this is chunk one", start_time=2.0, end_time=4.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=4.0,
            ),
            TranscriptionResult(
                text="This is chunk two content",
                segments=[
                    TranscriptionSegment(
                        text="This is chunk two", start_time=4.0, end_time=6.0
                    ),
                    TranscriptionSegment(text="content", start_time=6.0, end_time=7.0),
                ],
                chunk_start_time=4.0,
                chunk_end_time=7.0,
            ),
        ]

        result = assembler.assemble_script(
            video_id=123,
            transcriptions=transcriptions,
            filtered_sections=[],
        )

        assert result == "# Generated Script\n\nTest content"
        llm_service.generate_script.assert_called_once()

        # Verify the transcript passed to LLM contains all text
        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")
        assert "Hello world this is chunk one" in transcript
        assert "This is chunk two content" in transcript

    def test_assemble_script_builds_context(self):
        """Verify context dict is built with video metadata."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Generated script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Test content",
                segments=[
                    TranscriptionSegment(
                        text="Test content", start_time=0.0, end_time=2.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=2.0,
            ),
        ]

        assembler.assemble_script(
            video_id=456,
            transcriptions=transcriptions,
            filtered_sections=[],
        )

        call_args = llm_service.generate_script.call_args
        context = call_args.kwargs.get("context")

        assert context is not None
        assert context["video_id"] == 456
        assert context["total_chunks"] == 1
        assert context["total_duration"] == 2.0


class TestScriptAssemblerFilteredSections:
    """Tests for assembly with filtered sections (skipping content)."""

    def test_assemble_script_with_filtered_sections(self):
        """Verify content in filtered sections is skipped."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Generated script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Keep this part skip this part keep this too",
                segments=[
                    TranscriptionSegment(
                        text="Keep this part", start_time=0.0, end_time=2.0
                    ),
                    TranscriptionSegment(
                        text="skip this part", start_time=2.0, end_time=4.0
                    ),
                    TranscriptionSegment(
                        text="keep this too", start_time=4.0, end_time=6.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=6.0,
            ),
        ]

        filtered_sections = [
            FilteredSection(
                start_seconds=2.0,
                end_seconds=4.0,
                method=DetectionMethod.BLACK_FRAME,
                confidence=0.95,
            ),
        ]

        assembler.assemble_script(
            video_id=789,
            transcriptions=transcriptions,
            filtered_sections=filtered_sections,
        )

        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")

        # Verify filtered content is excluded
        assert "Keep this part" in transcript
        assert "skip this part" not in transcript
        assert "keep this too" in transcript

    def test_assemble_script_with_multiple_filtered_sections(self):
        """Verify multiple filtered sections are handled correctly."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Generated script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Part one part two part three part four",
                segments=[
                    TranscriptionSegment(text="Part one", start_time=0.0, end_time=1.0),
                    TranscriptionSegment(text="part two", start_time=1.0, end_time=2.0),
                    TranscriptionSegment(
                        text="part three", start_time=2.0, end_time=3.0
                    ),
                    TranscriptionSegment(
                        text="part four", start_time=3.0, end_time=4.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=4.0,
            ),
        ]

        filtered_sections = [
            FilteredSection(
                start_seconds=0.5,
                end_seconds=1.5,
                method=DetectionMethod.BLACK_FRAME,
                confidence=0.9,
            ),
            FilteredSection(
                start_seconds=2.5,
                end_seconds=3.5,
                method=DetectionMethod.SILENCE,
                confidence=0.85,
            ),
        ]

        assembler.assemble_script(
            video_id=999,
            transcriptions=transcriptions,
            filtered_sections=filtered_sections,
        )

        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")

        # Verify only unfiltered content is included
        # Segment "Part one" (0.0-1.0) overlaps with first filtered section (0.5-1.5)
        # Segment "part two" (1.0-2.0) overlaps with first filtered section (0.5-1.5)
        # Segment "part three" (2.0-3.0) overlaps with second filtered section (2.5-3.5)
        # Segment "part four" (3.0-4.0) overlaps with second filtered section (2.5-3.5)
        # Since all segments overlap with some filtered section, transcript should be empty
        assert transcript == ""

    def test_assemble_script_filtered_sections_across_chunks(self):
        """Verify filtered sections work across multiple chunks."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Generated script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Chunk one content",
                segments=[
                    TranscriptionSegment(
                        text="Chunk one", start_time=0.0, end_time=2.0
                    ),
                    TranscriptionSegment(text="content", start_time=2.0, end_time=3.0),
                ],
                chunk_start_time=0.0,
                chunk_end_time=3.0,
            ),
            TranscriptionResult(
                text="Chunk two content here",
                segments=[
                    TranscriptionSegment(
                        text="Chunk two", start_time=3.0, end_time=5.0
                    ),
                    TranscriptionSegment(
                        text="content here", start_time=5.0, end_time=7.0
                    ),
                ],
                chunk_start_time=3.0,
                chunk_end_time=7.0,
            ),
        ]

        filtered_sections = [
            FilteredSection(
                start_seconds=2.5,
                end_seconds=4.5,
                method=DetectionMethod.SILENCE,
                confidence=0.9,
            ),
        ]

        assembler.assemble_script(
            video_id=111,
            transcriptions=transcriptions,
            filtered_sections=filtered_sections,
        )

        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")

        # Verify correct segments are included/excluded after filtering
        # "Chunk one" (0.0-2.0) and "content here" (5.0-7.0) should be in transcript
        # "content" (2.0-3.0) and "Chunk two" (3.0-5.0) filtered due to overlap with 2.5-4.5
        assert "Chunk one" in transcript
        assert "Chunk two" not in transcript
        assert "content here" in transcript

class TestScriptAssemblerEmptyTranscript:
    """Tests for handling empty transcripts gracefully."""

    def test_assemble_script_empty_transcriptions(self):
        """Verify empty transcriptions list is handled gracefully."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "# Empty Script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        result = assembler.assemble_script(
            video_id=222,
            transcriptions=[],
            filtered_sections=[],
        )

        assert result == "# Empty Script"
        llm_service.generate_script.assert_called_once()

        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")
        assert transcript == ""

    def test_assemble_script_all_segments_filtered(self):
        """Verify when all content is filtered out."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "# All Filtered"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="All this content",
                segments=[
                    TranscriptionSegment(text="All this", start_time=0.0, end_time=2.0),
                    TranscriptionSegment(text="content", start_time=2.0, end_time=4.0),
                ],
                chunk_start_time=0.0,
                chunk_end_time=4.0,
            ),
        ]

        filtered_sections = [
            FilteredSection(
                start_seconds=0.0,
                end_seconds=10.0,
                method=DetectionMethod.BLACK_FRAME,
                confidence=1.0,
            ),
        ]

        result = assembler.assemble_script(
            video_id=333,
            transcriptions=transcriptions,
            filtered_sections=filtered_sections,
        )

        assert result == "# All Filtered"
        call_args = llm_service.generate_script.call_args
        transcript = call_args.kwargs.get("transcript", "")
        assert transcript == ""


class TestScriptAssemblerMultipleChunks:
    """Tests for combining multiple chunks."""

    def test_assemble_script_multiple_chunks_combined(self):
        """Verify multiple chunks are combined in order."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Combined script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="First chunk here",
                segments=[
                    TranscriptionSegment(
                        text="First chunk", start_time=0.0, end_time=2.0
                    ),
                    TranscriptionSegment(text="here", start_time=2.0, end_time=3.0),
                ],
                chunk_start_time=0.0,
                chunk_end_time=3.0,
            ),
            TranscriptionResult(
                text="Second chunk there",
                segments=[
                    TranscriptionSegment(
                        text="Second chunk", start_time=3.0, end_time=5.0
                    ),
                    TranscriptionSegment(text="there", start_time=5.0, end_time=6.0),
                ],
                chunk_start_time=3.0,
                chunk_end_time=6.0,
            ),
            TranscriptionResult(
                text="Third chunk everywhere",
                segments=[
                    TranscriptionSegment(
                        text="Third chunk", start_time=6.0, end_time=8.0
                    ),
                    TranscriptionSegment(
                        text="everywhere", start_time=8.0, end_time=10.0
                    ),
                ],
                chunk_start_time=6.0,
                chunk_end_time=10.0,
            ),
        ]

        assembler.assemble_script(
            video_id=444,
            transcriptions=transcriptions,
            filtered_sections=[],
        )

        call_args = llm_service.generate_script.call_args
        context = call_args.kwargs.get("context")

        assert context["total_chunks"] == 3
        assert context["total_duration"] == 10.0


class TestScriptAssemblerLLMFailures:
    """Tests for LLM generation failures."""

    def test_assemble_script_llm_raises_after_retries(self):
        """Verify LLM failures are propagated after retries."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.side_effect = Exception("LLM failed after retries")

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Test content",
                segments=[
                    TranscriptionSegment(
                        text="Test content", start_time=0.0, end_time=2.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=2.0,
            ),
        ]

        with pytest.raises(Exception) as exc_info:
            assembler.assemble_script(
                video_id=555,
                transcriptions=transcriptions,
                filtered_sections=[],
            )

        assert (
            "llm failed" in str(exc_info.value).lower()
            or "script generation" in str(exc_info.value).lower()
        )

    def test_assemble_script_preserves_exception_details(self):
        """Verify original exception details are preserved."""
        settings = Settings()
        llm_service = Mock()
        original_error = Exception("Connection timeout to LLM service")
        llm_service.generate_script.side_effect = original_error

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Test",
                segments=[
                    TranscriptionSegment(text="Test", start_time=0.0, end_time=1.0)
                ],
                chunk_start_time=0.0,
                chunk_end_time=1.0,
            ),
        ]

        with pytest.raises(Exception) as exc_info:
            assembler.assemble_script(
                video_id=666,
                transcriptions=transcriptions,
                filtered_sections=[],
            )

        assert (
            "connection" in str(exc_info.value).lower()
            or "timeout" in str(exc_info.value).lower()
        )


class TestScriptAssemblerContextContents:
    """Tests for context dictionary contents."""

    def test_context_includes_all_required_fields(self):
        """Verify context includes video_id, total_chunks, total_duration, etc."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Content A",
                segments=[
                    TranscriptionSegment(
                        text="Content A", start_time=0.0, end_time=5.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=5.0,
            ),
            TranscriptionResult(
                text="Content B",
                segments=[
                    TranscriptionSegment(
                        text="Content B", start_time=5.0, end_time=12.0
                    ),
                ],
                chunk_start_time=5.0,
                chunk_end_time=12.0,
            ),
        ]

        assembler.assemble_script(
            video_id=777,
            transcriptions=transcriptions,
            filtered_sections=[],
        )

        call_args = llm_service.generate_script.call_args
        context = call_args.kwargs.get("context")

        assert "video_id" in context
        assert "total_chunks" in context
        assert "total_duration" in context
        assert context["video_id"] == 777
        assert context["total_chunks"] == 2
        assert context["total_duration"] == 12.0

    def test_context_with_filtered_sections(self):
        """Verify context includes filtered_sections_count when applicable."""
        settings = Settings()
        llm_service = Mock()
        llm_service.generate_script.return_value = "Script"

        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        transcriptions = [
            TranscriptionResult(
                text="Some content",
                segments=[
                    TranscriptionSegment(
                        text="Some content", start_time=0.0, end_time=10.0
                    ),
                ],
                chunk_start_time=0.0,
                chunk_end_time=10.0,
            ),
        ]

        filtered_sections = [
            FilteredSection(
                start_seconds=2.0,
                end_seconds=4.0,
                method=DetectionMethod.SILENCE,
                confidence=0.9,
            ),
            FilteredSection(
                start_seconds=6.0,
                end_seconds=8.0,
                method=DetectionMethod.BLACK_FRAME,
                confidence=0.95,
            ),
        ]

        assembler.assemble_script(
            video_id=888,
            transcriptions=transcriptions,
            filtered_sections=filtered_sections,
        )

        call_args = llm_service.generate_script.call_args
        context = call_args.kwargs.get("context")

        assert "filtered_sections_count" in context
        assert context["filtered_sections_count"] == 2


class TestScriptAssemblerTypeAnnotations:
    """Tests for type annotations and signatures."""

    def test_assemble_script_has_type_hints(self):
        """Verify assemble_script method has proper type annotations."""
        import inspect

        settings = Settings()
        llm_service = Mock()
        assembler = ScriptAssembler(llm_service=llm_service, settings=settings)

        sig = inspect.signature(assembler.assemble_script)
        params = sig.parameters

        # Check required parameters
        assert "video_id" in params
        assert "transcriptions" in params
        assert "filtered_sections" in params

        # Check return type
        assert sig.return_annotation == str
