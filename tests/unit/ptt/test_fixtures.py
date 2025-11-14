"""
Tests for PTT fixtures to ensure they work correctly.

This test file validates that our test fixtures are functioning properly.
"""

import pytest
import numpy as np
from tests.fixtures.ptt.test_helpers import (
    assert_ptt_event_logged,
    assert_timing_within_threshold,
    create_mock_key_sequence,
    assert_logger_session_valid,
    create_test_audio
)


class TestFixtures:
    """Test that fixtures are set up correctly"""

    def test_clean_env_fixture(self, clean_env):
        """Test that clean_env removes PTT environment variables"""
        import os
        ptt_vars = [k for k in os.environ.keys() if k.startswith("CHATTA_PTT_")]
        assert len(ptt_vars) == 0, "PTT env vars should be cleared"

    def test_ptt_config_fixture(self, ptt_config):
        """Test default PTT configuration fixture"""
        assert ptt_config["enabled"] is False
        assert ptt_config["key_combo"] == "down+right"
        assert ptt_config["mode"] == "hold"
        assert ptt_config["timeout"] == 120.0

    def test_mock_keyboard_key_fixture(self, mock_keyboard_key):
        """Test mock keyboard key factory"""
        key = mock_keyboard_key(name="space")
        assert key.name == "space"
        assert str(key) == "space"

        char_key = mock_keyboard_key(char="a")
        assert char_key.char == "a"

    def test_mock_keyboard_listener_fixture(self, mock_keyboard_listener):
        """Test mock keyboard listener"""
        assert hasattr(mock_keyboard_listener, "start")
        assert hasattr(mock_keyboard_listener, "stop")

        mock_keyboard_listener.start()
        mock_keyboard_listener.start.assert_called_once()

    def test_sample_audio_data_fixture(self, sample_audio_data):
        """Test sample audio data fixture"""
        assert isinstance(sample_audio_data, np.ndarray)
        assert len(sample_audio_data) == 16000  # 1 second at 16kHz
        assert sample_audio_data.dtype == np.int16

    def test_sample_audio_with_speech_fixture(self, sample_audio_with_speech):
        """Test sample audio with speech simulation"""
        assert isinstance(sample_audio_with_speech, np.ndarray)
        assert len(sample_audio_with_speech) == 32000  # 2 seconds
        # Should have some variance (not all zeros)
        assert np.std(sample_audio_with_speech) > 0

    def test_ptt_logger_fixture(self, ptt_logger):
        """Test PTT logger fixture"""
        assert ptt_logger.session_id == "test_session"
        assert len(ptt_logger.events) == 0

        # Test logging works
        ptt_logger.log_event("test", {"key": "value"})
        assert len(ptt_logger.events) == 1

    def test_mock_ptt_logger_fixture(self, mock_ptt_logger):
        """Test mock PTT logger fixture"""
        assert mock_ptt_logger.session_id == "mock_session"

        # Test mocked methods
        mock_ptt_logger.log_event("test", {})
        mock_ptt_logger.log_event.assert_called_once()

        timer_id = mock_ptt_logger.start_timer("operation")
        assert timer_id == "timer_123"

    def test_ptt_states_fixture(self, ptt_states):
        """Test PTT states fixture"""
        assert "IDLE" in ptt_states
        assert "RECORDING" in ptt_states
        assert "PROCESSING" in ptt_states
        assert len(ptt_states) == 7  # All states defined

    def test_callback_tracker_fixture(self, callback_tracker):
        """Test callback tracker fixture"""
        assert callback_tracker.press_count == 0
        assert callback_tracker.release_count == 0

        callback_tracker.on_press()
        assert callback_tracker.press_count == 1

        callback_tracker.on_release()
        assert callback_tracker.release_count == 1

        callback_tracker.reset()
        assert len(callback_tracker.calls) == 0

    def test_performance_thresholds_fixture(self, performance_thresholds):
        """Test performance thresholds fixture"""
        assert "key_detection" in performance_thresholds
        assert "recording_start" in performance_thresholds
        assert performance_thresholds["key_detection"] == 10.0

    def test_full_ptt_stack_fixture(self, full_ptt_stack):
        """Test complete PTT stack fixture"""
        assert "keyboard" in full_ptt_stack
        assert "logger" in full_ptt_stack
        assert "audio" in full_ptt_stack
        assert "config" in full_ptt_stack


class TestHelperFunctions:
    """Test helper utility functions"""

    def test_assert_ptt_event_logged(self, ptt_logger):
        """Test event logging assertion helper"""
        ptt_logger.log_event("test_event", {})
        ptt_logger.log_event("test_event", {})
        ptt_logger.log_event("other_event", {})

        # Should pass
        assert_ptt_event_logged(ptt_logger, "test_event", expected_count=2)
        assert_ptt_event_logged(ptt_logger, "other_event", expected_count=1)

        # Should fail
        with pytest.raises(AssertionError):
            assert_ptt_event_logged(ptt_logger, "test_event", expected_count=1)

    def test_assert_timing_within_threshold(self):
        """Test timing assertion helper"""
        # Should pass
        assert_timing_within_threshold(50.0, 100.0, "test_op")

        # Should fail
        with pytest.raises(AssertionError):
            assert_timing_within_threshold(150.0, 100.0, "test_op")

    def test_create_mock_key_sequence(self):
        """Test mock key sequence creation"""
        keys = create_mock_key_sequence(["ctrl", "alt", "space"])

        assert len(keys) == 3
        assert keys[0].name == "ctrl"
        assert keys[1].name == "alt"
        assert keys[2].name == "space"

    def test_create_test_audio(self):
        """Test audio creation helper"""
        # Silence
        silence = create_test_audio(sample_rate=16000, duration=0.5, noise_level=0)
        assert len(silence) == 8000  # 0.5 seconds
        assert np.all(silence == 0)

        # With noise
        noisy = create_test_audio(sample_rate=16000, duration=0.5, noise_level=100)
        assert len(noisy) == 8000
        assert np.std(noisy) > 0  # Has variance

    def test_assert_logger_session_valid(self):
        """Test logger session validation helper"""
        # Create logger with default session ID (starts with "ptt_")
        from voice_mode.ptt.logging import PTTLogger
        valid_logger = PTTLogger()

        # Should pass
        assert_logger_session_valid(valid_logger)

        # Test with invalid logger
        invalid_logger = type('obj', (object,), {
            'session_id': None,
            'events': [],
            'timing_data': {}
        })()

        with pytest.raises(AssertionError):
            assert_logger_session_valid(invalid_logger)


class TestFixtureIsolation:
    """Test that fixtures are properly isolated between tests"""

    def test_logger_isolation_1(self, ptt_logger):
        """First test - should have empty logger"""
        assert len(ptt_logger.events) == 0
        ptt_logger.log_event("test1", {})
        assert len(ptt_logger.events) == 1

    def test_logger_isolation_2(self, ptt_logger):
        """Second test - should have fresh empty logger"""
        assert len(ptt_logger.events) == 0
        ptt_logger.log_event("test2", {})
        assert len(ptt_logger.events) == 1

    def test_callback_tracker_isolation_1(self, callback_tracker):
        """First test - should have no calls"""
        assert callback_tracker.press_count == 0
        callback_tracker.on_press()
        assert callback_tracker.press_count == 1

    def test_callback_tracker_isolation_2(self, callback_tracker):
        """Second test - should have fresh tracker"""
        assert callback_tracker.press_count == 0
