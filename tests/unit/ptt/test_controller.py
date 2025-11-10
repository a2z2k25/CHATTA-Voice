"""
Tests for PTT Controller.

This module tests the PTTController class that orchestrates
keyboard handling, state management, and event processing.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from voice_mode.ptt import (
    PTTController,
    PTTState,
    create_ptt_controller
)


@pytest.fixture(autouse=True)
def mock_keyboard_handler():
    """Mock KeyboardHandler to prevent actual keyboard monitoring"""
    with patch('voice_mode.ptt.controller.KeyboardHandler') as mock:
        # Create a mock instance that start() returns True
        instance = MagicMock()
        instance.start.return_value = True
        instance.stop.return_value = None
        instance.is_running.return_value = False
        mock.return_value = instance
        yield mock


class TestPTTController:
    """Tests for PTTController class"""

    def test_initialization(self):
        """Test controller initializes with correct defaults"""
        controller = PTTController()

        assert controller.is_enabled is False
        assert controller.is_recording is False
        assert controller.current_state == PTTState.IDLE
        assert controller.current_state_name == "IDLE"

    def test_initialization_with_custom_params(self, ptt_logger):
        """Test controller with custom parameters"""
        controller = PTTController(
            key_combo="space",
            cancel_key="esc",
            logger=ptt_logger,
            timeout=60.0
        )

        assert controller._key_combo == "space"
        assert controller._cancel_key == "esc"
        assert controller._timeout == 60.0
        assert controller._logger == ptt_logger

    def test_enable_ptt(self, mock_keyboard_handler):
        """Test enabling PTT mode"""
        controller = PTTController(key_combo="space")

        result = controller.enable()

        assert result is True
        assert controller.is_enabled is True
        assert controller.current_state == PTTState.WAITING_FOR_KEY

    def test_enable_when_already_enabled(self, mock_keyboard_handler):
        """Test enabling when already enabled returns False"""
        controller = PTTController()
        controller.enable()

        # Try to enable again
        result = controller.enable()

        assert result is False
        assert controller.is_enabled is True

    def test_disable_ptt(self, mock_keyboard_handler):
        """Test disabling PTT mode"""
        controller = PTTController()
        controller.enable()

        result = controller.disable()

        assert result is True
        assert controller.is_enabled is False
        assert controller.current_state == PTTState.IDLE

    def test_disable_when_not_enabled(self):
        """Test disabling when not enabled returns False"""
        controller = PTTController()

        result = controller.disable()

        assert result is False

    def test_key_press_triggers_state_transition(self, mock_keyboard_handler):
        """Test key press moves to KEY_PRESSED state"""
        controller = PTTController()
        controller.enable()

        # Simulate key press
        controller._on_key_press()

        assert controller.current_state == PTTState.KEY_PRESSED

    def test_key_press_queues_recording_event(self, mock_keyboard_handler):
        """Test key press queues start recording event"""
        controller = PTTController()
        controller.enable()

        # Simulate key press
        controller._on_key_press()

        # Check event was queued
        event = controller._event_queue.get_nowait()
        assert event["type"] == "start_recording"
        assert "timestamp" in event

    def test_key_release_from_recording(self, mock_keyboard_handler):
        """Test key release from RECORDING state"""
        controller = PTTController()
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")

        # Simulate key release
        controller._on_key_release()

        assert controller.current_state == PTTState.RECORDING_STOPPED

    def test_quick_release_before_recording(self, mock_keyboard_handler):
        """Test releasing key before recording starts"""
        controller = PTTController()
        controller.enable()
        controller._on_key_press()  # Move to KEY_PRESSED

        # Quick release
        controller._on_key_release()

        assert controller.current_state == PTTState.IDLE

    def test_cancel_recording(self, mock_keyboard_handler):
        """Test cancelling active recording"""
        controller = PTTController()
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")

        # Cancel
        controller._cancel_recording()

        assert controller.current_state == PTTState.RECORDING_CANCELLED

    @pytest.mark.asyncio
    async def test_wait_for_event(self):
        """Test waiting for events from queue"""
        controller = PTTController()

        # Put event in queue
        test_event = {"type": "test", "data": "value"}
        controller._event_queue.put(test_event)

        # Wait for it
        event = await controller.wait_for_event(timeout=1.0)

        assert event == test_event

    @pytest.mark.asyncio
    async def test_wait_for_event_timeout(self):
        """Test wait_for_event returns None on timeout"""
        controller = PTTController()

        # No events in queue
        event = await controller.wait_for_event(timeout=0.1)

        assert event is None

    @pytest.mark.asyncio
    async def test_handle_start_recording(self):
        """Test handling start recording event"""
        callback_called = []

        def on_start():
            callback_called.append(True)

        controller = PTTController(on_recording_start=on_start)
        controller.enable()
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        # Handle start event
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        assert controller.current_state == PTTState.RECORDING
        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_handle_start_recording_async_callback(self):
        """Test handling start recording with async callback"""
        callback_called = []

        async def on_start():
            callback_called.append(True)

        controller = PTTController(on_recording_start=on_start)
        controller.enable()
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_handle_stop_recording(self):
        """Test handling stop recording event"""
        callback_called = []

        def on_stop(audio_data):
            callback_called.append(audio_data)

        controller = PTTController(on_recording_stop=on_stop)
        controller.enable()

        # Get to RECORDING_STOPPED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")
        controller._state_machine.transition(PTTState.RECORDING_STOPPED, "stop")

        # Handle stop event
        event = {"type": "stop_recording", "timestamp": 0}
        await controller._handle_stop_recording(event)

        assert controller.current_state == PTTState.WAITING_FOR_KEY
        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_handle_cancel_recording(self):
        """Test handling cancel recording event"""
        callback_called = []

        def on_cancel():
            callback_called.append(True)

        controller = PTTController(on_recording_cancel=on_cancel)
        controller.enable()

        # Get to RECORDING_CANCELLED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")
        controller._state_machine.transition(PTTState.RECORDING_CANCELLED, "cancel")

        # Handle cancel event
        event = {"type": "cancel_recording", "timestamp": 0}
        await controller._handle_cancel_recording(event)

        assert controller.current_state == PTTState.WAITING_FOR_KEY
        assert len(callback_called) == 1

    def test_get_status(self):
        """Test getting controller status"""
        controller = PTTController(key_combo="space")

        status = controller.get_status()

        assert status["enabled"] is False
        assert status["state"] == "IDLE"
        assert status["is_recording"] is False
        assert status["key_combo"] == "space"
        assert "state_machine" in status

    def test_get_status_when_enabled(self):
        """Test status when PTT is enabled"""
        controller = PTTController()
        controller.enable()

        status = controller.get_status()

        assert status["enabled"] is True
        assert status["state"] == "WAITING_FOR_KEY"

    def test_context_manager(self):
        """Test using controller as context manager"""
        with PTTController() as controller:
            assert controller.is_enabled is True
            assert controller.current_state == PTTState.WAITING_FOR_KEY

        # After context exit
        assert controller.is_enabled is False
        assert controller.current_state == PTTState.IDLE

    def test_on_state_change_callback(self, ptt_logger):
        """Test state change callback is called"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # State change should have been logged
        state_changes = [
            e for e in ptt_logger.events
            if e.event_type == "state_change_callback"
        ]

        assert len(state_changes) > 0

    def test_recording_start_time_tracked(self):
        """Test recording start time is tracked"""
        controller = PTTController()
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")

        assert controller._recording_start_time is not None

    def test_recording_duration_logged(self, ptt_logger):
        """Test recording duration is logged"""
        import time

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")

        time.sleep(0.01)  # 10ms recording

        # Stop recording
        controller._state_machine.transition(PTTState.RECORDING_STOPPED, "stop")

        # Check duration was logged
        duration_events = [
            e for e in ptt_logger.events
            if e.event_type == "recording_duration"
        ]

        assert len(duration_events) == 1
        assert duration_events[0].data["duration_seconds"] > 0

    def test_error_logging_on_callback_exception(self, ptt_logger):
        """Test that callback exceptions are logged"""
        def bad_callback():
            raise RuntimeError("Callback failed")

        controller = PTTController(
            on_recording_start=bad_callback,
            logger=ptt_logger
        )
        controller.enable()

        # This should log the error, not crash
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        # Process the event
        import asyncio
        event = {"type": "start_recording", "timestamp": 0}

        async def run_test():
            await controller._handle_start_recording(event)

        asyncio.run(run_test())

        # Check error was logged
        errors = [e for e in ptt_logger.events if e.event_type == "error"]
        assert len(errors) > 0


