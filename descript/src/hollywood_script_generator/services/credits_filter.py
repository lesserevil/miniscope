"""Credits filter service for detecting and filtering video sections.

This module provides the CreditsFilter class for:
- Black frame detection using OpenCV
- Silence detection using audio amplitude analysis
- Configurable detection thresholds
- Combining heuristic detections with manual skip sections

Example:
    >>> from pathlib import Path
    >>> filter_service = CreditsFilter()
    >>> sections = filter_service.filter_video(
    ...     Path("/path/to/video.mp4"),
    ...     start_time=0.0,
    ...     end_time=120.0,
    ...     manual_skips=[]
    ... )
    >>> for section in sections:
    ...     print(f"Skip {section.start_seconds}s - {section.end_seconds}s: {section.method}")
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
import numpy as np
from moviepy import VideoFileClip

logger = logging.getLogger(__name__)


class DetectionMethod(Enum):
    """Enumeration of detection methods for filtered sections."""

    BLACK_FRAME = "black_frame"
    SILENCE = "silence"
    MANUAL = "manual"


@dataclass
class FilteredSection:
    """Represents a filtered/skip section of video.

    Attributes:
        start_seconds: Start time in seconds (inclusive).
        end_seconds: End time in seconds (inclusive).
        method: Detection method used to identify this section.
        confidence: Confidence score (0.0-1.0) for the detection.
        notes: Optional notes or description about the section.
    """

    start_seconds: float
    end_seconds: float
    method: DetectionMethod
    confidence: float = 1.0
    notes: str | None = None


class CreditsFilter:
    """Service for detecting and filtering credits/ads in videos.

    This service provides heuristics-based detection of:
    - Black frames (common in credits/ad transitions)
    - Silent sections (common in credits/ad breaks)

    It can also combine these detections with manually-specified skip sections.

    Attributes:
        black_frame_threshold: Brightness threshold for black frame detection (0-255).
            Default is 20 - frames with average brightness below this are considered black.
        silence_threshold_db: Audio level threshold for silence detection in dB.
            Default is -40 dB - sections quieter than this are considered silent.
        min_section_duration: Minimum duration in seconds for a section to be included.
            Default is 1.0 second - shorter detections are filtered out.

    Example:
        >>> filter_service = CreditsFilter(
        ...     black_frame_threshold=20,
        ...     silence_threshold_db=-40,
        ...     min_section_duration=1.0
        ... )
        >>> sections = filter_service.filter_video(
        ...     Path("/path/to/video.mp4"),
        ...     start_time=0.0,
        ...     end_time=120.0
        ... )
    """

    def __init__(
        self,
        black_frame_threshold: int = 20,
        silence_threshold_db: float = -40.0,
        min_section_duration: float = 1.0,
    ):
        """Initialize the CreditsFilter with configurable thresholds.

        Args:
            black_frame_threshold: Brightness threshold for black frame detection (0-255).
            silence_threshold_db: Audio level threshold in dB for silence detection.
            min_section_duration: Minimum section duration in seconds.

        Raises:
            ValueError: If threshold values are invalid.
        """
        if not 1 <= black_frame_threshold <= 255:
            raise ValueError("black_frame_threshold must be between 1 and 255")
        if silence_threshold_db > 0:
            raise ValueError("silence_threshold_db must be negative or zero")
        if min_section_duration <= 0:
            raise ValueError("min_section_duration must be positive")

        self.black_frame_threshold = black_frame_threshold
        self.silence_threshold_db = silence_threshold_db
        self.min_section_duration = min_section_duration
        logger.debug(
            f"CreditsFilter initialized: threshold={black_frame_threshold}, "
            f"silence_db={silence_threshold_db}, min_duration={min_section_duration}"
        )

    def _calculate_frame_brightness(self, frame: np.ndarray) -> float:
        """Calculate the average brightness of a frame.

        Args:
            frame: Video frame as numpy array (BGR format).

        Returns:
            Average brightness value (0.0-255.0).
        """
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Calculate average brightness
        return float(np.mean(gray))

    def detect_black_frames(
        self,
        video_path: Path,
        start_time: float = 0.0,
        end_time: float | None = None,
    ) -> list[FilteredSection]:
        """Detect black frame sequences in a video.

        Analyzes frames and identifies sections where consecutive frames
        have brightness below the configured threshold.

        Args:
            video_path: Path to the video file.
            start_time: Start time to analyze from (in seconds).
            end_time: End time to analyze to (in seconds). If None, analyzes to end.

        Returns:
            List of FilteredSection objects representing detected black frame sections.
        """
        sections: list[FilteredSection] = []

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning(f"Could not open video: {video_path}")
            return sections

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Calculate frame positions
            start_frame = int(start_time * fps)
            if end_time is None:
                end_frame = total_frames
            else:
                end_frame = min(int(end_time * fps), total_frames)

            # Seek to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            black_frame_start: int | None = None
            current_frame = start_frame
            black_frame_count = 0
            total_analyzed = 0

            while current_frame < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break

                brightness = self._calculate_frame_brightness(frame)
                is_black = brightness < self.black_frame_threshold

                if is_black:
                    if black_frame_start is None:
                        black_frame_start = current_frame
                    black_frame_count += 1
                else:
                    if black_frame_start is not None:
                        # End of black sequence
                        duration = (current_frame - black_frame_start) / fps
                        if duration >= self.min_section_duration:
                            sections.append(
                                FilteredSection(
                                    start_seconds=black_frame_start / fps,
                                    end_seconds=current_frame / fps,
                                    method=DetectionMethod.BLACK_FRAME,
                                    confidence=min(1.0, black_frame_count / (fps * 2)),
                                    notes=f"Detected {black_frame_count} black frames",
                                )
                            )
                        black_frame_start = None
                        black_frame_count = 0

                current_frame += 1
                total_analyzed += 1

            # Handle case where video ends during black sequence
            if black_frame_start is not None:
                duration = (current_frame - black_frame_start) / fps
                if duration >= self.min_section_duration:
                    sections.append(
                        FilteredSection(
                            start_seconds=black_frame_start / fps,
                            end_seconds=current_frame / fps,
                            method=DetectionMethod.BLACK_FRAME,
                            confidence=min(1.0, black_frame_count / (fps * 2)),
                            notes=f"Detected {black_frame_count} black frames",
                        )
                    )

            logger.info(
                f"Analyzed {total_analyzed} frames, found {len(sections)} black frame sections"
            )

        except Exception as e:
            logger.error(f"Error detecting black frames: {e}")
        finally:
            cap.release()

        return sections

    def _calculate_audio_level(self, audio_chunk: np.ndarray) -> float:
        """Calculate the audio level in dB.

        Converts stereo to mono if needed, then calculates RMS and converts to dB.

        Args:
            audio_chunk: Audio data as numpy array.

        Returns:
            Audio level in dB (typically negative, closer to 0 = louder).
        """
        # Convert to mono if stereo
        if len(audio_chunk.shape) > 1 and audio_chunk.shape[1] > 1:
            audio_chunk = np.mean(audio_chunk, axis=1)

        # Calculate RMS
        rms = np.sqrt(np.mean(audio_chunk**2))

        # Convert to dB (avoid log(0) with small epsilon)
        if rms < 1e-10:
            return -120.0

        db = 20 * np.log10(rms)
        return float(db)

    def detect_silence(
        self,
        video_path: Path,
        start_time: float = 0.0,
        end_time: float | None = None,
    ) -> list[FilteredSection]:
        """Detect silent sections in a video's audio.

        Analyzes audio chunks and identifies sections where the audio level
        is consistently below the configured threshold.

        Args:
            video_path: Path to the video file.
            start_time: Start time to analyze from (in seconds).
            end_time: End time to analyze to (in seconds). If None, analyzes to end.

        Returns:
            List of FilteredSection objects representing detected silent sections.
        """
        sections: list[FilteredSection] = []

        try:
            with VideoFileClip(str(video_path)) as clip:
                if clip.audio is None:
                    logger.warning(f"Video has no audio: {video_path}")
                    return sections

                # Determine time range
                clip_start = start_time
                if end_time is None:
                    clip_end = clip.duration
                else:
                    clip_end = min(end_time, clip.duration)

                # Process audio in chunks
                chunk_duration = 0.5  # 500ms chunks
                current_time = clip_start
                silence_start: float | None = None

                while current_time < clip_end:
                    chunk_end = min(current_time + chunk_duration, clip_end)

                    # Extract audio chunk
                    audio_chunk = clip.audio.subclipped(
                        current_time, chunk_end
                    ).to_soundarray()

                    if len(audio_chunk) > 0:
                        level_db = self._calculate_audio_level(audio_chunk)
                        is_silent = level_db < self.silence_threshold_db

                        if is_silent:
                            if silence_start is None:
                                silence_start = current_time
                        else:
                            if silence_start is not None:
                                # End of silence section
                                duration = current_time - silence_start
                                if duration >= self.min_section_duration:
                                    sections.append(
                                        FilteredSection(
                                            start_seconds=silence_start,
                                            end_seconds=current_time,
                                            method=DetectionMethod.SILENCE,
                                            confidence=min(1.0, duration / 5.0),
                                            notes=f"Silent section ({level_db:.1f} dB)",
                                        )
                                    )
                                silence_start = None

                    current_time = chunk_end

                # Handle case where audio ends during silence
                if silence_start is not None:
                    duration = current_time - silence_start
                    if duration >= self.min_section_duration:
                        sections.append(
                            FilteredSection(
                                start_seconds=silence_start,
                                end_seconds=current_time,
                                method=DetectionMethod.SILENCE,
                                confidence=min(1.0, duration / 5.0),
                                notes="Silent section at end",
                            )
                        )

                logger.info(f"Found {len(sections)} silent sections")

        except Exception as e:
            logger.error(f"Error detecting silence: {e}")

        return sections

    def combine_with_manual_skips(
        self,
        detected_sections: list[FilteredSection],
        manual_skips: list[FilteredSection],
    ) -> list[FilteredSection]:
        """Combine detected sections with manual skip sections.

        Merges overlapping sections and sorts by start time. Manual sections
        take precedence when merging.

        Args:
            detected_sections: Sections detected by heuristics.
            manual_skips: Manually specified skip sections.

        Returns:
            Sorted list of FilteredSection with overlaps merged.
        """
        # Combine all sections
        all_sections = detected_sections + manual_skips

        if not all_sections:
            return []

        # Sort by start time
        all_sections.sort(key=lambda s: s.start_seconds)

        # Merge overlapping sections
        merged: list[FilteredSection] = [all_sections[0]]

        for section in all_sections[1:]:
            last = merged[-1]

            # Check for overlap (sections overlap if one starts before the other ends)
            if section.start_seconds < last.end_seconds:
                # Merge - extend the end time if needed
                # If one section is MANUAL, preserve that method
                if (
                    last.method == DetectionMethod.MANUAL
                    or section.method == DetectionMethod.MANUAL
                ):
                    method = DetectionMethod.MANUAL
                    confidence = 1.0
                else:
                    method = last.method
                    confidence = max(last.confidence, section.confidence)

                merged[-1] = FilteredSection(
                    start_seconds=last.start_seconds,
                    end_seconds=max(last.end_seconds, section.end_seconds),
                    method=method,
                    confidence=confidence,
                    notes="Merged overlapping sections",
                )
            else:
                # No overlap - add as new section
                merged.append(section)

        return merged

    def filter_video(
        self,
        video_path: Path,
        start_time: float = 0.0,
        end_time: float | None = None,
        manual_skips: list[FilteredSection] | None = None,
    ) -> list[FilteredSection]:
        """Run complete filter analysis on a video.

        Detects black frames and silence, then combines results with
        any manual skip sections provided.

        Args:
            video_path: Path to the video file.
            start_time: Start time to analyze from (in seconds).
            end_time: End time to analyze to (in seconds). If None, analyzes to end.
            manual_skips: Optional list of manually specified skip sections.

        Returns:
            Sorted list of FilteredSection with overlaps merged.
        """
        if manual_skips is None:
            manual_skips = []

        logger.info(f"Analyzing video for credits/ads: {video_path}")

        # Detect black frames
        black_sections = self.detect_black_frames(video_path, start_time, end_time)
        logger.info(f"Detected {len(black_sections)} black frame sections")

        # Detect silence
        silence_sections = self.detect_silence(video_path, start_time, end_time)
        logger.info(f"Detected {len(silence_sections)} silent sections")

        # Combine all sections
        detected_sections = black_sections + silence_sections

        # Merge with manual skips
        all_sections = self.combine_with_manual_skips(detected_sections, manual_skips)

        logger.info(f"Total sections to filter: {len(all_sections)}")

        return all_sections
