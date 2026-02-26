"""Unit tests for the Credits Filter service.

This module tests the CreditsFilter functionality including:
- Black frame detection using OpenCV
- Silence detection using audio amplitude
- Threshold configuration
- Combining with manual skip sections
- Time range merging

Uses mocks to avoid actual video processing in tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from hollywood_script_generator.services.credits_filter import (
    CreditsFilter,
    DetectionMethod,
    FilteredSection,
)


class TestFilteredSection:
    """Tests for the FilteredSection dataclass."""

    def test_filtered_section_creation(self):
        """Verify FilteredSection can be created with required fields."""
        section = FilteredSection(
            start_seconds=10.0,
            end_seconds=30.0,
            method=DetectionMethod.BLACK_FRAME,
            confidence=0.95,
        )

        assert section.start_seconds == 10.0
        assert section.end_seconds == 30.0
        assert section.method == DetectionMethod.BLACK_FRAME
        assert section.confidence == 0.95

    def test_filtered_section_optional_notes(self):
        """Verify FilteredSection can include optional notes."""
        section = FilteredSection(
            start_seconds=0.0,
            end_seconds=5.0,
            method=DetectionMethod.SILENCE,
            confidence=0.80,
            notes="End credits",
        )

        assert section.notes == "End credits"
        assert section.method == DetectionMethod.SILENCE

    def test_filtered_section_enum_values(self):
        """Verify DetectionMethod enum values are correct."""
        assert DetectionMethod.BLACK_FRAME.value == "black_frame"
        assert DetectionMethod.SILENCE.value == "silence"
        assert DetectionMethod.MANUAL.value == "manual"


class TestCreditsFilterInitialization:
    """Tests for CreditsFilter initialization."""

    def test_filter_can_be_instantiated(self):
        """Verify CreditsFilter can be created with default settings."""
        filter_service = CreditsFilter()

        assert filter_service is not None
        assert filter_service.black_frame_threshold == 20
        assert filter_service.silence_threshold_db == -40
        assert filter_service.min_section_duration == 1.0

    def test_filter_custom_settings(self):
        """Verify CreditsFilter accepts custom threshold settings."""
        filter_service = CreditsFilter(
            black_frame_threshold=15,
            silence_threshold_db=-35,
            min_section_duration=2.0,
        )

        assert filter_service.black_frame_threshold == 15
        assert filter_service.silence_threshold_db == -35
        assert filter_service.min_section_duration == 2.0

    def test_filter_invalid_thresholds(self):
        """Verify CreditsFilter validates threshold settings."""
        with pytest.raises(ValueError):
            CreditsFilter(black_frame_threshold=0)

        with pytest.raises(ValueError):
            CreditsFilter(black_frame_threshold=256)  # Above max

        with pytest.raises(ValueError):
            CreditsFilter(silence_threshold_db=10)  # Positive dB

        with pytest.raises(ValueError):
            CreditsFilter(min_section_duration=0)


class TestBlackFrameDetection:
    """Tests for black frame detection functionality."""

    @patch("cv2.VideoCapture")
    def test_detect_black_frames(self, mock_video_capture):
        """Verify black frame detection returns FilteredSection objects."""
        # Mock video capture with 30 FPS
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            5: 30.0,  # FPS
            7: 300,   # Total frames (10 seconds)
        }.get(prop, 0)

        # Need at least 30 frames (1 second) of black to exceed min_section_duration
        # Create 50 frames: 10 normal, 30 black (1s), 10 normal
        frames = []
        brightness_values = []
        for i in range(50):
            frames.append((True, MagicMock()))
            if 10 <= i < 40:  # Frames 10-39 are black (30 frames = 1 second)
                brightness_values.append(10)  # Below threshold of 20
            else:
                brightness_values.append(50)  # Above threshold
        frames.append((False, None))  # End of video

        mock_cap.read.side_effect = frames
        mock_video_capture.return_value = mock_cap

        filter_service = CreditsFilter(min_section_duration=1.0)

        # Mock frame brightness calculation
        with patch.object(
            filter_service, "_calculate_frame_brightness", side_effect=brightness_values
        ):
            sections = filter_service.detect_black_frames(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=10.0,
            )

        assert len(sections) == 1
        assert sections[0].method == DetectionMethod.BLACK_FRAME
        # Check that the section covers approximately the black frame duration
        duration = sections[0].end_seconds - sections[0].start_seconds
        assert duration >= 1.0  # At least min_section_duration
    @patch("cv2.VideoCapture")
    def test_detect_black_frames_video_not_opened(self, mock_video_capture):
        """Verify black frame detection handles video open failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap

        filter_service = CreditsFilter()

        sections = filter_service.detect_black_frames(
            Path("/test/video.mp4"),
            start_time=0.0,
            end_time=10.0,
        )

        assert sections == []

    def test_calculate_frame_brightness(self):
        """Verify frame brightness calculation."""
        filter_service = CreditsFilter()

        # Create a black frame
        black_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        brightness = filter_service._calculate_frame_brightness(black_frame)
        assert brightness == 0.0

        # Create a white frame
        white_frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        brightness = filter_service._calculate_frame_brightness(white_frame)
        assert brightness == 255.0

        # Create a gray frame (128)
        gray_frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        brightness = filter_service._calculate_frame_brightness(gray_frame)
        assert brightness == 128.0

    @patch("cv2.VideoCapture")
    def test_black_frame_threshold_respected(self, mock_video_capture):
        """Verify black frame detection respects threshold."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 10.0}.get(prop, 0)
        mock_cap.read.side_effect = [
            (True, MagicMock()),  # brightness 25 (dark but above threshold)
            (False, None),
        ]
        mock_video_capture.return_value = mock_cap

        # Use threshold of 20 - frame with brightness 25 should NOT be detected
        filter_service = CreditsFilter(black_frame_threshold=20)

        with patch.object(
            filter_service, "_calculate_frame_brightness", return_value=25
        ):
            sections = filter_service.detect_black_frames(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=10.0,
            )

        assert len(sections) == 0  # No black frames detected

    @patch("cv2.VideoCapture")
    def test_black_frame_min_duration_filtering(self, mock_video_capture):
        """Verify short black frame sections are filtered out."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 30.0}.get(prop, 0)
        mock_cap.read.side_effect = [
            (True, MagicMock()),  # Normal
            (True, MagicMock()),  # Black for 1 frame (~33ms)
            (True, MagicMock()),  # Normal
            (False, None),
        ]
        mock_video_capture.return_value = mock_cap

        filter_service = CreditsFilter(min_section_duration=0.5)  # 500ms minimum

        with patch.object(
            filter_service, "_calculate_frame_brightness", side_effect=[100, 5, 100]
        ):
            sections = filter_service.detect_black_frames(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=1.0,
            )

        # Section is too short, should be filtered out
        assert len(sections) == 0


