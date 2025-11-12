"""
Unit tests for PTT transport adapter.

Tests the bridge between PTT system and CHATTA's transport layer,
ensuring interface compatibility and correct behavior across all PTT modes.
"""

import pytest
import numpy as np
import time
from unittest.mock import Mock, MagicMock, patch
from voice_mode.ptt.transport_adapter import (
    record_with_ptt,
    record_with_ptt_fallback,
    get_recording_function,
    PTTRecordingSession
)
from voice_mode.ptt.controller import PTTController


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


class TestPTTRecordingSession:
    """Test PTTRecordingSession class"""

    def test_initialization(self):
        """Test session initialization"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)

        assert session.controller == controller
        assert session.max_duration == 30.0
        assert session.min_duration == 2.0
        assert session.audio_data is None
        assert session.speech_detected is False
        assert session.error is None
        assert not session.completed.is_set()

    def test_on_recording_stop(self):
        """Test recording stop callback"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)
        session.start_time = time.time()

        audio_data = np.array([1, 2, 3], dtype='int16')
        session.on_recording_stop(audio_data)

        assert session.audio_data is not None
        assert len(session.audio_data) == 3
        assert session.speech_detected is True
        assert session.completed.is_set()
        assert session.end_time is not None

    def test_on_recording_stop_empty_audio(self):
        """Test recording stop with empty audio"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)
        session.start_time = time.time()

        audio_data = np.array([], dtype='int16')
        session.on_recording_stop(audio_data)

        assert session.audio_data is not None
        assert len(session.audio_data) == 0
        assert session.speech_detected is False
        assert session.completed.is_set()

    def test_on_recording_cancel(self):
        """Test recording cancel callback"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)
        session.start_time = time.time()

        session.on_recording_cancel()

        assert session.audio_data is None
        assert session.speech_detected is False
        assert session.completed.is_set()
        assert session.end_time is not None

    def test_on_error(self):
        """Test error callback"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)

        error = Exception("Test error")
        session.on_error(error)

        assert session.error == error
        assert session.audio_data is None
        assert session.speech_detected is False
        assert session.completed.is_set()

    def test_wait_for_completion_success(self):
        """Test waiting for completion that succeeds"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)

        # Simulate completion in background
        session.completed.set()

        result = session.wait_for_completion(timeout=1.0)
        assert result is True

    def test_wait_for_completion_timeout(self):
        """Test waiting for completion that times out"""
        controller = Mock()
        session = PTTRecordingSession(controller, 30.0, 2.0)

        # Don't set completion
        result = session.wait_for_completion(timeout=0.1)
        assert result is False


