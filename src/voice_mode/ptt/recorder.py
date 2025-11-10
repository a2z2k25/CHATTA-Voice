"""
PTT Audio Recorder.

This module provides audio recording functionality specifically for
Push-to-Talk, allowing manual start/stop control without silence detection.
"""

import asyncio
import time
import numpy as np
from typing import Optional, Tuple
from threading import Event, Lock
import queue

from voice_mode import config
from .logging import get_ptt_logger, PTTLogger

# Try to import sounddevice
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class PTTRecorder:
    """Audio recorder for Push-to-Talk.

    Records audio on demand without automatic silence detection.
    Designed to work with keyboard-controlled start/stop.

    Example:
        >>> recorder = PTTRecorder()
        >>> recorder.start()
        >>> # ... user speaks while holding key ...
        >>> audio_data = recorder.stop()
        >>> print(f"Recorded {len(audio_data)} samples")
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = 'int16',
        logger: Optional[PTTLogger] = None
    ):
        """Initialize PTT recorder.

        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 = mono)
            dtype: Audio data type (default: 'int16')
            logger: PTTLogger instance for logging
        """
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError(
                "sounddevice not available - cannot record audio. "
                "Install with: pip install sounddevice"
            )

        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self._logger = logger or get_ptt_logger()

        # Recording state
        self._is_recording = False
        self._audio_chunks: list = []
        self._stream: Optional[sd.InputStream] = None
        self._stop_event = Event()
        self._lock = Lock()

        # Timing
        self._start_time: Optional[float] = None
        self._duration: float = 0.0

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        if self._is_recording and self._start_time:
            return time.time() - self._start_time
        return self._duration

    def start(self) -> bool:
        """Start recording audio.

        Returns:
            True if started successfully, False if already recording

        Example:
            >>> recorder = PTTRecorder()
            >>> recorder.start()
            True
            >>> recorder.is_recording
            True
        """
        with self._lock:
            if self._is_recording:
                self._logger.log_event("recording_start_skipped", {
                    "reason": "already_recording"
                })
                return False

            try:
                # Clear previous recording
                self._audio_chunks = []
                self._stop_event.clear()
                self._start_time = time.time()
                self._duration = 0.0

                # Create and start audio stream
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    callback=self._audio_callback
                )
                self._stream.start()

                self._is_recording = True

                self._logger.log_event("recording_started", {
                    "sample_rate": self.sample_rate,
                    "channels": self.channels,
                    "dtype": self.dtype
                })

                return True

            except Exception as e:
                self._logger.log_error(e, {
                    "operation": "start_recording",
                    "sample_rate": self.sample_rate,
                    "channels": self.channels
                })
                return False

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data.

        Returns:
            Numpy array of recorded audio samples, or None if not recording

        Example:
            >>> recorder = PTTRecorder()
            >>> recorder.start()
            >>> time.sleep(2)  # Record for 2 seconds
            >>> audio = recorder.stop()
            >>> print(f"Recorded {len(audio)} samples")
        """
        with self._lock:
            if not self._is_recording:
                self._logger.log_event("recording_stop_skipped", {
                    "reason": "not_recording"
                })
                return None

            try:
                # Stop the stream
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None

                self._is_recording = False
                self._stop_event.set()

                # Calculate final duration
                if self._start_time:
                    self._duration = time.time() - self._start_time
                    self._start_time = None

                # Combine audio chunks
                if not self._audio_chunks:
                    self._logger.log_event("recording_stopped", {
                        "duration_seconds": self._duration,
                        "samples": 0,
                        "warning": "no_audio_captured"
                    })
                    return np.array([], dtype=self.dtype)

                audio_data = np.concatenate(self._audio_chunks, axis=0)

                self._logger.log_event("recording_stopped", {
                    "duration_seconds": self._duration,
                    "samples": len(audio_data),
                    "size_bytes": audio_data.nbytes
                })

                return audio_data

            except Exception as e:
                self._logger.log_error(e, {
                    "operation": "stop_recording",
                    "chunks": len(self._audio_chunks)
                })
                return None

    def cancel(self) -> None:
        """Cancel recording without returning audio data.

        Example:
            >>> recorder = PTTRecorder()
            >>> recorder.start()
            >>> # User presses escape
            >>> recorder.cancel()
        """
        with self._lock:
            if not self._is_recording:
                return

            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None

                self._is_recording = False
                self._stop_event.set()

                # Clear audio data
                num_chunks = len(self._audio_chunks)
                self._audio_chunks = []

                if self._start_time:
                    self._duration = time.time() - self._start_time
                    self._start_time = None

                self._logger.log_event("recording_cancelled", {
                    "duration_seconds": self._duration,
                    "chunks_discarded": num_chunks
                })

            except Exception as e:
                self._logger.log_error(e, {
                    "operation": "cancel_recording"
                })

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream (called by sounddevice).

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Timing information
            status: Stream status
        """
        if status:
            self._logger.log_event("audio_stream_status", {
                "status": str(status),
                "frames": frames
            })

        if self._is_recording:
            # Store audio chunk
            self._audio_chunks.append(indata.copy())


class AsyncPTTRecorder:
    """Async wrapper around PTTRecorder for use with asyncio.

    Provides async methods for start/stop/cancel operations.

    Example:
        >>> recorder = AsyncPTTRecorder()
        >>> await recorder.start()
        >>> audio_data = await recorder.stop()
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = 'int16',
        logger: Optional[PTTLogger] = None
    ):
        """Initialize async recorder.

        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            dtype: Audio data type
            logger: PTTLogger instance
        """
        self._recorder = PTTRecorder(
            sample_rate=sample_rate,
            channels=channels,
            dtype=dtype,
            logger=logger
        )

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recorder.is_recording

    @property
    def duration(self) -> float:
        """Get current recording duration."""
        return self._recorder.duration

    async def start(self) -> bool:
        """Start recording (async).

        Returns:
            True if started successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._recorder.start)

    async def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data (async).

        Returns:
            Numpy array of audio samples
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._recorder.stop)

    async def cancel(self) -> None:
        """Cancel recording (async)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._recorder.cancel)


def create_ptt_recorder(
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    logger: Optional[PTTLogger] = None
) -> PTTRecorder:
    """Factory function to create PTT recorder.

    Args:
        sample_rate: Audio sample rate (default from config)
        channels: Number of channels (default: 1)
        logger: PTTLogger instance

    Returns:
        Configured PTTRecorder instance

    Example:
        >>> recorder = create_ptt_recorder()
        >>> recorder.start()
    """
    return PTTRecorder(
        sample_rate=sample_rate or 16000,
        channels=channels or 1,
        logger=logger
    )


def create_async_ptt_recorder(
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    logger: Optional[PTTLogger] = None
) -> AsyncPTTRecorder:
    """Factory function to create async PTT recorder.

    Args:
        sample_rate: Audio sample rate (default from config)
        channels: Number of channels (default: 1)
        logger: PTTLogger instance

    Returns:
        Configured AsyncPTTRecorder instance

    Example:
        >>> recorder = create_async_ptt_recorder()
        >>> await recorder.start()
    """
    return AsyncPTTRecorder(
        sample_rate=sample_rate or 16000,
        channels=channels or 1,
        logger=logger
    )
