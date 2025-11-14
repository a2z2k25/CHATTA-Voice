"""
Tests for PTT Audio Recorder.

This module tests the audio recording functionality for Push-to-Talk,
including synchronous and asynchronous recorders.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from voice_mode.ptt import (
    PTTRecorder,
    AsyncPTTRecorder,
    create_ptt_recorder,
    create_async_ptt_recorder
)


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module to prevent actual audio recording"""
    with patch('voice_mode.ptt.recorder.sd') as mock_sd:
        # Create a mock stream
        mock_stream = MagicMock()
        mock_stream.start.return_value = None
        mock_stream.stop.return_value = None
        mock_stream.close.return_value = None

        # Mock InputStream to return our mock stream
        mock_sd.InputStream.return_value = mock_stream

        yield mock_sd


@pytest.fixture
def mock_sounddevice_unavailable():
    """Mock sounddevice as unavailable"""
    with patch('voice_mode.ptt.recorder.SOUNDDEVICE_AVAILABLE', False):
        yield


class TestPTTRecorder:
    """Tests for PTTRecorder class"""

    def test_initialization(self, mock_sounddevice):
        """Test recorder initializes with correct defaults"""
        recorder = PTTRecorder()

        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.dtype == 'int16'
        assert recorder.is_recording is False
        assert recorder.duration == 0.0

    def test_initialization_with_custom_params(self, mock_sounddevice, ptt_logger):
        """Test recorder with custom parameters"""
        recorder = PTTRecorder(
            sample_rate=48000,
            channels=2,
            dtype='float32',
            logger=ptt_logger
        )

        assert recorder.sample_rate == 48000
        assert recorder.channels == 2
        assert recorder.dtype == 'float32'
        assert recorder._logger == ptt_logger

    def test_initialization_without_sounddevice(self, mock_sounddevice_unavailable):
        """Test initialization fails when sounddevice unavailable"""
        with pytest.raises(RuntimeError, match="sounddevice not available"):
            PTTRecorder()

    def test_start_recording(self, mock_sounddevice):
        """Test starting audio recording"""
        recorder = PTTRecorder()

        result = recorder.start()

        assert result is True
        assert recorder.is_recording is True
        mock_sounddevice.InputStream.assert_called_once()

        # Verify stream was started
        stream = mock_sounddevice.InputStream.return_value
        stream.start.assert_called_once()

    def test_start_when_already_recording(self, mock_sounddevice, ptt_logger):
        """Test starting when already recording returns False"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Try to start again
        result = recorder.start()

        assert result is False
        # Should only have created one stream
        assert mock_sounddevice.InputStream.call_count == 1

    def test_start_recording_error_handling(self, mock_sounddevice, ptt_logger):
        """Test error handling during start"""
        mock_sounddevice.InputStream.side_effect = Exception("Audio device error")

        recorder = PTTRecorder(logger=ptt_logger)
        result = recorder.start()

        assert result is False
        assert recorder.is_recording is False

        # Check error was logged
        errors = [e for e in ptt_logger.events if e.event_type == "error"]
        assert len(errors) == 1

    def test_stop_recording(self, mock_sounddevice):
        """Test stopping audio recording"""
        recorder = PTTRecorder()
        recorder.start()

        # Simulate some audio data
        recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16'),
            np.array([4, 5, 6], dtype='int16')
        ]

        audio_data = recorder.stop()

        assert recorder.is_recording is False
        assert audio_data is not None
        assert len(audio_data) == 6
        np.testing.assert_array_equal(audio_data, [1, 2, 3, 4, 5, 6])

        # Verify stream was stopped and closed
        stream = mock_sounddevice.InputStream.return_value
        stream.stop.assert_called_once()
        stream.close.assert_called_once()

    def test_stop_when_not_recording(self, mock_sounddevice, ptt_logger):
        """Test stopping when not recording returns None"""
        recorder = PTTRecorder(logger=ptt_logger)

        result = recorder.stop()

        assert result is None

    def test_stop_with_no_audio_data(self, mock_sounddevice, ptt_logger):
        """Test stopping with no audio data returns empty array"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # No audio chunks added
        audio_data = recorder.stop()

        assert audio_data is not None
        assert len(audio_data) == 0

    def test_stop_recording_error_handling(self, mock_sounddevice, ptt_logger):
        """Test error handling during stop"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Make stop() raise an error
        stream = mock_sounddevice.InputStream.return_value
        stream.stop.side_effect = Exception("Stop failed")

        result = recorder.stop()

        assert result is None
        # Check error was logged
        errors = [e for e in ptt_logger.events if e.event_type == "error"]
        assert len(errors) == 1

    def test_cancel_recording(self, mock_sounddevice, ptt_logger):
        """Test cancelling audio recording"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Simulate some audio data
        recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16')
        ]

        recorder.cancel()

        assert recorder.is_recording is False
        assert len(recorder._audio_chunks) == 0

        # Verify stream was stopped and closed
        stream = mock_sounddevice.InputStream.return_value
        stream.stop.assert_called_once()
        stream.close.assert_called_once()

        # Check cancellation was logged
        cancel_events = [
            e for e in ptt_logger.events
            if e.event_type == "recording_cancelled"
        ]
        assert len(cancel_events) == 1

    def test_cancel_when_not_recording(self, mock_sounddevice):
        """Test cancelling when not recording does nothing"""
        recorder = PTTRecorder()

        # Should not raise
        recorder.cancel()

        assert recorder.is_recording is False

    def test_cancel_error_handling(self, mock_sounddevice, ptt_logger):
        """Test error handling during cancel"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Make close() raise an error
        stream = mock_sounddevice.InputStream.return_value
        stream.close.side_effect = Exception("Close failed")

        # Should not raise
        recorder.cancel()

        # Check error was logged
        errors = [e for e in ptt_logger.events if e.event_type == "error"]
        assert len(errors) == 1

    def test_audio_callback(self, mock_sounddevice, ptt_logger):
        """Test audio callback stores data"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Simulate audio callback
        audio_data = np.array([1, 2, 3, 4, 5], dtype='int16')
        recorder._audio_callback(audio_data, 5, None, None)

        assert len(recorder._audio_chunks) == 1
        np.testing.assert_array_equal(recorder._audio_chunks[0], audio_data)

    def test_audio_callback_with_status(self, mock_sounddevice, ptt_logger):
        """Test audio callback logs status"""
        recorder = PTTRecorder(logger=ptt_logger)
        recorder.start()

        # Simulate audio callback with status
        audio_data = np.array([1, 2, 3], dtype='int16')
        recorder._audio_callback(audio_data, 3, None, "input overflow")

        # Check status was logged
        status_events = [
            e for e in ptt_logger.events
            if e.event_type == "audio_stream_status"
        ]
        assert len(status_events) == 1
        assert "input overflow" in str(status_events[0].data["status"])

    def test_duration_tracking(self, mock_sounddevice):
        """Test recording duration is tracked"""
        import time

        recorder = PTTRecorder()
        recorder.start()

        # Wait a bit
        time.sleep(0.01)

        # Duration should be tracked while recording
        assert recorder.duration > 0

        # Stop and check final duration
        recorder.stop()
        final_duration = recorder.duration

        assert final_duration > 0

    def test_duration_when_not_recording(self, mock_sounddevice):
        """Test duration returns 0 when not recording"""
        recorder = PTTRecorder()

        assert recorder.duration == 0.0