class TestPTTControllerFactory:
    """Tests for create_ptt_controller factory"""

    def test_factory_creates_controller(self):
        """Test factory creates valid controller"""
        controller = create_ptt_controller()

        assert isinstance(controller, PTTController)
        assert controller.is_enabled is False

    def test_factory_with_params(self):
        """Test factory with custom parameters"""
        controller = create_ptt_controller(key_combo="space")

        assert controller._key_combo == "space"

    def test_factory_with_callbacks(self):
        """Test factory with callbacks"""
        start_called = []
        stop_called = []

        controller = create_ptt_controller(
            on_recording_start=lambda: start_called.append(True),
            on_recording_stop=lambda data: stop_called.append(data)
        )

        assert controller._on_recording_start is not None
        assert controller._on_recording_stop is not None


class TestPTTControllerIntegration:
    """Integration tests for full PTT flow"""

    @pytest.mark.asyncio
    async def test_full_recording_flow(self):
        """Test complete recording flow from enable to disable"""
        events = []

        def on_start():
            events.append("start")

        def on_stop(data):
            events.append("stop")

        controller = PTTController(
            key_combo="space",
            on_recording_start=on_start,
            on_recording_stop=on_stop
        )

        # Enable PTT
        controller.enable()
        assert controller.current_state == PTTState.WAITING_FOR_KEY

        # Simulate key press
        controller._on_key_press()
        assert controller.current_state == PTTState.KEY_PRESSED

        # Process start event
        event = await controller.wait_for_event(timeout=0.1)
        assert event is not None
        await controller._handle_start_recording(event)
        assert controller.current_state == PTTState.RECORDING
        assert "start" in events

        # Simulate key release
        controller._on_key_release()
        assert controller.current_state == PTTState.RECORDING_STOPPED

        # Process stop event
        event = await controller.wait_for_event(timeout=0.1)
        assert event is not None
        await controller._handle_stop_recording(event)
        assert controller.current_state == PTTState.WAITING_FOR_KEY
        assert "stop" in events

        # Disable
        controller.disable()
        assert controller.current_state == PTTState.IDLE

    @pytest.mark.asyncio
    async def test_quick_press_flow(self):
        """Test quick press and release (too short to record)"""
        controller = PTTController()
        controller.enable()

        # Quick press and release
        controller._on_key_press()
        controller._on_key_release()

        # Should be back to IDLE
        assert controller.current_state == PTTState.IDLE

    @pytest.mark.asyncio
    async def test_cancellation_flow(self):
        """Test cancelling a recording"""
        cancel_called = []

        def on_cancel():
            cancel_called.append(True)

        controller = PTTController(on_recording_cancel=on_cancel)
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Cancel
        controller._cancel_recording()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_cancel_recording(event)

        assert len(cancel_called) == 1
        assert controller.current_state == PTTState.WAITING_FOR_KEY

    def test_disable_while_recording_cancels(self):
        """Test that disabling while recording cancels it"""
        controller = PTTController()
        controller.enable()

        # Start recording
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")

        # Disable
        controller.disable()

        # Should be back to IDLE
        assert controller.current_state == PTTState.IDLE
        assert controller.is_enabled is False


