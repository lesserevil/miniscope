"""Audio transcriber service using OpenAI Whisper.

This module provides the AudioTranscriber class for:
- Loading Whisper models (with caching)
- Transcribing video chunks with timestamps
- Extracting audio from video files
- Batch processing multiple chunks
- Supporting CPU/CUDA device selection

Example:
    >>> from hollywood_script_generator.core.config import Settings
    >>> settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
    >>> transcriber = AudioTranscriber(settings=settings)
    >>> result = transcriber.transcribe_chunk(
    ...     video_path=Path("/path/to/video.mp4"),
    ...     start_time=0.0,
    ...     end_time=30.0,
    ... )
    >>> print(result.text)
    "Hello world"
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union
import logging

import numpy as np
import whisper
from moviepy import VideoFileClip

from hollywood_script_generator.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment with timing.

    Attributes:
        text: The transcribed text content.
        start_time: Start time in seconds (absolute video time).
        end_time: End time in seconds (absolute video time).
    """

    text: str
    start_time: float
    end_time: float

    def __post_init__(self):
        """Strip whitespace from text after initialization."""
        self.text = self.text.strip()


@dataclass
class TranscriptionResult:
    """Represents the complete transcription result for a chunk.

    Attributes:
        text: The full transcribed text (concatenated segments).
        segments: List of individual transcription segments.
        chunk_start_time: Start time of the chunk in the video.
        chunk_end_time: End time of the chunk in the video.
    """

    text: str
    segments: List[TranscriptionSegment]
    chunk_start_time: float
    chunk_end_time: float


