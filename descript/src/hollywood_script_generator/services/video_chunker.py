"""Video chunker service for scene-based video processing.

This module provides the VideoChunker class for:
- Splitting videos into 30-second chunks with 5-second overlap
- Detecting scene changes using OpenCV
- Extracting video metadata
- Managing chunk boundaries with timestamps
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from moviepy import VideoFileClip

from hollywood_script_generator.models.video_metadata import VideoMetadata


@dataclass
class SceneChange:
    """Represents a detected scene change.

    Attributes:
        timestamp: Time in seconds where the scene change occurs.
        confidence: Confidence score (0.0-1.0) for the scene change detection.
    """

    timestamp: float
    confidence: float = 1.0


@dataclass
class VideoChunk:
    """Represents a chunk of video with timing information.

    Attributes:
        start_time: Start time in seconds (inclusive).
        end_time: End time in seconds (inclusive).
        index: Sequential index of the chunk (0-based).
        has_scene_change: Whether this chunk contains any scene changes.
        scene_changes: List of scene changes detected in this chunk.
    """

    start_time: float
    end_time: float
    index: int
    has_scene_change: bool = False
    scene_changes: List[SceneChange] = field(default_factory=list)


class VideoChunker:
    """Service for chunking videos and detecting scenes.

    This service splits videos into overlapping chunks for processing and
    detects scene changes using computer vision techniques.

    Attributes:
        chunk_duration: Duration of each chunk in seconds (default: 30.0).
        overlap_duration: Overlap between consecutive chunks in seconds (default: 5.0).
        scene_threshold: Threshold for scene change detection (default: 0.3).

    Example:
        >>> chunker = VideoChunker(chunk_duration=30.0, overlap_duration=5.0)
        >>> result = chunker.process_video(Path("/path/to/video.mp4"))
        >>> for chunk in result["chunks"]:
        ...     print(f"Chunk {chunk.index}: {chunk.start_time}s - {chunk.end_time}s")
    """

    def __init__(
        self,
        chunk_duration: float = 30.0,
        overlap_duration: float = 5.0,
        scene_threshold: float = 0.3,
    ):
        """Initialize the VideoChunker.

        Args:
            chunk_duration: Duration of each chunk in seconds.
            overlap_duration: Overlap between consecutive chunks in seconds.
            scene_threshold: Threshold (0.0-1.0) for scene change detection.

        Raises:
            ValueError: If chunk_duration, overlap_duration are invalid, or
                       if overlap_duration >= chunk_duration.
        """
        if chunk_duration <= 0:
            raise ValueError("chunk_duration must be positive")
        if overlap_duration < 0:
            raise ValueError("overlap_duration must be non-negative")
        if overlap_duration >= chunk_duration:
            raise ValueError("overlap_duration must be less than chunk_duration")
        if scene_threshold < 0 or scene_threshold > 1:
            raise ValueError("scene_threshold must be between 0 and 1")

        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.scene_threshold = scene_threshold

    def _validate_video_file(self, video_path: Path) -> Path:
        """Validate that the video file exists and is an MP4.

        Args:
            video_path: Path to the video file.

        Returns:
            The validated path.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the path is not a file or not an MP4.
        """
        path = Path(video_path)

        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {video_path}")

        if path.suffix.lower() not in [".mp4", ".m4v"]:
            raise ValueError(f"File must be an MP4 or M4V file: {video_path}")

        return path

    def _get_video_metadata(self, video_path: Path) -> VideoMetadata:
        """Extract metadata from a video file using MoviePy.

        Args:
            video_path: Path to the video file.

        Returns:
            VideoMetadata with extracted information.

        Raises:
            Exception: If the video cannot be loaded or parsed.
        """
        try:
            with VideoFileClip(str(video_path)) as clip:
                return VideoMetadata(
                    path=video_path,
                    duration=clip.duration,
                    fps=clip.fps,
                    resolution=clip.size,
                    file_size=video_path.stat().st_size
                    if video_path.exists()
                    else None,
                )
        except Exception as e:
            raise Exception(f"Failed to extract metadata from {video_path}: {e}") from e

    def _calculate_chunks(self, metadata: VideoMetadata) -> List[VideoChunk]:
        """Calculate chunk boundaries for a video.

        Creates chunks of duration `chunk_duration` with `overlap_duration`
        overlap between consecutive chunks. The final chunk may be shorter
        if it reaches the end of the video.

        Args:
            metadata: Video metadata including duration.

        Returns:
            List of VideoChunk objects with calculated boundaries.
        """
        chunks: List[VideoChunk] = []
        duration = metadata.duration
        step = self.chunk_duration - self.overlap_duration

        index = 0
        start_time = 0.0

        while start_time < duration:
            end_time = min(start_time + self.chunk_duration, duration)

            chunk = VideoChunk(
                start_time=start_time,
                end_time=end_time,
                index=index,
            )
            chunks.append(chunk)

            # Move to next chunk position
            start_time += step
            index += 1

        return chunks

    def _calculate_frame_difference(
        self, frame1: np.ndarray, frame2: np.ndarray
    ) -> float:
        """Calculate the difference between two video frames.

        Uses histogram comparison to detect visual changes between frames.

        Args:
            frame1: First frame as numpy array.
            frame2: Second frame as numpy array.

        Returns:
            Difference score between 0.0 (identical) and 1.0 (completely different).
        """
        # Convert frames to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Calculate histograms
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

        # Normalize histograms
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()

        # Compare histograms using correlation
        correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

        # Convert correlation to difference (0 = identical, 1 = different)
        difference = 1.0 - max(0.0, correlation)

        return difference

    def _detect_scenes_in_chunk(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        threshold: Optional[float] = None,
    ) -> List[SceneChange]:
        """Detect scene changes within a specific time range of a video.

        Uses OpenCV to analyze frames and detect significant visual changes
        that indicate scene transitions.

        Args:
            video_path: Path to the video file.
            start_time: Start time in seconds.
            end_time: End time in seconds.
            threshold: Scene change threshold (uses self.scene_threshold if None).

        Returns:
            List of SceneChange objects detected in the time range.
        """
        if threshold is None:
            threshold = self.scene_threshold

        scene_changes: List[SceneChange] = []

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            return scene_changes

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)

            # Seek to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            prev_frame: Optional[np.ndarray] = None
            frame_idx = start_frame

            while frame_idx <= end_frame:
                ret, frame = cap.read()

                if not ret:
                    break

                if prev_frame is not None:
                    difference = self._calculate_frame_difference(prev_frame, frame)

                    if difference > threshold:
                        timestamp = frame_idx / fps
                        scene_changes.append(
                            SceneChange(
                                timestamp=timestamp,
                                confidence=difference,
                            )
                        )

                prev_frame = frame
                frame_idx += 1

        finally:
            cap.release()

        return scene_changes

    def process_video(self, video_path: Path) -> Dict[str, Any]:
        """Process a video file and return chunks with scene detection.

        This is the main entry point for the VideoChunker service. It:
        1. Validates the video file
        2. Extracts metadata
        3. Calculates chunk boundaries
        4. Detects scene changes in each chunk

        Args:
            video_path: Path to the MP4 video file.

        Returns:
            Dictionary containing:
                - "chunks": List of VideoChunk objects
                - "metadata": VideoMetadata object

        Raises:
            FileNotFoundError: If the video file does not exist.
            ValueError: If the file is not a valid MP4.
            Exception: If metadata extraction fails.
        """
        # Validate the video file
        validated_path = self._validate_video_file(video_path)

        # Extract metadata
        metadata = self._get_video_metadata(validated_path)

        # Calculate chunks
        chunks = self._calculate_chunks(metadata)

        # Detect scenes in each chunk
        for chunk in chunks:
            scene_changes = self._detect_scenes_in_chunk(
                validated_path,
                chunk.start_time,
                chunk.end_time,
            )

            if scene_changes:
                chunk.scene_changes = scene_changes
                chunk.has_scene_change = True

        return {
            "chunks": chunks,
            "metadata": metadata,
        }
