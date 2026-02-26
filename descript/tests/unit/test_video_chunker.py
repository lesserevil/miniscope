"""Unit tests for the Video Chunker service.

This module tests the VideoChunker functionality including:
- Video file validation
- 30s chunking with 5s overlap
- Scene detection using OpenCV
- Timestamp calculation
- Error handling for invalid files
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

from hollywood_script_generator.services.video_chunker import (
    VideoChunker,
    VideoChunk,
    SceneChange,
)
from hollywood_script_generator.models.video_metadata import VideoMetadata


class TestVideoChunk:
    """Tests for the VideoChunk dataclass."""

    def test_chunk_creation(self):
        """Verify VideoChunk can be created with required fields."""
        chunk = VideoChunk(
            start_time=0.0,
            end_time=30.0,
            index=0,
            has_scene_change=False,
        )

        assert chunk.start_time == 0.0
        assert chunk.end_time == 30.0
        assert chunk.index == 0
        assert chunk.has_scene_change is False
        assert chunk.scene_changes == []

    def test_chunk_with_scene_changes(self):
        """Verify VideoChunk can include scene changes."""
        scene_changes = [
            SceneChange(timestamp=15.5, confidence=0.85),
            SceneChange(timestamp=22.0, confidence=0.92),
        ]
        chunk = VideoChunk(
            start_time=0.0,
            end_time=30.0,
            index=0,
            has_scene_change=True,
            scene_changes=scene_changes,
        )

        assert chunk.has_scene_change is True
        assert len(chunk.scene_changes) == 2
        assert chunk.scene_changes[0].timestamp == 15.5


class TestSceneChange:
    """Tests for the SceneChange dataclass."""

    def test_scene_change_creation(self):
        """Verify SceneChange can be created."""
        change = SceneChange(timestamp=10.5, confidence=0.75)

        assert change.timestamp == 10.5
        assert change.confidence == 0.75

    def test_scene_change_defaults(self):
        """Verify SceneChange uses sensible defaults."""
        change = SceneChange(timestamp=5.0)

        assert change.timestamp == 5.0
        assert change.confidence == 1.0  # Default confidence


class TestVideoChunkerInitialization:
    """Tests for VideoChunker initialization."""

    def test_chunker_can_be_instantiated(self):
        """Verify VideoChunker can be created with default settings."""
        chunker = VideoChunker()

        assert chunker is not None
        assert chunker.chunk_duration == 30.0
        assert chunker.overlap_duration == 5.0

    def test_chunker_custom_settings(self):
        """Verify VideoChunker accepts custom chunk/overlap durations."""
        chunker = VideoChunker(
            chunk_duration=60.0,
            overlap_duration=10.0,
        )

        assert chunker.chunk_duration == 60.0
        assert chunker.overlap_duration == 10.0

    def test_chunker_invalid_settings(self):
        """Verify VideoChunker validates settings."""
        with pytest.raises(ValueError):
            VideoChunker(chunk_duration=0)

        with pytest.raises(ValueError):
            VideoChunker(chunk_duration=-10)

        with pytest.raises(ValueError):
            VideoChunker(overlap_duration=-5)

        with pytest.raises(ValueError):
            VideoChunker(chunk_duration=10, overlap_duration=15)  # overlap > chunk


class TestVideoChunkerValidation:
    """Tests for video file validation."""

    def test_validate_nonexistent_file(self):
        """Verify validation fails for nonexistent files."""
        chunker = VideoChunker()

        with pytest.raises(FileNotFoundError):
            chunker._validate_video_file(Path("/nonexistent/video.mp4"))

    def test_validate_directory_instead_of_file(self):
        """Verify validation fails for directories."""
        chunker = VideoChunker()

        with pytest.raises(ValueError):
            chunker._validate_video_file(Path("/tmp"))

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_validate_non_mp4_file(self, mock_is_file, mock_exists):
        """Verify validation fails for non-MP4 files."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        chunker = VideoChunker()

        with pytest.raises(ValueError):
            chunker._validate_video_file(Path("/path/video.avi"))

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_validate_valid_mp4_file(self, mock_is_file, mock_exists):
        """Verify validation passes for valid MP4 files."""
        mock_exists.return_value = True
        mock_is_file.return_value = True

        chunker = VideoChunker()
        path = chunker._validate_video_file(Path("/path/video.mp4"))

        assert path == Path("/path/video.mp4")


