"""Unit tests for the AudioTranscriber service.

This module tests the AudioTranscriber functionality including:
- Whisper model loading based on Settings
- Transcription of video chunks with timestamps
- Model caching for performance
- Device selection (CPU/CUDA)
- Error handling for model loading failures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from typing import Generator, List
import numpy as np

from hollywood_script_generator.services.audio_transcriber import (
    AudioTranscriber,
    TranscriptionSegment,
    TranscriptionResult,
)
from hollywood_script_generator.core.config import Settings


class TestTranscriptionSegment:
    """Tests for the TranscriptionSegment dataclass."""

    def test_segment_creation(self):
        """Verify segment can be created with all attributes."""
        segment = TranscriptionSegment(
            text="Hello world",
            start_time=0.0,
            end_time=2.5,
        )

        assert segment.text == "Hello world"
        assert segment.start_time == 0.0
        assert segment.end_time == 2.5

    def test_segment_with_whitespace_stripping(self):
        """Verify segment text is stripped of whitespace."""
        segment = TranscriptionSegment(
            text="  Hello world  ",
            start_time=1.0,
            end_time=3.0,
        )

        assert segment.text == "Hello world"


class TestTranscriptionResult:
    """Tests for the TranscriptionResult dataclass."""

    def test_result_creation_empty(self):
        """Verify result can be created with no segments."""
        result = TranscriptionResult(
            text="",
            segments=[],
            chunk_start_time=0.0,
            chunk_end_time=30.0,
        )

        assert result.text == ""
        assert len(result.segments) == 0
        assert result.chunk_start_time == 0.0
        assert result.chunk_end_time == 30.0

    def test_result_creation_with_segments(self):
        """Verify result can be created with multiple segments."""
        segments = [
            TranscriptionSegment(text="Hello", start_time=0.0, end_time=1.0),
            TranscriptionSegment(text="world", start_time=1.5, end_time=2.5),
        ]

        result = TranscriptionResult(
            text="Hello world",
            segments=segments,
            chunk_start_time=0.0,
            chunk_end_time=30.0,
        )

        assert result.text == "Hello world"
        assert len(result.segments) == 2


class TestAudioTranscriberInitialization:
    """Tests for AudioTranscriber initialization."""

    def test_transcriber_can_be_instantiated(self):
        """Verify transcriber can be created with Settings."""
        settings = Settings(
            WHISPER_MODEL="base",
            WHISPER_DEVICE="cpu",
        )

        transcriber = AudioTranscriber(settings=settings)

        assert transcriber is not None
        assert transcriber.settings == settings
        assert transcriber._model is None  # Model not loaded yet

    def test_transcriber_uses_settings_values(self):
        """Verify transcriber uses configuration from Settings."""
        settings = Settings(
            WHISPER_MODEL="small",
            WHISPER_DEVICE="cuda",
        )

        transcriber = AudioTranscriber(settings=settings)

        assert transcriber.settings.WHISPER_MODEL == "small"
        assert transcriber.settings.WHISPER_DEVICE == "cuda"

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_model_loading_on_first_access(self, mock_whisper):
        """Verify model is loaded lazily on first access."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(
            WHISPER_MODEL="base",
            WHISPER_DEVICE="cpu",
        )

        transcriber = AudioTranscriber(settings=settings)

        # Model should not be loaded yet
        assert transcriber._model is None

        # Access model property to trigger loading
        model = transcriber.model

        # Now model should be loaded
        assert model is mock_model
        mock_whisper.load_model.assert_called_once_with("base", device="cpu")

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_model_caching(self, mock_whisper):
        """Verify model is cached after first load."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(
            WHISPER_MODEL="base",
            WHISPER_DEVICE="cpu",
        )

        transcriber = AudioTranscriber(settings=settings)

        # Access model twice
        model1 = transcriber.model
        model2 = transcriber.model

        # Should return same instance
        assert model1 is model2

        # Should only load once
        mock_whisper.load_model.assert_called_once()


class TestAudioTranscriberModelLoading:
    """Tests for Whisper model loading."""

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_load_model_tiny(self, mock_whisper):
        """Verify tiny model can be loaded."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="tiny", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        _ = transcriber.model

        mock_whisper.load_model.assert_called_once_with("tiny", device="cpu")

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_load_model_base(self, mock_whisper):
        """Verify base model can be loaded."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        _ = transcriber.model

        mock_whisper.load_model.assert_called_once_with("base", device="cpu")

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_load_model_cuda_device(self, mock_whisper):
        """Verify CUDA device selection works."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cuda")
        transcriber = AudioTranscriber(settings=settings)

        _ = transcriber.model

        mock_whisper.load_model.assert_called_once_with("base", device="cuda")

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_model_loading_error(self, mock_whisper):
        """Verify error handling when model loading fails."""
        mock_whisper.load_model.side_effect = RuntimeError("Model not found")

        # Use a valid model name since Settings validates it
        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        with pytest.raises(RuntimeError) as exc_info:
            _ = transcriber.model

        assert (
            "model" in str(exc_info.value).lower()
            or "not found" in str(exc_info.value).lower()
        )