class TestAsyncPTTRecorder:
    """Tests for AsyncPTTRecorder class"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_sounddevice):
        """Test async recorder initializes correctly"""
        recorder = AsyncPTTRecorder()

        assert recorder._recorder is not None
        assert recorder.is_recording is False

    @pytest.mark.asyncio
    async def test_async_start(self, mock_sounddevice):
        """Test async start method"""
        recorder = AsyncPTTRecorder()

        result = await recorder.start()

        assert result is True
        assert recorder.is_recording is True

    @pytest.mark.asyncio
    async def test_async_stop(self, mock_sounddevice):
        """Test async stop method"""
        recorder = AsyncPTTRecorder()
        await recorder.start()

        # Add some audio data
        recorder._recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16')
        ]

        audio_data = await recorder.stop()

        assert audio_data is not None
        assert len(audio_data) == 3

    @pytest.mark.asyncio
    async def test_async_cancel(self, mock_sounddevice):
        """Test async cancel method"""
        recorder = AsyncPTTRecorder()
        await recorder.start()

        # Should not raise
        await recorder.cancel()

        assert recorder.is_recording is False

    @pytest.mark.asyncio
    async def test_duration_property(self, mock_sounddevice):
        """Test duration property works through async wrapper"""
        recorder = AsyncPTTRecorder()

        assert recorder.duration == 0.0

        await recorder.start()

        # Duration should be available
        assert recorder.duration >= 0.0


class TestRecorderFactories:
    """Tests for recorder factory functions"""

    def test_create_ptt_recorder(self, mock_sounddevice):
        """Test factory creates valid recorder"""
        recorder = create_ptt_recorder()

        assert isinstance(recorder, PTTRecorder)
        assert recorder.sample_rate == 16000

    def test_create_ptt_recorder_with_params(self, mock_sounddevice, ptt_logger):
        """Test factory with custom parameters"""
        recorder = create_ptt_recorder(
            sample_rate=48000,
            channels=2,
            logger=ptt_logger
        )

        assert recorder.sample_rate == 48000
        assert recorder.channels == 2
        assert recorder._logger == ptt_logger

    def test_create_async_ptt_recorder(self, mock_sounddevice):
        """Test async factory creates valid recorder"""
        recorder = create_async_ptt_recorder()

        assert isinstance(recorder, AsyncPTTRecorder)
        assert recorder._recorder.sample_rate == 16000

    def test_create_async_ptt_recorder_with_params(self, mock_sounddevice, ptt_logger):
        """Test async factory with custom parameters"""
        recorder = create_async_ptt_recorder(
            sample_rate=48000,
            channels=2,
            logger=ptt_logger
        )

        assert recorder._recorder.sample_rate == 48000
        assert recorder._recorder.channels == 2


class TestRecorderIntegration:
    """Integration tests for recorder"""

    @pytest.mark.asyncio
    async def test_full_recording_cycle(self, mock_sounddevice):
        """Test complete recording cycle"""
        recorder = AsyncPTTRecorder()

        # Start recording
        assert await recorder.start() is True
        assert recorder.is_recording is True

        # Simulate audio data
        recorder._recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16'),
            np.array([4, 5, 6], dtype='int16')
        ]

        # Stop and get data
        audio_data = await recorder.stop()
        assert recorder.is_recording is False
        assert audio_data is not None
        assert len(audio_data) == 6

    @pytest.mark.asyncio
    async def test_cancel_discards_data(self, mock_sounddevice):
        """Test that cancel discards recorded data"""
        recorder = AsyncPTTRecorder()

        await recorder.start()

        # Add audio data
        recorder._recorder._audio_chunks = [
            np.array([1, 2, 3, 4, 5], dtype='int16')
        ]

        # Cancel
        await recorder.cancel()

        # Data should be discarded
        assert len(recorder._recorder._audio_chunks) == 0
        assert recorder.is_recording is False

    @pytest.mark.asyncio
    async def test_multiple_recording_sessions(self, mock_sounddevice):
        """Test multiple recording sessions"""
        recorder = AsyncPTTRecorder()

        # First session
        await recorder.start()
        recorder._recorder._audio_chunks = [np.array([1, 2, 3], dtype='int16')]
        data1 = await recorder.stop()

        # Second session
        await recorder.start()
        recorder._recorder._audio_chunks = [np.array([4, 5, 6], dtype='int16')]
        data2 = await recorder.stop()

        # Both sessions should work independently
        assert len(data1) == 3
        assert len(data2) == 3
        np.testing.assert_array_equal(data1, [1, 2, 3])
        np.testing.assert_array_equal(data2, [4, 5, 6])
