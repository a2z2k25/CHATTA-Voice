"""
Phase 3 Validation Tests

These tests verify completeness, operability, and integration correctness
of the PTT Phase 3 implementation.
"""

import pytest
import asyncio
import time
import numpy as np
from unittest.mock import Mock, MagicMock, patch

# Test 1: Verify all public API exports are available
def test_public_api_exports():
    """Verify all documented public APIs are exportable"""
    from voice_mode import ptt

    # Core classes
    assert hasattr(ptt, 'PTTController')
    assert hasattr(ptt, 'PTTStateMachine')
    assert hasattr(ptt, 'PTTRecorder')
    assert hasattr(ptt, 'AsyncPTTRecorder')
    assert hasattr(ptt, 'KeyboardHandler')
    assert hasattr(ptt, 'PTTLogger')
    assert hasattr(ptt, 'PTTEvent')

    # Enums
    assert hasattr(ptt, 'PTTState')

    # Factory functions
    assert hasattr(ptt, 'create_ptt_controller')
    assert hasattr(ptt, 'create_ptt_state_machine')
    assert hasattr(ptt, 'create_ptt_recorder')
    assert hasattr(ptt, 'create_async_ptt_recorder')

    # Utility functions
    assert hasattr(ptt, 'get_ptt_logger')
    assert hasattr(ptt, 'reset_ptt_logger')
    assert hasattr(ptt, 'check_keyboard_permissions')

    # State transition class
    assert hasattr(ptt, 'StateTransition')


def test_ptt_state_enum_values():
    """Verify all state enum values are defined"""
    from voice_mode.ptt import PTTState

    assert hasattr(PTTState, 'IDLE')
    assert hasattr(PTTState, 'WAITING_FOR_KEY')
    assert hasattr(PTTState, 'KEY_PRESSED')
    assert hasattr(PTTState, 'RECORDING')
    assert hasattr(PTTState, 'RECORDING_STOPPED')
    assert hasattr(PTTState, 'RECORDING_CANCELLED')
    assert hasattr(PTTState, 'PROCESSING')

    # Verify they have correct values
    assert PTTState.IDLE.value == "IDLE"
    assert PTTState.WAITING_FOR_KEY.value == "WAITING_FOR_KEY"
    assert PTTState.RECORDING.value == "RECORDING"


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


def test_ptt_logger_functionality():
    """Verify PTT logger works correctly"""
    from voice_mode.ptt import get_ptt_logger, reset_ptt_logger, PTTEvent

    # Reset to clean state
    logger = reset_ptt_logger()

    # Log an event
    logger.log_event("test_event", {"key": "value"})

    # Retrieve events (PTTLogger stores events in .events list)
    assert len(logger.events) >= 1

    # Check event structure
    event = logger.events[-1]
    assert event.event_type == "test_event"
    assert event.data["key"] == "value"
    assert event.timestamp > 0

    # Log an error
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.log_error(e, {"context": "test"})

    # Check error was logged
    errors = [e for e in logger.events if e.event_type == "error"]
    assert len(errors) >= 1
    assert errors[-1].data["error_type"] == "ValueError"

    # Clear logger by resetting events list
    logger.events = []
    assert len(logger.events) == 0


def test_state_machine_valid_transitions():
    """Verify state machine enforces valid transitions"""
    from voice_mode.ptt import PTTStateMachine, PTTState

    sm = PTTStateMachine()

    # Valid: IDLE → WAITING_FOR_KEY
    assert sm.current_state == PTTState.IDLE
    sm.transition(PTTState.WAITING_FOR_KEY)
    assert sm.current_state == PTTState.WAITING_FOR_KEY

    # Valid: WAITING_FOR_KEY → KEY_PRESSED
    sm.transition(PTTState.KEY_PRESSED)
    assert sm.current_state == PTTState.KEY_PRESSED

    # Valid: KEY_PRESSED → RECORDING
    sm.transition(PTTState.RECORDING)
    assert sm.current_state == PTTState.RECORDING
    assert sm.is_recording() is True

    # Valid: RECORDING → RECORDING_STOPPED
    sm.transition(PTTState.RECORDING_STOPPED)
    assert sm.current_state == PTTState.RECORDING_STOPPED
    assert sm.is_recording() is False

    # Valid: RECORDING_STOPPED → PROCESSING
    sm.transition(PTTState.PROCESSING)
    assert sm.current_state == PTTState.PROCESSING

    # Valid: PROCESSING → IDLE
    sm.transition(PTTState.IDLE)
    assert sm.current_state == PTTState.IDLE


