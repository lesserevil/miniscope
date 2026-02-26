"""Video metadata models."""

from pathlib import Path
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoMetadata(BaseModel):
    """Metadata for a video file.

    This model stores technical information about a video file,
    including path, duration, frame rate, resolution, and optional
    codec information.

    Attributes:
        path: Path to the video file.
        duration: Video duration in seconds (must be positive).
        fps: Frames per second (must be positive).
        resolution: Tuple of (width, height) in pixels.
        file_size: File size in bytes (optional, must be non-negative).
        codec: Video codec name (optional).
        bitrate: Video bitrate in bits per second (optional, must be positive).
        audio_codec: Audio codec name (optional).
        audio_channels: Number of audio channels (optional, must be positive).
        audio_sample_rate: Audio sample rate in Hz (optional, must be positive).
    """

    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # Required fields
    path: Path = Field(..., description="Path to the video file")
    duration: float = Field(..., gt=0, description="Video duration in seconds")
    fps: float = Field(..., gt=0, description="Frames per second")
    resolution: Tuple[int, int] = Field(
        ..., description="Video resolution as (width, height) in pixels"
    )

    # Optional fields
    file_size: Optional[int] = Field(
        default=None, ge=0, description="File size in bytes"
    )
    codec: Optional[str] = Field(
        default=None, description="Video codec name (e.g., 'h264', 'hevc')"
    )
    bitrate: Optional[int] = Field(
        default=None, gt=0, description="Video bitrate in bits per second"
    )
    audio_codec: Optional[str] = Field(
        default=None, description="Audio codec name (e.g., 'aac', 'mp3')"
    )
    audio_channels: Optional[int] = Field(
        default=None, gt=0, description="Number of audio channels"
    )
    audio_sample_rate: Optional[int] = Field(
        default=None, gt=0, description="Audio sample rate in Hz"
    )

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: Tuple[int, int]) -> Tuple[int, int]:
        """Validate that resolution is a tuple of two positive integers."""
        if len(v) != 2:
            raise ValueError(
                "Resolution must be a tuple of two integers (width, height)"
            )
        if v[0] <= 0 or v[1] <= 0:
            raise ValueError("Resolution width and height must be positive integers")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path is a Path object."""
        if isinstance(v, str):
            return Path(v)
        return v

    @property
    def width(self) -> int:
        """Video width in pixels."""
        return self.resolution[0]

    @property
    def height(self) -> int:
        """Video height in pixels."""
        return self.resolution[1]

    @property
    def total_frames(self) -> int:
        """Total number of frames in the video."""
        return int(self.duration * self.fps)

    def __repr__(self) -> str:
        """Return a string representation of the video metadata."""
        return (
            f"VideoMetadata("
            f"path={self.path!r}, "
            f"duration={self.duration:.2f}s, "
            f"fps={self.fps}, "
            f"resolution={self.width}x{self.height}"
            f")"
        )
