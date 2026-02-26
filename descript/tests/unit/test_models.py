"""Tests for data models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from hollywood_script_generator.models.job_status import JobStatus
from hollywood_script_generator.models.video_metadata import VideoMetadata


class TestJobStatus:
    """Test suite for JobStatus enum."""

    def test_job_status_values(self):
        """Test that JobStatus has all expected values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.PROCESSING == "processing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"

    def test_job_status_enum_members(self):
        """Test that all expected enum members exist."""
        members = list(JobStatus)
        assert len(members) == 4
        assert JobStatus.PENDING in members
        assert JobStatus.PROCESSING in members
        assert JobStatus.COMPLETED in members
        assert JobStatus.FAILED in members

    def test_job_status_from_string(self):
        """Test creating JobStatus from string."""
        assert JobStatus("pending") == JobStatus.PENDING
        assert JobStatus("processing") == JobStatus.PROCESSING
        assert JobStatus("completed") == JobStatus.COMPLETED
        assert JobStatus("failed") == JobStatus.FAILED

    def test_job_status_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            JobStatus("invalid")

    def test_job_status_comparison(self):
        """Test job status comparison."""
        assert JobStatus.PENDING != JobStatus.PROCESSING
        assert JobStatus.COMPLETED == JobStatus.COMPLETED


class TestVideoMetadata:
    """Test suite for VideoMetadata model."""

    def test_video_metadata_creation(self):
        """Test creating VideoMetadata with valid data."""
        video = VideoMetadata(
            path=Path("/videos/test.mp4"),
            duration=120.5,
            fps=24.0,
            resolution=(1920, 1080),
        )

        assert video.path == Path("/videos/test.mp4")
        assert video.duration == 120.5
        assert video.fps == 24.0
        assert video.resolution == (1920, 1080)

    def test_video_metadata_optional_fields(self):
        """Test VideoMetadata with optional fields."""
        video = VideoMetadata(
            path=Path("/videos/test.mp4"),
            duration=60.0,
            fps=30.0,
            resolution=(1280, 720),
            file_size=1024000,
            codec="h264",
            bitrate=5000000,
            audio_codec="aac",
            audio_channels=2,
            audio_sample_rate=48000,
        )

        assert video.file_size == 1024000
        assert video.codec == "h264"
        assert video.bitrate == 5000000
        assert video.audio_codec == "aac"
        assert video.audio_channels == 2
        assert video.audio_sample_rate == 48000

    def test_video_metadata_required_fields(self):
        """Test that required fields are enforced."""
        # Missing path
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(duration=60.0, fps=30.0, resolution=(1280, 720))
        assert "path" in str(exc_info.value)

        # Missing duration
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"), fps=30.0, resolution=(1280, 720)
            )
        assert "duration" in str(exc_info.value)

        # Missing fps
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"), duration=60.0, resolution=(1280, 720)
            )
        assert "fps" in str(exc_info.value)

        # Missing resolution
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
            )
        assert "resolution" in str(exc_info.value)

    def test_video_metadata_duration_validation(self):
        """Test that duration must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=-1.0,
                fps=30.0,
                resolution=(1280, 720),
            )
        assert "duration" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=0.0,
                fps=30.0,
                resolution=(1280, 720),
            )
        assert "duration" in str(exc_info.value)

    def test_video_metadata_fps_validation(self):
        """Test that fps must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=-24.0,
                resolution=(1280, 720),
            )
        assert "fps" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=0.0,
                resolution=(1280, 720),
            )
        assert "fps" in str(exc_info.value)

    def test_video_metadata_resolution_validation(self):
        """Test that resolution must be a tuple of two positive integers."""
        # Resolution with negative values
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(-1920, 1080),
            )
        assert "resolution" in str(exc_info.value)

        # Resolution with zero values
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(0, 1080),
            )
        assert "resolution" in str(exc_info.value)

        # Resolution with wrong tuple size
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(1920, 1080, 30),  # Three elements instead of two
            )
        assert "resolution" in str(exc_info.value)

    def test_video_metadata_path_coercion(self):
        """Test that string paths are coerced to Path objects."""
        video = VideoMetadata(
            path="/videos/test.mp4", duration=60.0, fps=30.0, resolution=(1920, 1080)
        )

        assert isinstance(video.path, Path)
        assert video.path == Path("/videos/test.mp4")

    def test_video_metadata_file_size_validation(self):
        """Test that file_size must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(1920, 1080),
                file_size=-1,
            )
        assert "file_size" in str(exc_info.value)

    def test_video_metadata_bitrate_validation(self):
        """Test that bitrate must be positive when provided."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(1920, 1080),
                bitrate=-1,
            )
        assert "bitrate" in str(exc_info.value)

    def test_video_metadata_audio_channels_validation(self):
        """Test that audio_channels must be positive when provided."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(1920, 1080),
                audio_channels=-1,
            )
        assert "audio_channels" in str(exc_info.value)

    def test_video_metadata_audio_sample_rate_validation(self):
        """Test that audio_sample_rate must be positive when provided."""
        with pytest.raises(ValidationError) as exc_info:
            VideoMetadata(
                path=Path("/videos/test.mp4"),
                duration=60.0,
                fps=30.0,
                resolution=(1920, 1080),
                audio_sample_rate=-1,
            )
        assert "audio_sample_rate" in str(exc_info.value)