def test_state_machine_invalid_transitions():
    """Verify state machine rejects invalid transitions"""
    from voice_mode.ptt import PTTStateMachine, PTTState

    sm = PTTStateMachine()

    # Invalid: IDLE → RECORDING (must go through WAITING_FOR_KEY and KEY_PRESSED)
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(PTTState.RECORDING)

    # Invalid: IDLE → PROCESSING
    with pytest.raises(ValueError, match="Invalid transition"):
        sm.transition(PTTState.PROCESSING)


def test_state_machine_can_transition():
    """Verify can_transition() correctly predicts validity"""
    from voice_mode.ptt import PTTStateMachine, PTTState

    sm = PTTStateMachine()

    # From IDLE
    assert sm.can_transition(PTTState.WAITING_FOR_KEY) is True
    assert sm.can_transition(PTTState.RECORDING) is False
    assert sm.can_transition(PTTState.PROCESSING) is False


@pytest.mark.asyncio
async def test_ptt_controller_initialization():
    """Verify PTT controller initializes correctly"""
    from voice_mode.ptt import PTTController

    controller = PTTController(
        key_combo="ctrl+space",
        timeout=30.0
    )

    assert controller.is_enabled is False
    assert controller.is_recording is False
    assert controller._key_combo == "ctrl+space"
    assert controller._timeout == 30.0


@pytest.mark.asyncio
async def test_ptt_controller_enable_disable():
    """Verify PTT controller enable/disable lifecycle"""
    from voice_mode.ptt import PTTController, PTTState

    controller = PTTController()

    # Enable
    result = controller.enable()
    assert result is True
    assert controller.is_enabled is True
    assert controller.current_state == PTTState.WAITING_FOR_KEY

    # Enable again (should return False)
    result = controller.enable()
    assert result is False

    # Disable
    result = controller.disable()
    assert result is True
    assert controller.is_enabled is False
    assert controller.current_state == PTTState.IDLE

    # Disable again (should return False)
    result = controller.disable()
    assert result is False


@pytest.mark.asyncio
async def test_ptt_controller_get_status():
    """Verify get_status() returns correct information"""
    from voice_mode.ptt import PTTController
    from voice_mode import config

    config.PTT_MODE = "hybrid"
    controller = PTTController(key_combo="F12", timeout=45.0)

    status = controller.get_status()

    assert isinstance(status, dict)
    assert "enabled" in status
    assert "state" in status
    assert "is_recording" in status
    assert "key_combo" in status
    assert "timeout" in status
    assert "mode" in status

    assert status["enabled"] is False
    assert status["key_combo"] == "F12"
    assert status["timeout"] == 45.0
    assert status["mode"] == "hybrid"


@pytest.mark.asyncio
async def test_factory_functions():
    """Verify factory functions create correct instances"""
    from voice_mode.ptt import (
        create_ptt_controller,
        create_ptt_state_machine,
        create_ptt_recorder,
        create_async_ptt_recorder,
        PTTController,
        PTTStateMachine,
        PTTRecorder,
        AsyncPTTRecorder
    )

    # Controller factory
    controller = create_ptt_controller()
    assert isinstance(controller, PTTController)

    # State machine factory
    sm = create_ptt_state_machine()
    assert isinstance(sm, PTTStateMachine)

    # Recorder factory (sync)
    recorder = create_ptt_recorder()
    assert isinstance(recorder, PTTRecorder)

    # Recorder factory (async)
    async_recorder = create_async_ptt_recorder()
    assert isinstance(async_recorder, AsyncPTTRecorder)


@pytest.mark.asyncio
async def test_three_modes_configuration():
    """Verify all three PTT modes are configurable"""
    from voice_mode.ptt import PTTController
    from voice_mode import config

    # Hold mode
    config.PTT_MODE = "hold"
    controller_hold = PTTController()
    assert controller_hold._mode == "hold"

    # Toggle mode
    config.PTT_MODE = "toggle"
    controller_toggle = PTTController()
    assert controller_toggle._mode == "toggle"

    # Hybrid mode
    config.PTT_MODE = "hybrid"
    controller_hybrid = PTTController()
    assert controller_hybrid._mode == "hybrid"


@pytest.mark.asyncio
async def test_event_queue_mechanism():
    """Verify event queue works correctly"""
    from voice_mode.ptt import PTTController

    controller = PTTController()
    controller.enable()

    # Manually queue an event
    test_event = {"type": "test_event", "timestamp": time.time()}
    controller._event_queue.put(test_event)

    # Retrieve event
    event = await controller.wait_for_event(timeout=0.1)
    assert event is not None
    assert event["type"] == "test_event"

    # Timeout when no event
    event = await controller.wait_for_event(timeout=0.1)
    assert event is None

    controller.disable()