class TestSilenceDetection:
    """Tests for silence detection functionality."""

    @patch("hollywood_script_generator.services.credits_filter.VideoFileClip")
    def test_detect_silence_sections(self, mock_video_clip_class):
        """Verify silence detection returns FilteredSection objects."""
        # Create mock audio that will be returned by subclipped().to_soundarray()
        def create_mock_audio_chunk(start, end, silent=False):
            """Create a mock audio chunk with appropriate amplitude."""
            duration = end - start
            samples = int(duration * 16000)  # 16kHz sample rate
            if silent:
                # Silent audio - amplitude near zero
                data = np.ones((samples, 2), dtype=np.float32) * 1e-8
            else:
                # Loud audio - amplitude 0.5
                data = np.ones((samples, 2), dtype=np.float32) * 0.5
            return data

        # Mock the subclipped audio interface
        mock_audio_subclips = []
        # Create 4 chunks: loud (0-0.5s), silent (0.5-1.5s), silent (1.5-2.0s), loud (2.0-10s)
        chunks = [
            (0.0, 0.5, False),   # 0.0-0.5: loud
            (0.5, 1.0, True),    # 0.5-1.0: silent
            (1.0, 1.5, True),    # 1.0-1.5: silent
            (1.5, 2.0, True),    # 1.5-2.0: silent
        ]

        for start, end, silent in chunks:
            mock_subclip = MagicMock()
            mock_subclip.to_soundarray.return_value = create_mock_audio_chunk(start, end, silent)
            mock_audio_subclips.append((start, end, mock_subclip))

        def mock_subclipped(start, end):
            for s, e, subclip in mock_audio_subclips:
                if abs(s - start) < 0.01 and abs(e - end) < 0.01:
                    return subclip
            # Default: return loud audio
            default = MagicMock()
            default.to_soundarray.return_value = create_mock_audio_chunk(start, end, False)
            return default

        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_clip.audio = MagicMock()
        mock_clip.audio.subclipped.side_effect = mock_subclipped

        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_clip)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_video_clip_class.return_value = mock_context

        filter_service = CreditsFilter(silence_threshold_db=-40, min_section_duration=0.5)

        sections = filter_service.detect_silence(
            Path("/test/video.mp4"),
            start_time=0.0,
            end_time=2.0,
        )

        assert len(sections) == 1
        assert sections[0].method == DetectionMethod.SILENCE
    @patch("hollywood_script_generator.services.credits_filter.VideoFileClip")
    def test_detect_silence_video_error(self, mock_video_clip_class):
        """Verify silence detection handles video errors."""
        mock_video_clip_class.side_effect = Exception("Failed to load video")

        filter_service = CreditsFilter()

        sections = filter_service.detect_silence(
            Path("/test/video.mp4"),
            start_time=0.0,
            end_time=10.0,
        )

        assert sections == []

    def test_calculate_audio_level(self):
        """Verify audio level calculation."""
        filter_service = CreditsFilter()

        # Silent audio
        silent_audio = np.zeros((1000, 2), dtype=np.float32)
        level = filter_service._calculate_audio_level(silent_audio)
        assert level < -100  # Very low dB

        # Loud audio
        loud_audio = np.ones((1000, 2), dtype=np.float32) * 0.5
        level = filter_service._calculate_audio_level(loud_audio)
        assert level > -20  # Around -6 dB for 0.5 amplitude

    def test_audio_level_mono_conversion(self):
        """Verify stereo to mono conversion."""
        filter_service = CreditsFilter()

        # Stereo audio with different channels
        stereo_audio = np.array(
            [
                [1.0, 0.0],  # Left loud, right silent
                [0.0, 1.0],  # Left silent, right loud
            ],
            dtype=np.float32,
        )

        level = filter_service._calculate_audio_level(stereo_audio)
        # After averaging, both channels contribute equally
        assert level < 0  # Should be negative dB


