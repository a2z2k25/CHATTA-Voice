"""
Pytest fixtures for PTT testing.

These fixtures provide reusable mocks and test data for all PTT tests.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Set
import numpy as np


# ==================== Configuration Fixtures ====================

@pytest.fixture
def clean_env(monkeypatch):
    """Clean PTT environment variables for isolated testing"""
    # Remove all PTT-related env vars
    for key in list(os.environ.keys()):
        if key.startswith("CHATTA_PTT_"):
            monkeypatch.delenv(key, raising=False)

    # Reload config to pick up changes
    import voice_mode.config as config
    from importlib import reload
    reload(config)

    yield

    # Cleanup after test
    reload(config)


@pytest.fixture
def ptt_config():
    """Default PTT configuration for testing"""
    return {
        "enabled": False,
        "key_combo": "down+right",
        "mode": "hold",
        "timeout": 120.0,
        "audio_feedback": True,
        "visual_feedback": True,
        "release_delay": 0.1,
        "min_duration": 0.5
    }


@pytest.fixture
def ptt_enabled_config(monkeypatch):
    """Configuration with PTT enabled"""
    monkeypatch.setenv("CHATTA_PTT_ENABLED", "true")
    monkeypatch.setenv("CHATTA_PTT_KEY_COMBO", "space")
    monkeypatch.setenv("CHATTA_PTT_MODE", "hold")

    import voice_mode.config as config
    from importlib import reload
    reload(config)

    return config


# ==================== Keyboard Fixtures ====================

@dataclass
class MockKey:
    """Mock keyboard key"""
    name: str = None
    char: str = None

    def __str__(self):
        return self.name or self.char or "unknown"


@pytest.fixture
def mock_keyboard_key():
    """Factory for creating mock keyboard keys"""
    def _create_key(name=None, char=None):
        return MockKey(name=name, char=char)
    return _create_key


@pytest.fixture
def mock_key_press_event():
    """Mock key press event"""
    def _create_event(key_name: str):
        return MockKey(name=key_name)
    return _create_event


@pytest.fixture
def mock_keyboard_listener():
    """Mock pynput keyboard listener"""
    listener = Mock()
    listener.start = Mock()
    listener.stop = Mock()
    listener.join = Mock()
    return listener


@pytest.fixture
def mock_keyboard_handler():
    """Mock KeyboardHandler instance"""
    from voice_mode.ptt.keyboard import KeyboardHandler

    handler = Mock(spec=KeyboardHandler)
    handler.key_combo = {"down", "right"}
    handler.pressed_keys = set()
    handler.is_combo_active = Mock(return_value=False)
    handler.is_running = Mock(return_value=False)
    handler.start = Mock(return_value=True)
    handler.stop = Mock()

    return handler


# ==================== Audio Fixtures ====================

@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing"""
    # 1 second of 16kHz audio (silence)
    sample_rate = 16000
    duration = 1.0
    num_samples = int(sample_rate * duration)

    # Generate silence
    audio_data = np.zeros(num_samples, dtype=np.int16)

    return audio_data


@pytest.fixture
def sample_audio_with_speech():
    """Generate sample audio data with simulated speech"""
    # 2 seconds of audio with some noise to simulate speech
    sample_rate = 16000
    duration = 2.0
    num_samples = int(sample_rate * duration)

    # Generate noise to simulate speech
    audio_data = np.random.randint(-1000, 1000, num_samples, dtype=np.int16)

    return audio_data


@pytest.fixture
def mock_audio_stream():
    """Mock sounddevice audio stream"""
    stream = Mock()
    stream.start = Mock()
    stream.stop = Mock()
    stream.close = Mock()
    stream.read = Mock(return_value=(np.zeros(1024, dtype=np.int16), False))

    return stream


@pytest.fixture
def mock_audio_device():
    """Mock audio device information"""
    return {
        "name": "Test Microphone",
        "index": 0,
        "hostapi": 0,
        "max_input_channels": 1,
        "max_output_channels": 0,
        "default_low_input_latency": 0.01,
        "default_high_input_latency": 0.1,
        "default_samplerate": 16000.0
    }


# ==================== Logging Fixtures ====================

@pytest.fixture
def ptt_logger():
    """Fresh PTT logger instance for testing"""
    from voice_mode.ptt.logging import PTTLogger, reset_ptt_logger

    # Reset global logger
    reset_ptt_logger()

    # Create new logger with test session ID
    logger = PTTLogger(session_id="test_session")

    yield logger

    # Cleanup
    reset_ptt_logger()