@pytest.mark.asyncio
async def test_recorder_lifecycle():
    """Verify recorder lifecycle works correctly"""
    from voice_mode.ptt import create_async_ptt_recorder

    recorder = create_async_ptt_recorder()

    # Initial state
    assert recorder.is_recording is False
    assert recorder.duration == 0.0

    # Start recording
    result = await recorder.start()
    assert result is True
    assert recorder.is_recording is True

    # Try to start again (should return False)
    result = await recorder.start()
    assert result is False

    # Add mock audio data
    recorder._recorder._audio_chunks = [
        np.array([1, 2, 3, 4, 5], dtype='int16')
    ]

    # Stop and get data
    audio_data = await recorder.stop()
    assert audio_data is not None
    assert len(audio_data) == 5
    assert recorder.is_recording is False


@pytest.mark.asyncio
async def test_error_recovery_mechanism():
    """Verify error recovery works correctly"""
    from voice_mode.ptt import PTTController

    controller = PTTController()
    controller.enable()

    # Verify retry count starts at 0
    assert controller._retry_count == 0
    assert controller._max_retries == 3

    # Test recovery logic (internal method)
    result = await controller._recover_from_error("test_operation", Exception("Test"))
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_timeout_mechanism():
    """Verify timeout monitoring works"""
    from voice_mode.ptt import PTTController
    from voice_mode import config

    config.PTT_MODE = "hold"
    config.PTT_TIMEOUT = 0.2  # 200ms for fast testing

    controller = PTTController()
    controller.enable()

    # Start recording
    controller._key_press_time = time.time()
    controller._on_key_press()

    event = await controller.wait_for_event(timeout=0.1)
    assert event["type"] == "start_recording"

    await controller._handle_start_recording(event)
    assert controller.is_recording is True

    # Verify timeout task was created
    assert controller._timeout_task is not None

    controller.disable()


@pytest.mark.asyncio
async def test_hybrid_mode_silence_detection():
    """Verify hybrid mode silence detection configuration"""
    from voice_mode.ptt import PTTController
    from voice_mode import config

    config.PTT_MODE = "hybrid"
    config.SILENCE_THRESHOLD_MS = 1500

    controller = PTTController()

    # Verify silence timeout was configured
    assert controller._hybrid_silence_timeout == 1.5  # Converted to seconds


@pytest.mark.asyncio
async def test_component_integration():
    """Verify all components work together"""
    from voice_mode.ptt import PTTController, PTTState

    audio_received = []

    async def handle_audio(audio_data):
        audio_received.append(audio_data)

    controller = PTTController(
        key_combo="space",
        on_recording_stop=handle_audio
    )

    # Enable controller
    assert controller.enable() is True
    assert controller.current_state == PTTState.WAITING_FOR_KEY

    # Simulate key press
    controller._key_press_time = time.time()
    controller._on_key_press()

    # Process start event
    event = await controller.wait_for_event(timeout=0.1)
    assert event["type"] == "start_recording"
    await controller._handle_start_recording(event)
    assert controller.current_state == PTTState.RECORDING

    # Add audio data
    controller._recorder._recorder._audio_chunks = [
        np.array([1, 2, 3], dtype='int16')
    ]

    # Simulate key release
    await asyncio.sleep(0.1)  # Ensure minimum duration
    controller._on_key_release()

    # Process stop event
    event = await controller.wait_for_event(timeout=0.1)
    assert event["type"] == "stop_recording"
    await controller._handle_stop_recording(event)

    # Verify callback was called with audio
    assert len(audio_received) == 1
    assert audio_received[0] is not None

    controller.disable()


def test_documentation_examples_are_valid():
    """Verify code examples from documentation are syntactically valid"""
    # This is a meta-test to ensure documentation examples are correct

    # Example from README.md - Basic Usage
    example_code = """
from voice_mode.ptt import PTTController

controller = PTTController()
controller.enable()
controller.disable()
"""

    try:
        compile(example_code, '<string>', 'exec')
    except SyntaxError as e:
        pytest.fail(f"Documentation example has syntax error: {e}")

    # Example from API_REFERENCE.md
    api_example = """
from voice_mode.ptt import PTTController, PTTState

controller = PTTController(
    key_combo="ctrl+space",
    timeout=30.0
)
"""

    try:
        compile(api_example, '<string>', 'exec')
    except SyntaxError as e:
        pytest.fail(f"API documentation example has syntax error: {e}")


def test_all_config_variables_exist():
    """Verify all configuration variables are defined"""
    from voice_mode import config

    # Core PTT config
    assert hasattr(config, 'PTT_MODE')
    assert hasattr(config, 'PTT_KEY_COMBO')
    assert hasattr(config, 'PTT_CANCEL_KEY')
    assert hasattr(config, 'PTT_TIMEOUT')
    assert hasattr(config, 'PTT_MIN_DURATION')
    assert hasattr(config, 'SILENCE_THRESHOLD_MS')


def test_version_information():
    """Verify version information is accessible"""
    from voice_mode.ptt import __version__

    assert __version__ == "0.1.0"