class TestManualSkipCombination:
    """Tests for combining with manual skip sections."""

    def test_combine_with_manual_skips(self):
        """Verify detected sections can be combined with manual skips."""
        filter_service = CreditsFilter()

        detected_sections = [
            FilteredSection(0.0, 5.0, DetectionMethod.BLACK_FRAME, 0.9),
            FilteredSection(120.0, 125.0, DetectionMethod.SILENCE, 0.85),
        ]

        manual_skips = [
            FilteredSection(10.0, 15.0, DetectionMethod.MANUAL, 1.0, "Ads"),
        ]

        combined = filter_service.combine_with_manual_skips(
            detected_sections, manual_skips
        )

        assert len(combined) == 3
        assert any(s.method == DetectionMethod.MANUAL for s in combined)

    def test_merge_overlapping_sections(self):
        """Verify overlapping detected and manual sections are merged."""
        filter_service = CreditsFilter()

        detected_sections = [
            FilteredSection(0.0, 10.0, DetectionMethod.BLACK_FRAME, 0.9),
        ]

        manual_skips = [
            FilteredSection(8.0, 15.0, DetectionMethod.MANUAL, 1.0),  # Overlaps
        ]

        combined = filter_service.combine_with_manual_skips(
            detected_sections, manual_skips
        )

        # Should merge into single section: 0.0 - 15.0
        assert len(combined) == 1
        assert combined[0].start_seconds == 0.0
        assert combined[0].end_seconds == 15.0
        assert combined[0].method == DetectionMethod.MANUAL

    def test_sort_combined_sections(self):
        """Verify combined sections are sorted by start time."""
        filter_service = CreditsFilter()

        sections = [
            FilteredSection(50.0, 60.0, DetectionMethod.BLACK_FRAME, 0.9),
            FilteredSection(10.0, 20.0, DetectionMethod.SILENCE, 0.85),
            FilteredSection(30.0, 40.0, DetectionMethod.BLACK_FRAME, 0.8),
        ]

        combined = filter_service.combine_with_manual_skips(sections, [])

        # Should be sorted by start time
        assert combined[0].start_seconds == 10.0
        assert combined[1].start_seconds == 30.0
        assert combined[2].start_seconds == 50.0

    def test_filter_adjacent_but_not_overlapping(self):
        """Verify adjacent sections are not merged."""
        filter_service = CreditsFilter()

        sections = [
            FilteredSection(0.0, 10.0, DetectionMethod.BLACK_FRAME, 0.9),
            FilteredSection(10.0, 20.0, DetectionMethod.SILENCE, 0.85),
        ]

        combined = filter_service.combine_with_manual_skips(sections, [])

        # Adjacent sections should remain separate
        assert len(combined) == 2