class AudioTranscriber:
    """Service for transcribing audio using OpenAI Whisper.

    This service loads a Whisper model and provides methods to transcribe
    audio from video chunks. It supports model caching, device selection
    (CPU/CUDA), and timestamp tracking.

    Attributes:
        settings: Application settings containing Whisper configuration.
        _model: Cached Whisper model instance (loaded on first access).

    Example:
        >>> settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        >>> transcriber = AudioTranscriber(settings=settings)
        >>> result = transcriber.transcribe_chunk(
        ...     video_path=Path("video.mp4"),
        ...     start_time=0.0,
        ...     end_time=30.0,
        ... )
    """

    def __init__(self, settings: Settings):
        """Initialize the AudioTranscriber.

        Args:
            settings: Application settings containing WHISPER_MODEL and
                     WHISPER_DEVICE configuration.
        """
        self.settings = settings
        self._model: Optional[whisper.Whisper] = None

        logger.info(
            f"AudioTranscriber initialized with model={settings.WHISPER_MODEL}, "
            f"device={settings.WHISPER_DEVICE}"
        )

    @property
    def model(self) -> whisper.Whisper:
        """Get or load the Whisper model (lazy loading with caching).

        The model is loaded on first access and cached for subsequent calls.
        This improves performance when transcribing multiple chunks.

        Returns:
            The loaded Whisper model instance.

        Raises:
            RuntimeError: If the model fails to load.
        """
        if self._model is None:
            try:
                logger.info(
                    f"Loading Whisper model: {self.settings.WHISPER_MODEL} "
                    f"on {self.settings.WHISPER_DEVICE}"
                )
                self._model = whisper.load_model(
                    self.settings.WHISPER_MODEL,
                    device=self.settings.WHISPER_DEVICE,
                )
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise RuntimeError(f"Failed to load Whisper model: {e}") from e

        return self._model

    def _load_audio(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
    ) -> np.ndarray:
        """Extract and prepare audio from a video file.

        This method extracts audio from the specified time range, converts
        to mono, and resamples to 16kHz for Whisper compatibility.

        Args:
            video_path: Path to the video file.
            start_time: Start time in seconds.
            end_time: End time in seconds.

        Returns:
            Audio array as 1D numpy array of float32, sampled at 16kHz.

        Raises:
            Exception: If the video file cannot be opened or processed.
        """
        try:
            logger.debug(
                f"Loading audio from {video_path}: {start_time}s - {end_time}s"
            )

            with VideoFileClip(str(video_path)) as video:
                # Extract subclip
                subclip = video.subclipped(start_time, end_time)

                if subclip.audio is None:
                    logger.warning(f"No audio track found in {video_path}")
                    return np.array([], dtype=np.float32)

                # Extract audio as array
                audio_array = subclip.audio.to_soundarray()
                fps = subclip.audio.fps

            # Convert to mono if stereo
            if audio_array.ndim > 1 and audio_array.shape[1] > 1:
                audio_array = audio_array.mean(axis=1)
            elif audio_array.ndim > 1:
                audio_array = audio_array.flatten()

            # Resample to 16kHz if necessary
            target_fps = 16000
            if fps != target_fps:
                # Simple resampling using linear interpolation
                original_length = len(audio_array)
                new_length = int(original_length * target_fps / fps)
                indices = np.linspace(0, original_length - 1, new_length)
                audio_array = np.interp(
                    indices, np.arange(original_length), audio_array
                )

            # Ensure float32 and normalize
            audio_array = audio_array.astype(np.float32)

            logger.debug(f"Audio extracted: {len(audio_array)} samples at 16kHz")
            return audio_array

        except Exception as e:
            logger.error(f"Failed to load audio from {video_path}: {e}")
            raise Exception(f"Failed to load audio from video file: {e}") from e

    def transcribe(
        self,
        audio: np.ndarray,
        chunk_start_time: float,
        chunk_end_time: float,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio array with timestamp tracking.

        Args:
            audio: Audio array as 1D numpy array of float32.
            chunk_start_time: Start time of this chunk in the video (seconds).
            chunk_end_time: End time of this chunk in the video (seconds).
            language: Optional language code (e.g., "en", "es"). Auto-detected if None.

        Returns:
            TranscriptionResult containing text, segments, and timing info.

        Raises:
            Exception: If transcription fails.
        """
        try:
            logger.debug(
                f"Transcribing audio chunk: {chunk_start_time}s - {chunk_end_time}s"
            )

            # Prepare transcription options
            options = {}
            if language:
                options["language"] = language

            # Run transcription
            result = self.model.transcribe(audio, **options)

            # Extract segments with absolute timestamps
            segments: List[TranscriptionSegment] = []
            for seg in result.get("segments", []):
                # Adjust timestamps to absolute video time
                absolute_start = seg["start"] + chunk_start_time
                absolute_end = seg["end"] + chunk_start_time

                segment = TranscriptionSegment(
                    text=seg["text"],
                    start_time=absolute_start,
                    end_time=absolute_end,
                )
                segments.append(segment)

            # Get full text
            text = result.get("text", "").strip()

            logger.debug(
                f"Transcription complete: {len(segments)} segments, {len(text)} chars"
            )

            return TranscriptionResult(
                text=text,
                segments=segments,
                chunk_start_time=chunk_start_time,
                chunk_end_time=chunk_end_time,
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise Exception(f"Transcription failed: {e}") from e

    def transcribe_chunk(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe a specific time range from a video file.

        This is a convenience method that extracts audio and transcribes
        in one call.

        Args:
            video_path: Path to the video file.
            start_time: Start time in seconds.
            end_time: End time in seconds.
            language: Optional language code (e.g., "en", "es"). Auto-detected if None.

        Returns:
            TranscriptionResult containing text, segments, and timing info.

        Raises:
            Exception: If audio extraction or transcription fails.
        """
        logger.info(
            f"Transcribing chunk from {video_path}: {start_time}s - {end_time}s"
        )

        # Load audio from video
        audio = self._load_audio(video_path, start_time, end_time)

        if len(audio) == 0:
            # Return empty result if no audio
            return TranscriptionResult(
                text="",
                segments=[],
                chunk_start_time=start_time,
                chunk_end_time=end_time,
            )

        # Transcribe the audio
        return self.transcribe(
            audio=audio,
            chunk_start_time=start_time,
            chunk_end_time=end_time,
            language=language,
        )

    def batch_transcribe(
        self,
        video_path: Path,
        chunks: List[dict],
        language: Optional[str] = None,
    ) -> List[TranscriptionResult]:
        """Transcribe multiple chunks from a video file.

        Args:
            video_path: Path to the video file.
            chunks: List of chunk dictionaries with "start_time" and "end_time" keys.
            language: Optional language code (e.g., "en", "es"). Auto-detected if None.

        Returns:
            List of TranscriptionResult objects, one per chunk.
        """
        if not chunks:
            logger.info("No chunks to transcribe")
            return []

        logger.info(f"Batch transcribing {len(chunks)} chunks from {video_path}")

        results: List[TranscriptionResult] = []
        for i, chunk in enumerate(chunks):
            try:
                result = self.transcribe_chunk(
                    video_path=video_path,
                    start_time=chunk["start_time"],
                    end_time=chunk["end_time"],
                    language=language,
                )
                results.append(result)
                logger.debug(f"Transcribed chunk {i + 1}/{len(chunks)}")
            except Exception as e:
                logger.error(f"Failed to transcribe chunk {i + 1}: {e}")
                # Add empty result for failed chunk
                results.append(
                    TranscriptionResult(
                        text="",
                        segments=[],
                        chunk_start_time=chunk["start_time"],
                        chunk_end_time=chunk["end_time"],
                    )
                )

        logger.info(f"Batch transcription complete: {len(results)} results")
        return results