class TestVideoChunkerChunkCalculation:
    """Tests for chunk calculation logic."""

    def test_calculate_chunks_30s_video(self):
        """Verify chunk calculation for 30s video."""
        chunker = VideoChunker(chunk_duration=30.0, overlap_duration=5.0)
        metadata = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=30.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunks = chunker._calculate_chunks(metadata)

        # With 30s chunks and 5s overlap: 0-30, 25-30 (final truncated chunk)
        assert len(chunks) == 2
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 30.0
        assert chunks[0].index == 0

        # Overlapping final chunk
        assert chunks[1].start_time == 25.0  # 30 - 5 overlap
        assert chunks[1].end_time == 30.0
        assert chunks[1].index == 1
    def test_calculate_chunks_60s_video_with_overlap(self):
        """Verify chunk calculation for 60s video with overlap."""
        chunker = VideoChunker(chunk_duration=30.0, overlap_duration=5.0)
        metadata = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=60.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunks = chunker._calculate_chunks(metadata)

        # With 30s chunks and 5s overlap on a 60s video:
        # Chunk 1: 0-30
        # Chunk 2: 25-55 (starts at 30 - 5 = 25)
        # Chunk 3: 50-60 (final truncated chunk)
        assert len(chunks) == 3

        # First chunk
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 30.0
        assert chunks[0].index == 0

        # Second chunk with overlap
        assert chunks[1].start_time == 25.0  # 30 - 5 overlap
        assert chunks[1].end_time == 55.0
        assert chunks[1].index == 1

        # Third chunk (truncated)
        assert chunks[2].start_time == 50.0
        assert chunks[2].end_time == 60.0
        assert chunks[2].index == 2
    def test_calculate_chunks_90s_video(self):
        """Verify chunk calculation for 90s video."""
        chunker = VideoChunker(chunk_duration=30.0, overlap_duration=5.0)
        metadata = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=90.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunks = chunker._calculate_chunks(metadata)

        # With overlap: 0-30, 25-55, 50-80, 75-90 (final chunk truncated)
        assert len(chunks) == 4

        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 30.0

        assert chunks[1].start_time == 25.0
        assert chunks[1].end_time == 55.0

        assert chunks[2].start_time == 50.0
        assert chunks[2].end_time == 80.0

        # Final chunk reaches end of video
        assert chunks[3].start_time == 75.0
        assert chunks[3].end_time == 90.0

    def test_calculate_chunks_short_video(self):
        """Verify chunk calculation for video shorter than chunk duration."""
        chunker = VideoChunker(chunk_duration=30.0, overlap_duration=5.0)
        metadata = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=15.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunks = chunker._calculate_chunks(metadata)

        assert len(chunks) == 1
        assert chunks[0].start_time == 0.0
        assert chunks[0].end_time == 15.0


