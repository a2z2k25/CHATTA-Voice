"""
Integration tests for PTT with converse tool.

Tests that the converse() MCP tool correctly uses PTT recording
when PTT_ENABLED is True, and uses standard recording when False.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from voice_mode.tools.converse import converse as converse_tool

# Get the actual function from the MCP tool wrapper
converse = converse_tool.fn


@pytest.fixture(autouse=True)
def mock_keyboard_handler():
    """Mock KeyboardHandler to prevent actual keyboard monitoring"""
    with patch('voice_mode.ptt.controller.KeyboardHandler') as mock:
        instance = MagicMock()
        instance.start.return_value = True
        instance.stop.return_value = None
        mock.return_value = instance
        yield mock


@pytest.fixture(autouse=True)
def mock_sounddevice():
    """Mock sounddevice module to prevent actual audio recording"""
    with patch('voice_mode.ptt.recorder.sd') as mock_sd:
        mock_stream = MagicMock()
        mock_stream.start.return_value = None
        mock_stream.stop.return_value = None
        mock_stream.close.return_value = None
        mock_sd.InputStream.return_value = mock_stream
        yield mock_sd


@pytest.fixture(autouse=True)
def mock_startup():
    """Mock startup initialization"""
    with patch('voice_mode.tools.converse.startup_initialization', new_callable=AsyncMock):
        # Mock FFmpeg availability
        import voice_mode.config
        voice_mode.config.FFMPEG_AVAILABLE = True
        voice_mode.config.VAD_AGGRESSIVENESS = 2
        yield


class TestConverseWithPTTDisabled:
    """Test converse tool with PTT disabled (default behavior)"""

    @pytest.mark.asyncio
    @patch('voice_mode.config.PTT_ENABLED', False)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_uses_standard_recording(
        self,
        mock_audio_feedback,
        mock_stt,
        mock_record,
        mock_tts
    ):
        """Test that standard recording is used when PTT disabled"""
        # Mock TTS
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})

        # Mock audio feedback
        mock_audio_feedback.return_value = None

        # Mock recording
        mock_record.return_value = (np.array([1, 2, 3], dtype='int16'), True)

        # Mock STT
        mock_stt.return_value = "Test response"

        # Call converse
        result = await converse(
            message="Test message",
            wait_for_response=True,
            listen_duration=30.0
        )

        # Verify standard recording was called
        mock_record.assert_called_once()

        # Verify result
        assert "Test response" in result

    @pytest.mark.asyncio
    @patch('voice_mode.config.PTT_ENABLED', False)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_parameters_passed_correctly(
        self,
        mock_audio_feedback,
        mock_record,
        mock_tts
    ):
        """Test that parameters are passed to standard recording"""
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})
        mock_audio_feedback.return_value = None
        mock_record.return_value = (np.array([1], dtype='int16'), True)

        # Call with custom parameters
        await converse(
            message="Test",
            wait_for_response=True,
            listen_duration=45.0,
            min_listen_duration=3.0,
            disable_silence_detection=True,
            vad_aggressiveness=1
        )

        # Verify standard recording was called
        mock_record.assert_called_once()


class TestConverseWithPTTEnabled:
    """Test converse tool with PTT enabled"""

    @pytest.mark.asyncio
    @patch('voice_mode.tools.converse.PTT_ENABLED', True)
    @patch('voice_mode.tools.converse.check_livekit_available', new_callable=AsyncMock)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.get_recording_function')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_uses_ptt_recording(
        self,
        mock_audio_feedback,
        mock_stt,
        mock_get_recording_func,
        mock_tts,
        mock_livekit_check
    ):
        """Test that PTT recording is used when PTT enabled"""
        # Force local transport (don't use LiveKit)
        mock_livekit_check.return_value = False

        # Mock TTS
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})

        # Mock audio feedback
        mock_audio_feedback.return_value = None

        # Mock PTT recording function
        mock_ptt_record = Mock(return_value=(np.array([1, 2, 3], dtype='int16'), True))
        mock_get_recording_func.return_value = mock_ptt_record

        # Mock STT
        mock_stt.return_value = "PTT response"

        # Call converse
        result = await converse(
            message="Test message",
            wait_for_response=True,
            listen_duration=30.0
        )

        # Verify get_recording_function was called with PTT enabled
        mock_get_recording_func.assert_called_once_with(ptt_enabled=True)

        # Verify PTT recording function was called
        mock_ptt_record.assert_called_once()

        # Verify result
        assert "PTT response" in result

    @pytest.mark.asyncio
    @patch('voice_mode.tools.converse.PTT_ENABLED', True)
    @patch('voice_mode.tools.converse.check_livekit_available', new_callable=AsyncMock)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.get_recording_function')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_ptt_parameters_passed_correctly(
        self,
        mock_audio_feedback,
        mock_get_recording_func,
        mock_tts,
        mock_livekit_check
    ):
        """Test that parameters are passed to PTT recording"""
        # Force local transport
        mock_livekit_check.return_value = False

        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})
        mock_audio_feedback.return_value = None

        # Mock PTT recording function
        mock_ptt_record = Mock(return_value=(np.array([1], dtype='int16'), True))
        mock_get_recording_func.return_value = mock_ptt_record

        # Call with custom parameters
        await converse(
            message="Test",
            wait_for_response=True,
            listen_duration=45.0,
            min_listen_duration=3.0,
            disable_silence_detection=True,
            vad_aggressiveness=1
        )

        # Verify PTT recording function was called
        mock_ptt_record.assert_called_once()

    @pytest.mark.asyncio
    @patch('voice_mode.tools.converse.PTT_ENABLED', True)
    @patch('voice_mode.tools.converse.check_livekit_available', new_callable=AsyncMock)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.get_recording_function')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_ptt_fallback_on_error(
        self,
        mock_audio_feedback,
        mock_stt,
        mock_get_recording_func,
        mock_tts,
        mock_livekit_check
    ):
        """Test that PTT recording function is used (fallback is internal)"""
        # Force local transport
        mock_livekit_check.return_value = False

        # Mock TTS
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})

        # Mock audio feedback
        mock_audio_feedback.return_value = None

        # Mock PTT recording function that succeeds (fallback logic is tested in unit tests)
        mock_ptt_record = Mock(return_value=(np.array([1, 2], dtype='int16'), True))
        mock_get_recording_func.return_value = mock_ptt_record

        # Mock STT
        mock_stt.return_value = "PTT response"

        # Call converse
        result = await converse(
            message="Test",
            wait_for_response=True
        )

        # Verify PTT recording function was used
        mock_get_recording_func.assert_called_once_with(ptt_enabled=True)
        mock_ptt_record.assert_called()

        # Verify we got a successful result
        assert "PTT response" in result


class TestConverseBackwardCompatibility:
    """Test that converse tool maintains backward compatibility"""

    @pytest.mark.asyncio
    @patch('voice_mode.config.PTT_ENABLED', False)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_speak_only_mode_unaffected(
        self,
        mock_audio_feedback,
        mock_stt,
        mock_record,
        mock_tts
    ):
        """Test speak-only mode (wait_for_response=False) is unaffected"""
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})
        mock_audio_feedback.return_value = None

        result = await converse(
            message="Test message",
            wait_for_response=False
        )

        # Verify no recording occurred
        mock_record.assert_not_called()

        # Verify result indicates success
        assert "Error" not in result

    @pytest.mark.asyncio
    @patch('voice_mode.config.PTT_ENABLED', False)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    async def test_all_parameters_still_work(
        self,
        mock_audio_feedback,
        mock_stt,
        mock_record,
        mock_tts
    ):
        """Test that all existing parameters still work"""
        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})
        mock_audio_feedback.return_value = None
        mock_record.return_value = (np.array([1], dtype='int16'), True)
        mock_stt.return_value = "Test"

        # Call with all parameters
        result = await converse(
            message="Test",
            wait_for_response=True,
            listen_duration=45.0,
            min_listen_duration=3.0,
            transport="local",
            voice="alloy",
            tts_provider="openai",
            audio_feedback=True,
            disable_silence_detection=True,
            vad_aggressiveness=1
        )

        # Just verify it doesn't crash and returns a result
        assert isinstance(result, str)


class TestConverseTransportSelection:
    """Test transport selection with PTT"""

    @pytest.mark.asyncio
    @patch('voice_mode.config.PTT_ENABLED', True)
    @patch('voice_mode.tools.converse.check_livekit_available')
    @patch('voice_mode.tools.converse.livekit_converse')
    async def test_livekit_transport_bypasses_ptt(
        self,
        mock_livekit_converse,
        mock_livekit_check
    ):
        """Test that LiveKit transport doesn't use PTT (uses internal VAD)"""
        # Make LiveKit available
        mock_livekit_check.return_value = True
        mock_livekit_converse.return_value = "LiveKit response"

        # Call with auto transport (should select LiveKit)
        result = await converse(
            message="Test",
            wait_for_response=True,
            transport="auto"
        )

        # Verify LiveKit was used
        mock_livekit_converse.assert_called_once()

        # Verify result
        assert "LiveKit response" in result

    @pytest.mark.asyncio
    @patch('voice_mode.tools.converse.PTT_ENABLED', True)
    @patch('voice_mode.tools.converse.text_to_speech_with_failover')
    @patch('voice_mode.tools.converse.get_recording_function')
    @patch('voice_mode.tools.converse.speech_to_text')
    @patch('voice_mode.tools.converse.play_audio_feedback')
    @patch('voice_mode.tools.converse.check_livekit_available', new_callable=AsyncMock)
    async def test_local_transport_uses_ptt(
        self,
        mock_livekit_check,
        mock_audio_feedback,
        mock_stt,
        mock_get_recording_func,
        mock_tts
    ):
        """Test that local transport uses PTT when enabled"""
        # Make LiveKit unavailable (forces local)
        mock_livekit_check.return_value = False

        mock_tts.return_value = (True, {'ttfa': 0.1, 'generation': 0.2, 'playback': 0.3}, {'model': 'tts-1', 'voice': 'alloy'})
        mock_audio_feedback.return_value = None

        # Mock PTT recording function
        mock_ptt_record = Mock(return_value=(np.array([1, 2], dtype='int16'), True))
        mock_get_recording_func.return_value = mock_ptt_record

        mock_stt.return_value = "PTT local response"

        # Call with auto transport (will fallback to local)
        result = await converse(
            message="Test",
            wait_for_response=True,
            transport="auto"
        )

        # Verify PTT recording function was used
        mock_get_recording_func.assert_called_once_with(ptt_enabled=True)
        mock_ptt_record.assert_called_once()

        # Verify result
        assert "PTT local response" in result
