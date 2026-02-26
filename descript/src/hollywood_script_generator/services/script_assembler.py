"""Script assembler service for combining transcriptions and generating scripts.

This module provides the ScriptAssembler class for:
- Filtering transcribed text from filtered sections (skip sections)
- Combining remaining text into a single transcript
- Building context dict with video metadata
- Calling llm_service.generate_script() with transcript and context
- Returning generated Markdown script

Example:
    >>> from hollywood_script_generator.core.config import Settings
    >>> from hollywood_script_generator.services.llm_service import LLMService
    >>> settings = Settings()
    >>> llm_service = LLMService(settings=settings)
    >>> assembler = ScriptAssembler(llm_service=llm_service, settings=settings)
    >>> script = assembler.assemble_script(
    ...     video_id=123,
    ...     transcriptions=transcriptions,
    ...     filtered_sections=filtered_sections,
    ... )
"""

import logging
from typing import Any, Dict, List

from hollywood_script_generator.core.config import Settings
from hollywood_script_generator.services.audio_transcriber import (
    TranscriptionResult,
    TranscriptionSegment,
)
from hollywood_script_generator.services.credits_filter import FilteredSection

logger = logging.getLogger(__name__)


class ScriptAssembler:
    """Service for assembling transcriptions and generating scripts.

    This service combines transcription results, filters out content from
    specified sections, and generates a Hollywood-style script using an LLM.

    Attributes:
        llm_service: The LLM service for script generation.
        settings: Application settings containing configuration.
        logger: Logger instance for this service.

    Example:
        >>> settings = Settings()
        >>> llm_service = LLMService(settings=settings)
        >>> assembler = ScriptAssembler(llm_service=llm_service, settings=settings)
        >>> script = assembler.assemble_script(
        ...     video_id=123,
        ...     transcriptions=transcriptions,
        ...     filtered_sections=filtered_sections,
        ... )
    """

    def __init__(self, llm_service: Any, settings: Settings):
        """Initialize the ScriptAssembler.

        Args:
            llm_service: The LLM service instance for script generation.
            settings: Application settings with configuration.
        """
        self.llm_service = llm_service
        self.settings = settings
        self.logger = logger

        self.logger.info("ScriptAssembler initialized")

    def assemble_script(
        self,
        video_id: int,
        transcriptions: List[TranscriptionResult],
        filtered_sections: List[FilteredSection],
    ) -> str:
        """Assemble transcriptions into a script, filtering specified sections.

        This method:
        1. Filters out transcribed text from filtered sections (skip sections)
        2. Combines remaining text into a single transcript
        3. Builds context dict with video_id, chunk info, etc.
        4. Calls llm_service.generate_script() with transcript and context
        5. Returns the generated Markdown script

        Args:
            video_id: The ID of the video being processed.
            transcriptions: List of TranscriptionResult objects from audio transcription.
            filtered_sections: List of FilteredSection objects to skip/filter out.

        Returns:
            The generated script in Markdown format.

        Raises:
            Exception: If script generation fails after retries.
        """
        self.logger.info(
            f"Assembling script for video {video_id} with "
            f"{len(transcriptions)} transcription chunks and "
            f"{len(filtered_sections)} filtered sections"
        )

        # Step 1 & 2: Filter segments and combine remaining text
        filtered_transcript = self._build_filtered_transcript(
            transcriptions, filtered_sections
        )

        self.logger.debug(
            f"Filtered transcript length: {len(filtered_transcript)} characters"
        )

        # Step 3: Build context dict
        context = self._build_context(video_id, transcriptions, filtered_sections)

        # Step 4 & 5: Generate script via LLM service
        try:
            script = self.llm_service.generate_script(
                transcript=filtered_transcript,
                context=context,
            )
            self.logger.info(
                f"Script generation complete for video {video_id}: "
                f"{len(script)} characters"
            )
            return script
        except Exception as e:
            self.logger.error(f"Script generation failed for video {video_id}: {e}")
            raise Exception(f"Script generation failed: {e}") from e

    def _build_filtered_transcript(
        self,
        transcriptions: List[TranscriptionResult],
        filtered_sections: List[FilteredSection],
    ) -> str:
        """Build filtered transcript by excluding segments in filtered sections.

        Args:
            transcriptions: List of transcription results.
            filtered_sections: List of sections to filter out.

        Returns:
            Combined transcript string with filtered sections removed.
        """
        if not transcriptions:
            return ""

        kept_segments: List[str] = []

        for transcription in transcriptions:
            for segment in transcription.segments:
                # Check if this segment overlaps with any filtered section
                if not self._segment_in_filtered_section(segment, filtered_sections):
                    kept_segments.append(segment.text)
                else:
                    self.logger.debug(
                        f"Filtering out segment: '{segment.text[:50]}...' "
                        f"({segment.start_time}s - {segment.end_time}s)"
                    )

        return " ".join(kept_segments)

    def _segment_in_filtered_section(
        self,
        segment: TranscriptionSegment,
        filtered_sections: List[FilteredSection],
    ) -> bool:
        """Check if a segment overlaps with any filtered section.

        Args:
            segment: The transcription segment to check.
            filtered_sections: List of sections to check against.

        Returns:
            True if the segment overlaps with any filtered section.
        """
        for section in filtered_sections:
            # Check for overlap: segment overlaps if it starts before section ends
            # and ends after section starts
            if (
                segment.start_time < section.end_seconds
                and segment.end_time > section.start_seconds
            ):
                return True
        return False

    def _build_context(
        self,
        video_id: int,
        transcriptions: List[TranscriptionResult],
        filtered_sections: List[FilteredSection],
    ) -> Dict[str, Any]:
        """Build context dictionary for script generation.

        Args:
            video_id: The ID of the video.
            transcriptions: List of transcription results.
            filtered_sections: List of filtered sections.

        Returns:
            Context dictionary with video metadata.
        """
        total_duration = 0.0
        if transcriptions:
            # Get the end time of the last chunk
            last_chunk = max(transcriptions, key=lambda t: t.chunk_end_time)
            total_duration = last_chunk.chunk_end_time

        context: Dict[str, Any] = {
            "video_id": video_id,
            "total_chunks": len(transcriptions),
            "total_duration": total_duration,
        }

        if filtered_sections:
            context["filtered_sections_count"] = len(filtered_sections)

        return context