class TestEndToEndFiltering:
    """Tests for end-to-end filtering workflow."""

    @patch("cv2.VideoCapture")
    @patch("hollywood_script_generator.services.credits_filter.VideoFileClip")
    def test_filter_video_combined_detection(self, mock_video_clip, mock_video_capture):
        """Verify complete filtering workflow combining black frames and silence."""
        # Mock video capture for black frame detection
        # Need at least 10 frames at 10fps to get 1 second of black frames (min_section_duration)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            5: 10.0,  # 10 FPS
            7: 100,   # 100 frames = 10 seconds
        }.get(prop, 0)

        # Create 30 frames: 5 normal, 20 black (2s), 5 normal
        # 20 frames at 10fps = 2 seconds, which exceeds min_section_duration of 1.0
        frames = []
        brightness_values = []
        for i in range(30):
            frames.append((True, MagicMock()))
            if 5 <= i < 25:  # Frames 5-24 are black (20 frames = 2 seconds)
                brightness_values.append(10)  # Below threshold of 20
            else:
                brightness_values.append(50)  # Above threshold
        frames.append((False, None))  # End of video

        mock_cap.read.side_effect = frames
        mock_video_capture.return_value = mock_cap

        # Mock video clip for silence detection (no audio)
        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_clip.audio = None  # No audio, so silence detection returns empty

        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_clip)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_video_clip.return_value = mock_context

        filter_service = CreditsFilter(min_section_duration=1.0)

        with patch.object(
            filter_service, "_calculate_frame_brightness", side_effect=brightness_values
        ):
            sections = filter_service.filter_video(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=10.0,
                manual_skips=[],
            )

        # Should have detected the black frame section
        assert len(sections) == 1
        assert sections[0].method == DetectionMethod.BLACK_FRAME
    @patch("cv2.VideoCapture")
    def test_filter_video_with_manual_skips(self, mock_video_capture):
        """Verify filter_video includes manual skips in output."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {5: 1.0}.get(prop, 0)
        mock_cap.read.return_value = (False, None)  # No frames
        mock_video_capture.return_value = mock_cap

        filter_service = CreditsFilter()

        manual_skips = [
            FilteredSection(0.0, 5.0, DetectionMethod.MANUAL, 1.0, "Credits"),
        ]

        with (
            patch.object(filter_service, "detect_black_frames", return_value=[]),
            patch.object(filter_service, "detect_silence", return_value=[]),
        ):
            sections = filter_service.filter_video(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=60.0,
                manual_skips=manual_skips,
            )

        assert len(sections) == 1
        assert sections[0].method == DetectionMethod.MANUAL


class TestTypeAnnotations:
    """Tests for type annotations and signatures."""

    def test_filter_video_has_type_hints(self):
        """Verify filter_video method has proper type annotations."""
        import inspect

        filter_service = CreditsFilter()
        sig = inspect.signature(filter_service.filter_video)
        params = sig.parameters

        assert "video_path" in params
        assert params["video_path"].annotation == Path

        # Check return type
        assert sig.return_annotation != inspect.Signature.empty

    def test_filtered_section_dataclass_typing(self):
        """Verify FilteredSection uses proper type annotations."""
        import inspect

        sig = inspect.signature(FilteredSection)
        params = sig.parameters

        assert "start_seconds" in params
        assert "end_seconds" in params
        assert "method" in params
        assert "confidence" in params
        assert "notes" in params