class TestPTTControllerErrorRecovery:
    """Tests for error recovery and timeout handling"""

    @pytest.mark.asyncio
    async def test_timeout_monitoring(self, ptt_logger):
        """Test that recording is cancelled after timeout"""
        controller = PTTController(timeout=0.1, logger=ptt_logger)
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        # Start recording
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        assert controller.is_recording is True
        assert controller._timeout_task is not None

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Should have timed out and cancelled
        timeout_events = [
            e for e in ptt_logger.events
            if e.event_type == "recording_timeout"
        ]
        assert len(timeout_events) >= 1

    @pytest.mark.asyncio
    async def test_timeout_task_cancelled_on_stop(self):
        """Test that timeout task is cancelled when recording stops normally"""
        controller = PTTController(timeout=10.0)
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        timeout_task = controller._timeout_task
        assert timeout_task is not None
        assert not timeout_task.done()

        # Stop recording
        controller._state_machine.transition(PTTState.RECORDING_STOPPED, "stop")
        event = {"type": "stop_recording", "timestamp": 0}
        await controller._handle_stop_recording(event)

        # Timeout task should be cancelled
        assert timeout_task.cancelled() or timeout_task.done()

    @pytest.mark.asyncio
    async def test_timeout_task_cancelled_on_cancel(self):
        """Test that timeout task is cancelled when recording is cancelled"""
        controller = PTTController(timeout=10.0)
        controller.enable()

        # Get to RECORDING state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        timeout_task = controller._timeout_task
        assert timeout_task is not None

        # Cancel recording
        controller._state_machine.transition(PTTState.RECORDING_CANCELLED, "cancel")
        event = {"type": "cancel_recording", "timestamp": 0}
        await controller._handle_cancel_recording(event)

        # Timeout task should be cancelled
        assert timeout_task.cancelled() or timeout_task.done()

    @pytest.mark.asyncio
    async def test_error_recovery_on_start_failure(self, ptt_logger):
        """Test automatic recovery when start recording fails"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Make recorder.start() fail once then succeed
        call_count = [0]

        async def failing_start():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Audio device busy")
            return True

        controller._recorder.start = failing_start

        # Get to KEY_PRESSED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        # Handle start event
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        # Should have recovered and be in RECORDING state
        assert controller.current_state == PTTState.RECORDING
        assert call_count[0] == 2  # Called twice (fail + retry)

        # Check recovery was logged
        recovery_events = [
            e for e in ptt_logger.events
            if e.event_type == "attempting_recovery"
        ]
        assert len(recovery_events) == 1

    @pytest.mark.asyncio
    async def test_error_recovery_fails_after_max_retries(self, ptt_logger):
        """Test that recovery fails after max retries"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()
        controller._max_retries = 2

        # Make recorder.start() always fail
        async def always_fail():
            raise RuntimeError("Permanent audio device failure")

        controller._recorder.start = always_fail

        # Get to KEY_PRESSED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")

        # Handle start event
        event = {"type": "start_recording", "timestamp": 0}
        await controller._handle_start_recording(event)

        # Should have returned to IDLE after failed recovery
        assert controller.current_state == PTTState.IDLE
        assert controller._retry_count == 0  # Reset after failure

        # Check recovery failure was logged
        failure_events = [
            e for e in ptt_logger.events
            if e.event_type == "recovery_failed"
        ]
        assert len(failure_events) == 1

    @pytest.mark.asyncio
    async def test_error_recovery_on_stop_failure(self, ptt_logger):
        """Test recovery when stop recording fails"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Get to RECORDING_STOPPED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")
        controller._state_machine.transition(PTTState.RECORDING_STOPPED, "stop")

        # Make stop fail once then succeed
        call_count = [0]

        async def failing_stop():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Stop failed")
            return np.array([1, 2, 3])

        controller._recorder.stop = failing_stop

        # Handle stop event
        event = {"type": "stop_recording", "timestamp": 0}
        await controller._handle_stop_recording(event)

        # Should have recovered
        assert call_count[0] == 2  # Called twice

        # Check recovery was logged
        recovery_events = [
            e for e in ptt_logger.events
            if e.event_type == "attempting_recovery"
        ]
        assert len(recovery_events) == 1

    @pytest.mark.asyncio
    async def test_retry_count_reset_on_success(self):
        """Test that retry count resets after successful operation"""
        controller = PTTController()
        controller.enable()

        # Simulate some retries
        controller._retry_count = 2

        # Get to RECORDING_STOPPED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")
        controller._state_machine.transition(PTTState.RECORDING_STOPPED, "stop")

        # Handle successful stop
        event = {"type": "stop_recording", "timestamp": 0}
        await controller._handle_stop_recording(event)

        # Retry count should be reset
        assert controller._retry_count == 0

    @pytest.mark.asyncio
    async def test_recovery_attempts_recorder_cancel(self, ptt_logger):
        """Test that recovery attempts to cancel recorder"""
        controller = PTTController(logger=ptt_logger)

        # Mock recorder in recording state
        controller._recorder._is_recording = True
        cancel_called = [False]

        async def mock_cancel():
            cancel_called[0] = True

        controller._recorder.cancel = mock_cancel

        # Trigger recovery
        await controller._recover_from_error("test_op", RuntimeError("test"))

        # Should have called cancel
        assert cancel_called[0] is True

    @pytest.mark.asyncio
    async def test_recovery_handles_cancel_failure(self, ptt_logger):
        """Test that recovery handles cancel failures gracefully"""
        controller = PTTController(logger=ptt_logger)

        # Mock recorder that fails on cancel
        controller._recorder._is_recording = True

        async def failing_cancel():
            raise RuntimeError("Cancel failed")

        controller._recorder.cancel = failing_cancel

        # Should not raise
        result = await controller._recover_from_error("test_op", RuntimeError("test"))

        # Recovery should still succeed despite cancel failure
        assert result is True

    @pytest.mark.asyncio
    async def test_error_recovery_on_cancel_failure(self, ptt_logger):
        """Test recovery when cancel recording fails"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Get to RECORDING_CANCELLED state
        controller._state_machine.transition(PTTState.KEY_PRESSED, "key_down")
        controller._state_machine.transition(PTTState.RECORDING, "start")
        controller._state_machine.transition(PTTState.RECORDING_CANCELLED, "cancel")

        # Make cancel fail once then succeed
        call_count = [0]

        async def failing_cancel():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Cancel failed")

        controller._recorder.cancel = failing_cancel

        # Handle cancel event
        event = {"type": "cancel_recording", "timestamp": 0}
        await controller._handle_cancel_recording(event)

        # Should have attempted recovery
        assert call_count[0] == 2

        # Check recovery was logged
        recovery_events = [
            e for e in ptt_logger.events
            if e.event_type == "attempting_recovery"
        ]
        assert len(recovery_events) == 1