class TestAudioTranscriberTranscribe:
    """Tests for transcription functionality."""

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_audio_array(self, mock_whisper):
        """Verify transcription of audio array."""
        # Setup mock model and result
        mock_model = MagicMock()
        mock_result = {
            "text": "Hello world",
            "segments": [
                {"text": "Hello", "start": 0.0, "end": 1.0},
                {"text": "world", "start": 1.2, "end": 2.0},
            ],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        # Create dummy audio array
        audio = np.zeros(16000, dtype=np.float32)  # 1 second at 16kHz

        result = transcriber.transcribe(
            audio=audio,
            chunk_start_time=0.0,
            chunk_end_time=30.0,
        )

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Hello"
        assert result.segments[0].start_time == 0.0
        assert result.segments[1].text == "world"
        assert result.segments[1].end_time == 2.0

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_returns_segments_with_absolute_timestamps(self, mock_whisper):
        """Verify timestamps are adjusted to absolute video time."""
        mock_model = MagicMock()
        mock_result = {
            "text": "Test transcript",
            "segments": [
                {"text": "Test", "start": 0.0, "end": 1.0},
                {"text": "transcript", "start": 1.5, "end": 2.5},
            ],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = np.zeros(16000, dtype=np.float32)
        chunk_start = 60.0  # Chunk starts at 60 seconds into video

        result = transcriber.transcribe(
            audio=audio,
            chunk_start_time=chunk_start,
            chunk_end_time=chunk_start + 30.0,
        )

        # Timestamps should be offset by chunk_start_time
        assert result.segments[0].start_time == 60.0
        assert result.segments[0].end_time == 61.0
        assert result.segments[1].start_time == 61.5
        assert result.segments[1].end_time == 62.5

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_empty_audio(self, mock_whisper):
        """Verify handling of empty or silent audio."""
        mock_model = MagicMock()
        mock_result = {"text": "", "segments": []}
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = np.zeros(16000, dtype=np.float32)

        result = transcriber.transcribe(
            audio=audio,
            chunk_start_time=0.0,
            chunk_end_time=30.0,
        )

        assert result.text == ""
        assert len(result.segments) == 0

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_with_language_option(self, mock_whisper):
        """Verify language option is passed to whisper."""
        mock_model = MagicMock()
        mock_result = {"text": "Hola mundo", "segments": []}
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = np.zeros(16000, dtype=np.float32)

        result = transcriber.transcribe(
            audio=audio,
            chunk_start_time=0.0,
            chunk_end_time=30.0,
            language="es",
        )

        # Verify language was passed to transcribe
        call_kwargs = mock_model.transcribe.call_args.kwargs
        assert call_kwargs.get("language") == "es"


class TestAudioTranscriberTranscribeChunk:
    """Tests for transcribe_chunk convenience method."""

    @patch(
        "hollywood_script_generator.services.audio_transcriber.AudioTranscriber._load_audio"
    )
    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_chunk_loads_audio_and_transcribes(
        self, mock_whisper, mock_load_audio
    ):
        """Verify transcribe_chunk loads audio from file and transcribes."""
        # Setup mocks
        mock_model = MagicMock()
        mock_result = {
            "text": "Chunk transcript",
            "segments": [{"text": "Chunk", "start": 0.0, "end": 1.0}],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        mock_audio = np.zeros(480000, dtype=np.float32)  # 30 seconds at 16kHz
        mock_load_audio.return_value = mock_audio

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        result = transcriber.transcribe_chunk(
            video_path=Path("/path/to/video.mp4"),
            start_time=0.0,
            end_time=30.0,
        )

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Chunk transcript"
        mock_load_audio.assert_called_once_with(Path("/path/to/video.mp4"), 0.0, 30.0)

    @patch(
        "hollywood_script_generator.services.audio_transcriber.AudioTranscriber._load_audio"
    )
    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_chunk_with_mid_video_timestamp(
        self, mock_whisper, mock_load_audio
    ):
        """Verify timestamps are correct for mid-video chunks."""
        mock_model = MagicMock()
        mock_result = {
            "text": "Middle chunk",
            "segments": [{"text": "Middle", "start": 0.0, "end": 1.0}],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        mock_audio = np.zeros(480000, dtype=np.float32)
        mock_load_audio.return_value = mock_audio

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        result = transcriber.transcribe_chunk(
            video_path=Path("/path/to/video.mp4"),
            start_time=120.0,
            end_time=150.0,
        )

        # Timestamps should be offset by chunk start time
        assert result.chunk_start_time == 120.0
        assert result.chunk_end_time == 150.0
        assert result.segments[0].start_time == 120.0


class TestAudioTranscriberLoadAudio:
    """Tests for _load_audio helper method."""

    @patch("hollywood_script_generator.services.audio_transcriber.VideoFileClip")
    def test_load_audio_extracts_audio(self, mock_video_clip_class):
        """Verify audio extraction from video file."""
        # Setup mock video clip chain: VideoFileClip -> subclipped -> audio
        mock_subclip = MagicMock()
        mock_audio = MagicMock()
        mock_audio.to_soundarray.return_value = np.array([[0.1], [0.2], [0.3]])
        mock_subclip.audio = mock_audio
        mock_subclip.fps = 3  # 3 samples per second
        
        mock_clip = MagicMock()
        mock_clip.subclipped.return_value = mock_subclip
        
        # Context manager returns mock_clip, which gives subclip when subclipped
        mock_video_clip_class.return_value.__enter__.return_value = mock_clip

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = transcriber._load_audio(
            video_path=Path("/path/to/video.mp4"),
            start_time=0.0,
            end_time=1.0,
        )

        assert isinstance(audio, np.ndarray)
        mock_video_clip_class.assert_called_once_with("/path/to/video.mp4")
        mock_clip.subclipped.assert_called_once_with(0.0, 1.0)

    @patch("hollywood_script_generator.services.audio_transcriber.VideoFileClip")
    def test_load_audio_handles_mono_conversion(self, mock_video_clip_class):
        """Verify stereo audio is converted to mono."""
        # Setup mock for stereo audio
        mock_subclip = MagicMock()
        mock_audio = MagicMock()
        # Stereo audio (2 channels)
        mock_audio.to_soundarray.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_subclip.audio = mock_audio
        mock_subclip.fps = 2
        
        mock_clip = MagicMock()
        mock_clip.subclipped.return_value = mock_subclip
        
        mock_video_clip_class.return_value.__enter__.return_value = mock_clip

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = transcriber._load_audio(
            video_path=Path("/path/to/video.mp4"),
            start_time=0.0,
            end_time=1.0,
        )

        # Should be mono (1D array)
        assert audio.ndim == 1
    @patch("hollywood_script_generator.services.audio_transcriber.VideoFileClip")
    def test_load_audio_resampling(self, mock_video_clip_class):
        """Verify audio is resampled to 16kHz."""
        # Setup mock for 48kHz audio
        mock_subclip = MagicMock()
        mock_audio = MagicMock()
        # 48kHz audio (3 samples for 1/16000 second at 48kHz)
        mock_audio.to_soundarray.return_value = np.array([[0.1], [0.2], [0.3]])
        mock_subclip.audio = mock_audio
        mock_subclip.fps = 48000  # 48kHz
        
        mock_clip = MagicMock()
        mock_clip.subclipped.return_value = mock_subclip
        
        mock_video_clip_class.return_value.__enter__.return_value = mock_clip

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = transcriber._load_audio(
            video_path=Path("/path/to/video.mp4"),
            start_time=0.0,
            end_time=1.0,
        )

        # Should be resampled (fewer samples than original)
        assert len(audio) < 48000

class TestAudioTranscriberBatchTranscribe:
    """Tests for batch transcription."""

    @patch(
        "hollywood_script_generator.services.audio_transcriber.AudioTranscriber.transcribe_chunk"
    )
    def test_batch_transcribe_multiple_chunks(self, mock_transcribe_chunk):
        """Verify batch transcription processes multiple chunks."""
        # Setup mock results for each chunk
        mock_transcribe_chunk.side_effect = [
            TranscriptionResult(
                text="Chunk 1",
                segments=[TranscriptionSegment("Chunk 1", 0.0, 30.0)],
                chunk_start_time=0.0,
                chunk_end_time=30.0,
            ),
            TranscriptionResult(
                text="Chunk 2",
                segments=[TranscriptionSegment("Chunk 2", 30.0, 60.0)],
                chunk_start_time=30.0,
                chunk_end_time=60.0,
            ),
            TranscriptionResult(
                text="Chunk 3",
                segments=[TranscriptionSegment("Chunk 3", 60.0, 90.0)],
                chunk_start_time=60.0,
                chunk_end_time=90.0,
            ),
        ]

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        chunks = [
            {"start_time": 0.0, "end_time": 30.0},
            {"start_time": 30.0, "end_time": 60.0},
            {"start_time": 60.0, "end_time": 90.0},
        ]

        results = transcriber.batch_transcribe(
            video_path=Path("/path/to/video.mp4"),
            chunks=chunks,
        )

        assert len(results) == 3
        assert results[0].text == "Chunk 1"
        assert results[1].text == "Chunk 2"
        assert results[2].text == "Chunk 3"

    @patch(
        "hollywood_script_generator.services.audio_transcriber.AudioTranscriber.transcribe_chunk"
    )
    def test_batch_transcribe_empty_chunks(self, mock_transcribe_chunk):
        """Verify batch transcription handles empty chunk list."""
        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        results = transcriber.batch_transcribe(
            video_path=Path("/path/to/video.mp4"),
            chunks=[],
        )

        assert len(results) == 0
        mock_transcribe_chunk.assert_not_called()

    @patch(
        "hollywood_script_generator.services.audio_transcriber.AudioTranscriber.transcribe_chunk"
    )
    def test_batch_transcribe_single_chunk(self, mock_transcribe_chunk):
        """Verify batch transcription handles single chunk."""
        mock_transcribe_chunk.return_value = TranscriptionResult(
            text="Single chunk",
            segments=[TranscriptionSegment("Single chunk", 0.0, 30.0)],
            chunk_start_time=0.0,
            chunk_end_time=30.0,
        )

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        results = transcriber.batch_transcribe(
            video_path=Path("/path/to/video.mp4"),
            chunks=[{"start_time": 0.0, "end_time": 30.0}],
        )

        assert len(results) == 1
        assert results[0].text == "Single chunk"


class TestAudioTranscriberErrorHandling:
    """Tests for error handling."""

    @patch("hollywood_script_generator.services.audio_transcriber.whisper")
    def test_transcribe_handles_whisper_error(self, mock_whisper):
        """Verify graceful handling of transcription errors."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Transcription failed")
        mock_whisper.load_model.return_value = mock_model

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        audio = np.zeros(16000, dtype=np.float32)

        with pytest.raises(Exception) as exc_info:
            transcriber.transcribe(
                audio=audio,
                chunk_start_time=0.0,
                chunk_end_time=30.0,
            )

        assert (
            "transcription" in str(exc_info.value).lower()
            or "failed" in str(exc_info.value).lower()
        )

    @patch("hollywood_script_generator.services.audio_transcriber.VideoFileClip")
    def test_load_audio_handles_file_error(self, mock_video_clip_class):
        """Verify graceful handling of video file errors."""
        mock_video_clip_class.side_effect = Exception("Cannot open video")

        settings = Settings(WHISPER_MODEL="base", WHISPER_DEVICE="cpu")
        transcriber = AudioTranscriber(settings=settings)

        with pytest.raises(Exception) as exc_info:
            transcriber._load_audio(
                video_path=Path("/invalid/path.mp4"),
                start_time=0.0,
                end_time=30.0,
            )

        assert (
            "video" in str(exc_info.value).lower()
            or "file" in str(exc_info.value).lower()
        )


class TestAudioTranscriberTypeAnnotations:
    """Tests for type annotations and signatures."""

    def test_transcribe_has_type_hints(self):
        """Verify transcribe method has proper type annotations."""
        import inspect

        settings = Settings()
        transcriber = AudioTranscriber(settings=settings)

        sig = inspect.signature(transcriber.transcribe)
        params = sig.parameters

        # Check required parameters
        assert "audio" in params
        assert "chunk_start_time" in params
        assert "chunk_end_time" in params

        # Check optional parameters
        assert "language" in params

        # Check return type
        assert sig.return_annotation.__name__ == "TranscriptionResult"

    def test_transcribe_chunk_has_type_hints(self):
        """Verify transcribe_chunk method has proper type annotations."""
        import inspect

        settings = Settings()
        transcriber = AudioTranscriber(settings=settings)

        sig = inspect.signature(transcriber.transcribe_chunk)
        params = sig.parameters

        # Check parameters
        assert "video_path" in params
        assert "start_time" in params
        assert "end_time" in params

        # Check return type
        assert sig.return_annotation.__name__ == "TranscriptionResult"