class TestRecordWithPTT:
    """Test record_with_ptt function"""

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_interface_contract_return_type(self, mock_controller_class):
        """Test that return value matches interface contract"""
        # Mock controller
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        # Mock successful recording
        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([1, 2, 3], dtype='int16')
            mock_session.speech_detected = True
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 1.0
            mock_session_class.return_value = mock_session

            result = record_with_ptt(max_duration=30.0)

            # Verify return type
            assert isinstance(result, tuple)
            assert len(result) == 2
            audio_data, speech_detected = result

            # Verify audio data
            assert isinstance(audio_data, np.ndarray)
            assert audio_data.dtype == np.int16
            assert len(audio_data) == 3

            # Verify speech detected
            assert isinstance(speech_detected, bool)
            assert speech_detected is True

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_interface_contract_empty_recording(self, mock_controller_class):
        """Test empty recording returns correct format"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([], dtype='int16')
            mock_session.speech_detected = False
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 0.1
            mock_session_class.return_value = mock_session

            result = record_with_ptt(max_duration=30.0)
            audio_data, speech_detected = result

            assert isinstance(audio_data, np.ndarray)
            assert audio_data.dtype == np.int16
            assert len(audio_data) == 0
            assert speech_detected is False

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_parameter_handling_all_parameters(self, mock_controller_class):
        """Test that all parameters are handled correctly"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([1, 2, 3], dtype='int16')
            mock_session.speech_detected = True
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 1.0
            mock_session_class.return_value = mock_session

            result = record_with_ptt(
                max_duration=45.0,
                disable_silence_detection=True,
                min_duration=3.0,
                vad_aggressiveness=1
            )

            # Verify controller was created with correct parameters
            assert mock_controller_class.called
            call_kwargs = mock_controller_class.call_args[1]
            assert call_kwargs['timeout'] == 45.0
            assert call_kwargs['min_duration'] == 3.0

            # Verify result
            audio_data, speech_detected = result
            assert len(audio_data) == 3
            assert speech_detected is True

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    @patch('voice_mode.config.PTT_MODE', 'hybrid')
    def test_hybrid_mode_with_silence_detection_disabled(self, mock_controller_class):
        """Test hybrid mode switches to hold when silence detection disabled"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([1, 2], dtype='int16')
            mock_session.speech_detected = True
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 1.0
            mock_session_class.return_value = mock_session

            result = record_with_ptt(
                max_duration=30.0,
                disable_silence_detection=True  # Should switch from hybrid to hold
            )

            # Verify mode was changed to hold
            call_kwargs = mock_controller_class.call_args[1]
            assert call_kwargs['mode'] == 'hold'

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_timeout_handling(self, mock_controller_class):
        """Test timeout returns empty result"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = False  # Timeout
            mock_session_class.return_value = mock_session

            result = record_with_ptt(max_duration=30.0)
            audio_data, speech_detected = result

            assert isinstance(audio_data, np.ndarray)
            assert len(audio_data) == 0
            assert speech_detected is False

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_error_handling(self, mock_controller_class):
        """Test error is raised when recording fails"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = RuntimeError("Recording failed")
            mock_session_class.return_value = mock_session

            with pytest.raises(RuntimeError, match="Recording failed"):
                record_with_ptt(max_duration=30.0)

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_controller_enable_failure(self, mock_controller_class):
        """Test error raised when controller fails to enable"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = False  # Fails to enable
        mock_controller_class.return_value = mock_controller

        with pytest.raises(RuntimeError, match="Failed to enable PTT controller"):
            record_with_ptt(max_duration=30.0)

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_cleanup_on_success(self, mock_controller_class):
        """Test controller is disabled after successful recording"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([1, 2], dtype='int16')
            mock_session.speech_detected = True
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 1.0
            mock_session_class.return_value = mock_session

            result = record_with_ptt(max_duration=30.0)

            # Verify controller was disabled
            mock_controller.disable.assert_called_once()

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_cleanup_on_error(self, mock_controller_class):
        """Test controller is disabled even after error"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = RuntimeError("Test error")
            mock_session_class.return_value = mock_session

            with pytest.raises(RuntimeError):
                record_with_ptt(max_duration=30.0)

            # Verify controller was still disabled
            mock_controller.disable.assert_called_once()