@pytest.fixture
def mock_ptt_logger():
    """Mock PTT logger for testing without actual logging"""
    from voice_mode.ptt.logging import PTTLogger

    logger = Mock(spec=PTTLogger)
    logger.session_id = "mock_session"
    logger.events = []
    logger.timing_data = {}
    logger.log_event = Mock()
    logger.log_key_event = Mock()
    logger.start_timer = Mock(return_value="timer_123")
    logger.stop_timer = Mock(return_value=10.0)
    logger.log_error = Mock()
    logger.log_state_transition = Mock()
    logger.get_session_summary = Mock(return_value={"total_events": 0})

    return logger


@pytest.fixture
def temp_log_dir(tmp_path):
    """Temporary directory for log files"""
    log_dir = tmp_path / "logs" / "ptt"
    log_dir.mkdir(parents=True)
    return log_dir


# ==================== State Machine Fixtures ====================

@pytest.fixture
def ptt_states():
    """PTT state enumeration values"""
    return {
        "IDLE": "IDLE",
        "WAITING_FOR_KEY": "WAITING_FOR_KEY",
        "KEY_PRESSED": "KEY_PRESSED",
        "RECORDING": "RECORDING",
        "RECORDING_STOPPED": "RECORDING_STOPPED",
        "RECORDING_CANCELLED": "RECORDING_CANCELLED",
        "PROCESSING": "PROCESSING"
    }


# ==================== Recording Fixtures ====================

@pytest.fixture
def mock_recording_session():
    """Mock recording session data"""
    return {
        "audio_data": np.zeros(16000, dtype=np.int16),  # 1 second
        "sample_rate": 16000,
        "duration": 1.0,
        "transcription": "test transcription text",
        "confidence": 0.95
    }


# ==================== Callback Fixtures ====================

@pytest.fixture
def callback_tracker():
    """Track callback invocations"""
    class CallbackTracker:
        def __init__(self):
            self.calls = []

        def on_press(self):
            self.calls.append(("press", None))

        def on_release(self):
            self.calls.append(("release", None))

        def reset(self):
            self.calls.clear()

        @property
        def press_count(self):
            return sum(1 for call in self.calls if call[0] == "press")

        @property
        def release_count(self):
            return sum(1 for call in self.calls if call[0] == "release")

    return CallbackTracker()


# ==================== Helper Functions ====================

@pytest.fixture
def simulate_key_combo():
    """Simulate pressing a key combination"""
    def _simulate(handler, keys: List[str], action: str = "press"):
        """
        Simulate key press or release on handler.

        Args:
            handler: KeyboardHandler instance
            keys: List of key names to press/release
            action: "press" or "release"
        """
        for key_name in keys:
            mock_key = MockKey(name=key_name)
            if action == "press":
                handler._on_press(mock_key)
            else:
                handler._on_release(mock_key)

    return _simulate


# ==================== Performance Testing Fixtures ====================

@pytest.fixture
def performance_thresholds():
    """Performance threshold values for testing"""
    return {
        "key_detection": 10.0,  # ms
        "recording_start": 100.0,  # ms
        "callback_execution": 5.0,  # ms
        "state_transition": 1.0,  # ms
        "audio_processing": 50.0  # ms
    }


# ==================== Async Fixtures ====================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Platform Fixtures ====================

@pytest.fixture
def mock_platform():
    """Mock platform detection"""
    def _mock_platform(platform_name: str):
        """
        Mock platform.system() to return specific platform.

        Args:
            platform_name: "Darwin", "Windows", "Linux"
        """
        with patch("platform.system", return_value=platform_name):
            yield platform_name

    return _mock_platform


# ==================== File System Fixtures ====================

@pytest.fixture
def temp_session_file(tmp_path):
    """Temporary file for session export"""
    session_file = tmp_path / "test_session.json"
    yield session_file
    # Cleanup happens automatically with tmp_path


# ==================== Integration Test Fixtures ====================

@pytest.fixture
def full_ptt_stack(mock_keyboard_handler, mock_ptt_logger, sample_audio_data):
    """Complete PTT stack for integration testing"""
    return {
        "keyboard": mock_keyboard_handler,
        "logger": mock_ptt_logger,
        "audio": sample_audio_data,
        "config": {
            "key_combo": "space",
            "mode": "hold",
            "timeout": 10.0
        }
    }