class TestPTTControllerHoldMode:
    """Tests for hold mode (press-and-hold) functionality"""

    def test_hold_mode_configuration(self):
        """Test that hold mode is configured correctly"""
        controller = PTTController()

        assert controller._mode == "hold"
        assert controller._min_duration > 0

    @pytest.mark.asyncio
    async def test_hold_mode_press_and_hold_flow(self, ptt_logger):
        """Test complete press-and-hold recording flow"""
        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Press key
        controller._on_key_press()
        assert controller.current_state == PTTState.KEY_PRESSED
        assert controller._key_press_time is not None

        # Process start event
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"
        await controller._handle_start_recording(event)
        assert controller.current_state == PTTState.RECORDING

        # Hold for minimum duration
        await asyncio.sleep(0.1)

        # Release key
        controller._on_key_release()
        assert controller.current_state == PTTState.RECORDING_STOPPED

        # Check key released event was logged
        release_events = [
            e for e in ptt_logger.events
            if e.event_type == "key_released"
        ]
        assert len(release_events) == 1
        assert release_events[0].data["state"] == "recording"

    def test_hold_mode_quick_release_below_minimum(self, ptt_logger):
        """Test that quick release below minimum duration cancels"""
        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.5  # 500ms minimum
        controller.enable()

        # Press key
        controller._on_key_press()
        press_time = controller._key_press_time

        # Immediately release (well below 500ms)
        controller._on_key_release()

        # Should be back to IDLE
        assert controller.current_state == PTTState.IDLE

        # Check quick release was logged
        quick_release_events = [
            e for e in ptt_logger.events
            if e.event_type == "quick_release"
        ]
        assert len(quick_release_events) == 1
        assert quick_release_events[0].data["hold_duration_seconds"] < 0.5
        assert quick_release_events[0].data["min_duration_seconds"] == 0.5

    @pytest.mark.asyncio
    async def test_hold_mode_release_after_minimum_before_recording(self, ptt_logger):
        """Test release after minimum duration but before recording starts"""
        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.01  # 10ms minimum
        controller.enable()

        # Press key
        controller._on_key_press()
        assert controller.current_state == PTTState.KEY_PRESSED

        # Wait for minimum duration but don't process start event
        await asyncio.sleep(0.02)

        # Release key (still in KEY_PRESSED state, not RECORDING)
        controller._on_key_release()

        # Should be back to IDLE
        assert controller.current_state == PTTState.IDLE

        # Check released_before_recording event was logged
        release_events = [
            e for e in ptt_logger.events
            if e.event_type == "released_before_recording"
        ]
        assert len(release_events) == 1

    @pytest.mark.asyncio
    async def test_hold_mode_press_time_tracking(self):
        """Test that press time is tracked correctly"""
        import time
        controller = PTTController()
        controller.enable()

        before_press = time.time()
        controller._on_key_press()
        after_press = time.time()

        assert controller._key_press_time is not None
        assert before_press <= controller._key_press_time <= after_press

    @pytest.mark.asyncio
    async def test_hold_mode_press_time_cleared_on_quick_release(self):
        """Test that press time is cleared after quick release"""
        controller = PTTController()
        controller._min_duration = 1.0  # 1 second minimum
        controller.enable()

        controller._on_key_press()
        assert controller._key_press_time is not None

        # Quick release
        controller._on_key_release()

        # Press time should be cleared
        assert controller._key_press_time is None

    @pytest.mark.asyncio
    async def test_hold_mode_duration_calculation(self, ptt_logger):
        """Test that hold duration is calculated correctly"""
        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.05  # 50ms
        controller.enable()

        # Press and start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Hold for a specific duration
        await asyncio.sleep(0.1)  # 100ms

        # Release
        controller._on_key_release()

        # Check logged duration
        release_events = [
            e for e in ptt_logger.events
            if e.event_type == "key_released"
        ]
        assert len(release_events) == 1
        # Should be around 100ms (with some tolerance)
        assert 0.08 <= release_events[0].data["hold_duration_seconds"] <= 0.15

    @pytest.mark.asyncio
    async def test_hold_mode_multiple_press_release_cycles(self, ptt_logger):
        """Test multiple press-release cycles"""
        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.01
        controller.enable()

        for i in range(3):
            # Press
            controller._on_key_press()
            assert controller._key_press_time is not None

            # Start recording
            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_start_recording(event)

            # Wait
            await asyncio.sleep(0.02)

            # Release
            controller._on_key_release()

            # Process stop event
            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_stop_recording(event)

            # Should be back to WAITING_FOR_KEY
            assert controller.current_state == PTTState.WAITING_FOR_KEY

        # Check we have 3 release events
        release_events = [
            e for e in ptt_logger.events
            if e.event_type == "key_released"
        ]
        assert len(release_events) == 3

    def test_hold_mode_zero_minimum_duration(self):
        """Test that zero minimum duration allows immediate release"""
        controller = PTTController()
        controller._min_duration = 0.0
        controller.enable()

        # Press and immediately release
        controller._on_key_press()
        controller._on_key_release()

        # Should not trigger quick_release since minimum is 0
        assert controller.current_state == PTTState.IDLE

    @pytest.mark.asyncio
    async def test_hold_mode_long_hold(self, ptt_logger):
        """Test holding for extended period"""
        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.01
        controller.enable()

        # Press
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Hold for longer period
        await asyncio.sleep(0.2)

        # Release
        controller._on_key_release()

        # Check duration
        release_events = [
            e for e in ptt_logger.events
            if e.event_type == "key_released"
        ]
        assert len(release_events) == 1
        assert release_events[0].data["hold_duration_seconds"] >= 0.2