class TestRecordWithPTTFallback:
    """Test record_with_ptt_fallback function"""

    @patch('voice_mode.ptt.transport_adapter.record_with_ptt')
    def test_success_uses_ptt(self, mock_record_with_ptt):
        """Test fallback uses PTT when it succeeds"""
        mock_record_with_ptt.return_value = (np.array([1, 2], dtype='int16'), True)

        result = record_with_ptt_fallback(max_duration=30.0)
        audio_data, speech_detected = result

        assert len(audio_data) == 2
        assert speech_detected is True
        mock_record_with_ptt.assert_called_once()

    @patch('voice_mode.ptt.transport_adapter.record_with_ptt')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    def test_error_falls_back_to_standard(self, mock_standard_record, mock_record_with_ptt):
        """Test fallback uses standard recording when PTT fails"""
        # PTT raises error
        mock_record_with_ptt.side_effect = RuntimeError("PTT failed")

        # Standard recording succeeds
        mock_standard_record.return_value = (np.array([3, 4], dtype='int16'), True)

        result = record_with_ptt_fallback(max_duration=30.0)
        audio_data, speech_detected = result

        assert len(audio_data) == 2
        assert speech_detected is True
        mock_record_with_ptt.assert_called_once()
        mock_standard_record.assert_called_once()

    @patch('voice_mode.ptt.transport_adapter.record_with_ptt')
    @patch('voice_mode.tools.converse.record_audio_with_silence_detection')
    def test_parameters_passed_to_fallback(self, mock_standard_record, mock_record_with_ptt):
        """Test parameters are passed to standard recording on fallback"""
        mock_record_with_ptt.side_effect = RuntimeError("PTT failed")
        mock_standard_record.return_value = (np.array([1], dtype='int16'), True)

        record_with_ptt_fallback(
            max_duration=45.0,
            disable_silence_detection=True,
            min_duration=3.0,
            vad_aggressiveness=1
        )

        # Verify parameters passed to standard recording
        mock_standard_record.assert_called_once_with(
            max_duration=45.0,
            disable_silence_detection=True,
            min_duration=3.0,
            vad_aggressiveness=1
        )


class TestGetRecordingFunction:
    """Test get_recording_function utility"""

    @patch('voice_mode.config.PTT_ENABLED', True)
    def test_returns_ptt_function_when_enabled(self):
        """Test returns PTT function when PTT is enabled"""
        func = get_recording_function()
        assert func == record_with_ptt_fallback

    @patch('voice_mode.config.PTT_ENABLED', False)
    def test_returns_standard_function_when_disabled(self):
        """Test returns standard function when PTT is disabled"""
        from voice_mode.tools.converse import record_audio_with_silence_detection

        func = get_recording_function()
        assert func == record_audio_with_silence_detection

    def test_explicit_override_enabled(self):
        """Test explicit override to enable PTT"""
        func = get_recording_function(ptt_enabled=True)
        assert func == record_with_ptt_fallback

    def test_explicit_override_disabled(self):
        """Test explicit override to disable PTT"""
        from voice_mode.tools.converse import record_audio_with_silence_detection

        func = get_recording_function(ptt_enabled=False)
        assert func == record_audio_with_silence_detection


class TestInterfaceCompatibility:
    """Test interface compatibility with existing recording functions"""

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_matches_record_audio_with_silence_detection_signature(self, mock_controller_class):
        """Test signature matches existing function"""
        from voice_mode.tools.converse import record_audio_with_silence_detection
        import inspect

        # Get signatures
        ptt_sig = inspect.signature(record_with_ptt)
        standard_sig = inspect.signature(record_audio_with_silence_detection)

        # Verify parameter names match (order matters for positional calls)
        ptt_params = list(ptt_sig.parameters.keys())
        standard_params = list(standard_sig.parameters.keys())

        assert ptt_params == standard_params

    @patch('voice_mode.ptt.transport_adapter.PTTController')
    def test_returns_same_format_as_standard(self, mock_controller_class):
        """Test return format matches existing function"""
        mock_controller = MagicMock()
        mock_controller.enable.return_value = True
        mock_controller_class.return_value = mock_controller

        with patch('voice_mode.ptt.transport_adapter.PTTRecordingSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.wait_for_completion.return_value = True
            mock_session.error = None
            mock_session.audio_data = np.array([1, 2], dtype='int16')
            mock_session.speech_detected = True
            mock_session.start_time = time.time()
            mock_session.end_time = time.time() + 1.0
            mock_session_class.return_value = mock_session

            # Call PTT function
            ptt_result = record_with_ptt(30.0, False, 2.0, 2)

            # Verify result format
            assert isinstance(ptt_result, tuple)
            assert len(ptt_result) == 2
            audio_data, speech_detected = ptt_result
            assert isinstance(audio_data, np.ndarray)
            assert audio_data.dtype == np.int16
            assert isinstance(speech_detected, bool)