class TestVideoChunkerSceneDetection:
    """Tests for scene detection functionality."""

    @patch("cv2.VideoCapture")
    def test_detect_scenes_in_chunk(self, mock_video_capture):
        """Verify scene detection returns SceneChange objects."""
        # Mock video capture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            5: 24.0,  # FPS
            7: 720,  # Total frames
        }.get(prop, 0)
        mock_cap.read.side_effect = [
            (True, MagicMock()),  # Frame at 0s
            (True, MagicMock()),  # Frame at ~0.5s
            (True, MagicMock()),  # Frame at ~1.0s (scene change)
            (True, MagicMock()),  # Frame at ~1.5s
            (False, None),  # End of video
        ]
        mock_video_capture.return_value = mock_cap

        chunker = VideoChunker()

        # Mock frame comparison to simulate scene change
        with patch.object(
            chunker, "_calculate_frame_difference", side_effect=[0.1, 0.5, 0.15, 0.1]
        ):
            scene_changes = chunker._detect_scenes_in_chunk(
                Path("/test/video.mp4"),
                start_time=0.0,
                end_time=30.0,
                threshold=0.3,
            )

        assert len(scene_changes) == 1
        assert isinstance(scene_changes[0], SceneChange)
        assert scene_changes[0].confidence > 0.3

    @patch("cv2.VideoCapture")
    def test_detect_scenes_video_not_opened(self, mock_video_capture):
        """Verify scene detection handles video open failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap

        chunker = VideoChunker()

        scene_changes = chunker._detect_scenes_in_chunk(
            Path("/test/video.mp4"),
            start_time=0.0,
            end_time=30.0,
        )

        assert scene_changes == []

    def test_calculate_frame_difference(self):
        """Verify frame difference calculation."""
        chunker = VideoChunker()

        # Create two similar frames
        import numpy as np

        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)

        # Identical frames should have 0 difference
        diff = chunker._calculate_frame_difference(frame1, frame2)
        assert diff == 0.0

        # Different frames should have higher difference
        frame2.fill(255)
        diff = chunker._calculate_frame_difference(frame1, frame2)
        assert diff > 0.9  # Should be close to 1.0


class TestVideoChunkerProcessVideo:
    """Tests for the main process_video method."""

    @patch(
        "hollywood_script_generator.services.video_chunker.VideoChunker._get_video_metadata"
    )
    @patch(
        "hollywood_script_generator.services.video_chunker.VideoChunker._validate_video_file"
    )
    def test_process_video_success(self, mock_validate, mock_get_metadata):
        """Verify successful video processing returns chunks with metadata."""
        mock_validate.return_value = Path("/test/video.mp4")
        mock_get_metadata.return_value = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=30.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunker = VideoChunker()

        with patch.object(chunker, "_detect_scenes_in_chunk", return_value=[]):
            result = chunker.process_video(Path("/test/video.mp4"))

        assert result is not None
        assert "chunks" in result
        assert "metadata" in result
        # With 30s duration and 5s overlap, expect 2 chunks: 0-30 and 25-30
        assert len(result["chunks"]) == 2
        assert result["metadata"].duration == 30.0

    @patch(
        "hollywood_script_generator.services.video_chunker.VideoChunker._validate_video_file"
    )
    def test_process_video_invalid_file(self, mock_validate):
        """Verify processing fails for invalid files."""
        mock_validate.side_effect = FileNotFoundError("Video not found")

        chunker = VideoChunker()

        with pytest.raises(FileNotFoundError):
            chunker.process_video(Path("/nonexistent/video.mp4"))

    @patch(
        "hollywood_script_generator.services.video_chunker.VideoChunker._get_video_metadata"
    )
    @patch(
        "hollywood_script_generator.services.video_chunker.VideoChunker._validate_video_file"
    )
    def test_process_video_with_scene_changes(self, mock_validate, mock_get_metadata):
        """Verify chunks include scene change information."""
        mock_validate.return_value = Path("/test/video.mp4")
        mock_get_metadata.return_value = VideoMetadata(
            path=Path("/test/video.mp4"),
            duration=60.0,
            fps=24.0,
            resolution=(1920, 1080),
        )

        chunker = VideoChunker()

        scene_changes = [SceneChange(timestamp=15.0, confidence=0.85)]

        with patch.object(
            chunker, "_detect_scenes_in_chunk", return_value=scene_changes
        ):
            result = chunker.process_video(Path("/test/video.mp4"))

        # The first chunk (0-30) should contain the scene change at 15s
        chunk_0 = result["chunks"][0]
        assert chunk_0.has_scene_change is True
        assert len(chunk_0.scene_changes) == 1
        assert chunk_0.scene_changes[0].timestamp == 15.0


class TestVideoChunkerGetVideoMetadata:
    """Tests for video metadata extraction."""

    @patch("hollywood_script_generator.services.video_chunker.VideoFileClip")
    def test_get_video_metadata_success(self, mock_video_clip_class):
        """Verify metadata extraction from video file."""
        mock_clip = MagicMock()
        mock_clip.duration = 120.5
        mock_clip.fps = 24.0
        mock_clip.size = (1920, 1080)
        
        # Set up the context manager mock
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_clip)
        mock_context.__exit__ = MagicMock(return_value=None)
        mock_video_clip_class.return_value = mock_context

        chunker = VideoChunker()
        metadata = chunker._get_video_metadata(Path("/test/video.mp4"))

        assert metadata is not None
        assert metadata.duration == 120.5
        assert metadata.fps == 24.0
        assert metadata.resolution == (1920, 1080)
        assert metadata.path == Path("/test/video.mp4")

    @patch("hollywood_script_generator.services.video_chunker.VideoFileClip")
    def test_get_video_metadata_error(self, mock_video_clip_class):
        """Verify error handling for metadata extraction failure."""
        mock_video_clip_class.side_effect = Exception("Failed to load video")

        chunker = VideoChunker()

        with pytest.raises(Exception):
            chunker._get_video_metadata(Path("/test/video.mp4"))


class TestVideoChunkerTypeAnnotations:
    """Tests for type annotations and signatures."""

    def test_process_video_has_type_hints(self):
        """Verify process_video method has proper type annotations."""
        import inspect

        chunker = VideoChunker()
        sig = inspect.signature(chunker.process_video)
        params = sig.parameters

        assert "video_path" in params
        assert params["video_path"].annotation == Path

        # Check return type
        assert sig.return_annotation != inspect.Signature.empty

    def test_chunk_dataclass_typing(self):
        """Verify VideoChunk uses proper type annotations."""
        import inspect

        sig = inspect.signature(VideoChunk)
        params = sig.parameters

        assert "start_time" in params
        assert "end_time" in params
        assert "index" in params
        assert "has_scene_change" in params
        assert "scene_changes" in params