class TestPTTControllerToggleMode:
    """Tests for toggle mode (press to start/stop) functionality"""

    def test_toggle_mode_configuration(self):
        """Test that controller can be configured for toggle mode"""
        # Temporarily set mode to toggle
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController()
        assert controller._mode == "toggle"

        # Restore original
        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_start_recording(self, ptt_logger):
        """Test first press starts recording in toggle mode"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # First press should start recording
        controller._on_key_press()

        assert controller.current_state == PTTState.KEY_PRESSED
        assert controller._toggle_active is True

        # Check toggle_started event was logged
        toggle_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_started"
        ]
        assert len(toggle_events) == 1

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_stop_recording(self, ptt_logger):
        """Test second press stops recording in toggle mode"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # First press - start
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        assert controller.current_state == PTTState.RECORDING
        assert controller._toggle_active is True

        # Second press - stop
        controller._on_key_press()

        assert controller.current_state == PTTState.RECORDING_STOPPED
        assert controller._toggle_active is False

        # Check toggle_stopped event was logged
        toggle_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_stopped"
        ]
        assert len(toggle_events) == 1

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_ignores_key_release(self):
        """Test that toggle mode ignores key release events"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController()
        controller.enable()

        # Press to start
        controller._on_key_press()
        initial_state = controller.current_state

        # Release should be ignored
        controller._on_key_release()

        # State should not change
        assert controller.current_state == initial_state

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_full_cycle(self, ptt_logger):
        """Test complete toggle mode cycle: press, record, press, stop"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # First press - start
        controller._on_key_press()
        assert controller._toggle_active is True

        # Process start event
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)
        assert controller.current_state == PTTState.RECORDING

        # Simulate recording for a bit
        await asyncio.sleep(0.05)

        # Second press - stop
        controller._on_key_press()
        assert controller._toggle_active is False

        # Process stop event
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Should be back to WAITING_FOR_KEY
        assert controller.current_state == PTTState.WAITING_FOR_KEY

        # Check both toggle events were logged
        start_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_started"
        ]
        stop_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_stopped"
        ]
        assert len(start_events) == 1
        assert len(stop_events) == 1

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_multiple_cycles(self, ptt_logger):
        """Test multiple toggle on/off cycles"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        for i in range(3):
            # Toggle on
            controller._on_key_press()
            assert controller._toggle_active is True

            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_start_recording(event)

            await asyncio.sleep(0.02)

            # Toggle off
            controller._on_key_press()
            assert controller._toggle_active is False

            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_stop_recording(event)

            assert controller.current_state == PTTState.WAITING_FOR_KEY

        # Check we have 3 start and 3 stop events
        start_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_started"
        ]
        stop_events = [
            e for e in ptt_logger.events
            if e.event_type == "toggle_stopped"
        ]
        assert len(start_events) == 3
        assert len(stop_events) == 3

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_press_while_not_recording_ignored(self):
        """Test that extra presses in wrong state are ignored"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController()
        controller.enable()

        # First press should work
        controller._on_key_press()
        assert controller.current_state == PTTState.KEY_PRESSED

        # Second press while still in KEY_PRESSED (not RECORDING) should be ignored
        controller._on_key_press()
        # State shouldn't change since we're not in RECORDING yet
        assert controller.current_state == PTTState.KEY_PRESSED

        config.PTT_MODE = original_mode

    def test_toggle_mode_state_persists_across_releases(self):
        """Test that toggle state persists even when key is released"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "toggle"

        controller = PTTController()
        controller.enable()

        # Press to activate toggle
        controller._on_key_press()
        assert controller._toggle_active is True

        # Release multiple times - should not affect toggle state
        for _ in range(5):
            controller._on_key_release()

        # Toggle should still be active
        assert controller._toggle_active is True

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_toggle_mode_vs_hold_mode_behavior(self):
        """Test that toggle and hold modes behave differently"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE

        # Test hold mode behavior
        config.PTT_MODE = "hold"
        hold_controller = PTTController()
        hold_controller.enable()

        hold_controller._on_key_press()
        hold_press_state = hold_controller.current_state

        hold_controller._on_key_release()
        # In hold mode, quick release changes state
        hold_release_state = hold_controller.current_state

        # Test toggle mode behavior
        config.PTT_MODE = "toggle"
        toggle_controller = PTTController()
        toggle_controller.enable()

        toggle_controller._on_key_press()
        toggle_press_state = toggle_controller.current_state

        toggle_controller._on_key_release()
        # In toggle mode, release is ignored
        toggle_release_state = toggle_controller.current_state

        # States should be different after release
        # Hold mode: press then release changes state
        # Toggle mode: press then release keeps state
        assert hold_press_state == toggle_press_state  # Both KEY_PRESSED initially
        assert hold_release_state != toggle_release_state  # Different after release

        config.PTT_MODE = original_mode


class TestPTTControllerHybridMode:
    """Tests for hybrid mode (hold + silence detection) functionality"""

    def test_hybrid_mode_configuration(self):
        """Test that hybrid mode is configured correctly"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController()

        assert controller._mode == "hybrid"
        assert controller._hybrid_silence_timeout > 0

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_starts_like_hold_mode(self, ptt_logger):
        """Test that hybrid mode starts recording like hold mode"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Press key (like hold mode)
        controller._on_key_press()

        assert controller.current_state == PTTState.KEY_PRESSED
        assert controller._key_press_time is not None

        # Check hybrid_started event was logged
        hybrid_events = [
            e for e in ptt_logger.events
            if e.event_type == "hybrid_started"
        ]
        assert len(hybrid_events) == 1

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_auto_stop_on_silence(self, ptt_logger):
        """Test that hybrid mode auto-stops after silence timeout"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        original_silence = config.SILENCE_THRESHOLD_MS
        config.PTT_MODE = "hybrid"
        config.SILENCE_THRESHOLD_MS = 100  # 100ms for fast testing

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 0.1  # 100ms
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        assert controller.current_state == PTTState.RECORDING
        assert controller._hybrid_silence_task is not None

        # Wait for silence timeout
        await asyncio.sleep(0.15)

        # Check that silence was detected
        silence_events = [
            e for e in ptt_logger.events
            if e.event_type == "hybrid_silence_detected"
        ]
        assert len(silence_events) == 1

        config.PTT_MODE = original_mode
        config.SILENCE_THRESHOLD_MS = original_silence

    @pytest.mark.asyncio
    async def test_hybrid_mode_manual_stop_on_release(self, ptt_logger):
        """Test that hybrid mode can be stopped manually by releasing key"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 10.0  # Long timeout
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        silence_task = controller._hybrid_silence_task
        assert silence_task is not None
        assert not silence_task.done()

        # Release key (manual stop)
        controller._on_key_release()
        assert controller.current_state == PTTState.RECORDING_STOPPED

        # Process stop event
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Silence task should be cancelled
        assert silence_task.cancelled() or silence_task.done()

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_minimum_duration_enforcement(self, ptt_logger):
        """Test that hybrid mode enforces minimum hold duration"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController(logger=ptt_logger)
        controller._min_duration = 0.5  # 500ms minimum
        controller.enable()

        # Press and immediately release (below minimum)
        controller._on_key_press()
        controller._on_key_release()

        # Should be back to IDLE (quick release)
        assert controller.current_state == PTTState.IDLE

        # Check quick release was logged
        quick_release_events = [
            e for e in ptt_logger.events
            if e.event_type == "quick_release"
        ]
        assert len(quick_release_events) == 1

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_full_cycle_with_manual_stop(self, ptt_logger):
        """Test complete hybrid mode cycle with manual stop"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 10.0
        controller._min_duration = 0.01
        controller.enable()

        # Press
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        assert controller.current_state == PTTState.RECORDING

        # Wait a bit
        await asyncio.sleep(0.05)

        # Release (manual stop)
        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        assert controller.current_state == PTTState.WAITING_FOR_KEY

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_silence_monitor_cleanup(self):
        """Test that silence monitor is properly cleaned up"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController()
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        task = controller._hybrid_silence_task
        assert task is not None

        # Stop manually
        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Task should be cancelled
        assert task.cancelled() or task.done()

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_vs_hold_mode_behavior(self):
        """Test that hybrid differs from hold only in silence detection"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE

        # Test hold mode (no silence monitor)
        config.PTT_MODE = "hold"
        hold_controller = PTTController()
        hold_controller.enable()

        hold_controller._on_key_press()
        event = await hold_controller.wait_for_event(timeout=0.1)
        await hold_controller._handle_start_recording(event)

        # No silence task in hold mode
        assert hold_controller._hybrid_silence_task is None

        # Test hybrid mode (has silence monitor)
        config.PTT_MODE = "hybrid"
        hybrid_controller = PTTController()
        hybrid_controller.enable()

        hybrid_controller._on_key_press()
        event = await hybrid_controller.wait_for_event(timeout=0.1)
        await hybrid_controller._handle_start_recording(event)

        # Has silence task in hybrid mode
        assert hybrid_controller._hybrid_silence_task is not None

        config.PTT_MODE = original_mode

    @pytest.mark.asyncio
    async def test_hybrid_mode_cancel_stops_silence_monitor(self):
        """Test that cancelling recording stops silence monitor"""
        import voice_mode.config as config
        original_mode = config.PTT_MODE
        config.PTT_MODE = "hybrid"

        controller = PTTController()
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Move to RECORDING_CANCELLED state
        controller._state_machine.transition(PTTState.RECORDING_CANCELLED, "cancel")

        task = controller._hybrid_silence_task
        assert task is not None

        # Cancel
        event = {"type": "cancel_recording", "timestamp": 0}
        await controller._handle_cancel_recording(event)

        # Silence task should be cancelled
        assert task.cancelled() or task.done()

        config.PTT_MODE = original_mode
