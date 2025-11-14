"""
Integration tests for PTT (Push-to-Talk) system.

These tests verify the full PTT system works correctly across different
modes and scenarios, including cross-mode workflows, error recovery,
and resource cleanup.
"""

import pytest
import asyncio
import time
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from voice_mode import config
from voice_mode.ptt import (
    PTTController,
    PTTState,
    get_ptt_logger,
    reset_ptt_logger,
)


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
        # Create a mock stream
        mock_stream = MagicMock()
        mock_stream.start.return_value = None
        mock_stream.stop.return_value = None
        mock_stream.close.return_value = None

        # Mock InputStream to return our mock stream
        mock_sd.InputStream.return_value = mock_stream

        yield mock_sd


@pytest.fixture
def ptt_logger():
    """Create a fresh PTT logger for each test"""
    reset_ptt_logger()
    logger = get_ptt_logger()
    yield logger
    reset_ptt_logger()


@pytest.fixture
def reset_config():
    """Reset config to defaults after each test"""
    original_mode = config.PTT_MODE
    original_timeout = config.PTT_TIMEOUT
    original_silence = config.SILENCE_THRESHOLD_MS
    yield
    config.PTT_MODE = original_mode
    config.PTT_TIMEOUT = original_timeout
    config.SILENCE_THRESHOLD_MS = original_silence


class TestCrossModeWorkflows:
    """Test switching between different PTT modes"""

    @pytest.mark.asyncio
    async def test_switch_from_hold_to_toggle_mode(self, ptt_logger, reset_config):
        """Test switching from hold to toggle mode"""
        # Start in hold mode
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.1

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Record in hold mode
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        await controller._handle_start_recording(event)
        assert controller.is_recording

        # Wait minimum duration
        await asyncio.sleep(0.15)

        # Release key
        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "stop_recording"

        await controller._handle_stop_recording(event)
        assert not controller.is_recording

        # Switch to toggle mode
        controller.disable()
        config.PTT_MODE = "toggle"
        controller_toggle = PTTController(logger=ptt_logger)
        controller_toggle.enable()

        # First press starts recording
        controller_toggle._on_key_press()
        event = await controller_toggle.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        await controller_toggle._handle_start_recording(event)
        assert controller_toggle.is_recording

        # Second press stops recording
        controller_toggle._on_key_press()
        event = await controller_toggle.wait_for_event(timeout=0.1)
        assert event["type"] == "stop_recording"

        controller_toggle.disable()

    @pytest.mark.asyncio
    async def test_switch_from_toggle_to_hybrid_mode(self, ptt_logger, reset_config):
        """Test switching from toggle to hybrid mode"""
        # Start in toggle mode
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Toggle on
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)
        assert controller.is_recording

        # Toggle off
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)
        assert not controller.is_recording

        controller.disable()

        # Switch to hybrid mode
        config.PTT_MODE = "hybrid"
        config.SILENCE_THRESHOLD_MS = 100

        controller_hybrid = PTTController(logger=ptt_logger)
        controller_hybrid._hybrid_silence_timeout = 0.1
        controller_hybrid.enable()

        # Press key (hybrid works like hold)
        controller_hybrid._on_key_press()
        event = await controller_hybrid.wait_for_event(timeout=0.1)
        await controller_hybrid._handle_start_recording(event)
        assert controller_hybrid.is_recording

        # Wait for silence timeout
        await asyncio.sleep(0.15)

        # Should auto-stop on silence
        silence_events = [
            e for e in ptt_logger.events
            if e.event_type == "hybrid_silence_detected"
        ]
        assert len(silence_events) > 0

        controller_hybrid.disable()


class TestFullRecordingCycles:
    """Test complete recording workflows for all modes"""

    @pytest.mark.asyncio
    async def test_hold_mode_full_cycle(self, ptt_logger, reset_config):
        """Test complete hold mode recording cycle"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.1

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Press key
        controller._key_press_time = time.time()
        controller._on_key_press()

        # Wait for start event
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        # Handle start
        await controller._handle_start_recording(event)
        assert controller.is_recording
        assert controller.current_state == PTTState.RECORDING

        # Add some audio data
        controller._recorder._recorder._audio_chunks = [
            np.array([1, 2, 3, 4, 5], dtype='int16')
        ]

        # Wait minimum duration
        await asyncio.sleep(0.15)

        # Release key
        controller._on_key_release()

        # Wait for stop event
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "stop_recording"

        # Handle stop (automatically transitions through PROCESSING to IDLE)
        await controller._handle_stop_recording(event)
        assert not controller.is_recording
        # Should be back in WAITING_FOR_KEY or IDLE
        assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]

        controller.disable()

    @pytest.mark.asyncio
    async def test_toggle_mode_full_cycle(self, ptt_logger, reset_config):
        """Test complete toggle mode recording cycle"""
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # First press - start
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        await controller._handle_start_recording(event)
        assert controller.is_recording
        assert controller._toggle_active

        # Add audio data
        controller._recorder._recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16')
        ]

        # Second press - stop
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "stop_recording"

        await controller._handle_stop_recording(event)
        assert not controller.is_recording
        assert not controller._toggle_active
        # Should be back in WAITING_FOR_KEY or IDLE
        assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]

        controller.disable()

    @pytest.mark.asyncio
    async def test_hybrid_mode_full_cycle_with_silence(self, ptt_logger, reset_config):
        """Test complete hybrid mode cycle with silence detection"""
        config.PTT_MODE = "hybrid"
        config.SILENCE_THRESHOLD_MS = 100

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 0.1
        controller.enable()

        # Press key
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        await controller._handle_start_recording(event)
        assert controller.is_recording

        # Add audio data
        controller._recorder._recorder._audio_chunks = [
            np.array([1, 2, 3, 4], dtype='int16')
        ]

        # Wait for silence timeout
        await asyncio.sleep(0.15)

        # Verify silence was detected
        silence_events = [
            e for e in ptt_logger.events
            if e.event_type == "hybrid_silence_detected"
        ]
        assert len(silence_events) == 1

        # Should auto-transition to stopped
        event = await controller.wait_for_event(timeout=0.1)
        if event["type"] == "stop_recording":
            await controller._handle_stop_recording(event)

        controller.disable()


class TestErrorRecovery:
    """Test error recovery across different scenarios"""

    @pytest.mark.asyncio
    async def test_recording_start_failure_recovery(self, ptt_logger, reset_config):
        """Test recovery from recording start failure"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.1

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Make recorder.start() consistently raise exceptions (even on retry)
        call_count = 0
        async def failing_start():
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"Recording start failed (attempt {call_count})")

        with patch.object(controller._recorder, 'start', side_effect=failing_start):
            controller._key_press_time = time.time()
            controller._on_key_press()

            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_start_recording(event)

            # Error recovery should have attempted multiple tries
            assert call_count >= 1  # At least one attempt
            # The key is that controller should be ready for next attempt after failure
            assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]
            assert not controller.is_recording

        controller.disable()

    @pytest.mark.asyncio
    async def test_recording_stop_failure_recovery(self, ptt_logger, reset_config):
        """Test recovery from recording stop failure"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.1

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Start recording successfully
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        await asyncio.sleep(0.15)

        # Make recorder.stop() return None (no audio data)
        with patch.object(controller._recorder, 'stop', return_value=None):
            controller._on_key_release()
            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_stop_recording(event)

            # Should handle None audio data gracefully and recover
            # Controller should be back in waiting or idle state
            assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]

        controller.disable()

    @pytest.mark.asyncio
    async def test_invalid_state_transition_recovery(self, ptt_logger, reset_config):
        """Test recovery from invalid state transitions"""
        config.PTT_MODE = "hold"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Try to stop without starting
        controller._on_key_release()

        # Should not crash, should stay in waiting state
        assert controller.current_state == PTTState.WAITING_FOR_KEY

        # Should still be able to record properly
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        assert event["type"] == "start_recording"

        controller.disable()


class TestConcurrentOperations:
    """Test concurrent operations and race conditions"""

    @pytest.mark.asyncio
    async def test_rapid_key_presses(self, ptt_logger, reset_config):
        """Test rapid key press/release events"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.05

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Rapid press/release cycles
        for _ in range(3):
            controller._key_press_time = time.time()
            controller._on_key_press()

            try:
                event = await controller.wait_for_event(timeout=0.05)
                if event["type"] == "start_recording":
                    await controller._handle_start_recording(event)
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.06)

            controller._on_key_release()

            try:
                event = await controller.wait_for_event(timeout=0.05)
                if event["type"] == "stop_recording":
                    await controller._handle_stop_recording(event)
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.05)

        # Should still be functional
        assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]

        controller.disable()

    @pytest.mark.asyncio
    async def test_timeout_and_silence_interaction(self, ptt_logger, reset_config):
        """Test interaction between timeout and silence detection"""
        config.PTT_MODE = "hybrid"
        config.PTT_TIMEOUT = 0.3  # 300ms timeout
        config.SILENCE_THRESHOLD_MS = 200  # 200ms silence

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 0.2
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Wait to see which triggers first (silence should win)
        await asyncio.sleep(0.25)

        # Check which event triggered
        silence_events = [
            e for e in ptt_logger.events
            if e.event_type == "hybrid_silence_detected"
        ]
        timeout_events = [
            e for e in ptt_logger.events
            if e.event_type == "timeout_exceeded"
        ]

        # At least one should have triggered
        assert len(silence_events) + len(timeout_events) > 0

        controller.disable()


class TestResourceCleanup:
    """Test proper resource cleanup in various scenarios"""

    @pytest.mark.asyncio
    async def test_cleanup_on_normal_stop(self, ptt_logger, reset_config):
        """Test resources are cleaned up on normal stop"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.1

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Record and stop
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        await asyncio.sleep(0.15)

        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Verify cleanup
        assert not controller.is_recording
        assert controller._timeout_task is None or controller._timeout_task.done()

        controller.disable()

    @pytest.mark.asyncio
    async def test_cleanup_on_cancel(self, ptt_logger, reset_config):
        """Test resources are cleaned up on cancel"""
        config.PTT_MODE = "hold"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Start recording
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Trigger cancel by putting cancel event in queue
        controller._event_queue.put({"type": "cancel_recording", "timestamp": time.time()})
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_cancel_recording(event)

        # Verify cleanup
        assert not controller.is_recording
        # Should be back in WAITING_FOR_KEY since controller is still enabled
        assert controller.current_state in [PTTState.IDLE, PTTState.WAITING_FOR_KEY]
        assert controller._timeout_task is None or controller._timeout_task.done()

        controller.disable()

    @pytest.mark.asyncio
    async def test_cleanup_on_disable(self, ptt_logger, reset_config):
        """Test resources are cleaned up on disable"""
        config.PTT_MODE = "toggle"

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Start recording
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Disable while recording
        controller.disable()

        # Verify cleanup
        assert not controller._enabled
        assert not controller.is_recording
        assert controller.current_state == PTTState.IDLE

    @pytest.mark.asyncio
    async def test_cleanup_hybrid_silence_monitor(self, ptt_logger, reset_config):
        """Test hybrid silence monitor is properly cleaned up"""
        config.PTT_MODE = "hybrid"
        config.SILENCE_THRESHOLD_MS = 100

        controller = PTTController(logger=ptt_logger)
        controller._hybrid_silence_timeout = 0.1
        controller.enable()

        # Start recording (starts silence monitor)
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        assert controller._hybrid_silence_task is not None
        assert not controller._hybrid_silence_task.done()

        # Trigger cancel
        controller._event_queue.put({"type": "cancel_recording", "timestamp": time.time()})
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_cancel_recording(event)

        # Verify silence monitor is cancelled
        if controller._hybrid_silence_task:
            assert controller._hybrid_silence_task.cancelled() or controller._hybrid_silence_task.done()

        controller.disable()


class TestTimeoutInteractions:
    """Test timeout behavior in different modes"""

    @pytest.mark.asyncio
    async def test_timeout_in_hold_mode(self, ptt_logger, reset_config):
        """Test timeout works correctly in hold mode"""
        config.PTT_MODE = "hold"
        config.PTT_TIMEOUT = 0.15  # 150ms timeout
        config.PTT_MIN_DURATION = 0.05

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Start recording
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Verify timeout task was created
        assert controller._timeout_task is not None

        # Wait for timeout to trigger and handle cancellation
        await asyncio.sleep(0.2)

        # The timeout should have triggered the cancel_recording event
        # Wait for and process that event
        try:
            event = await controller.wait_for_event(timeout=0.2)
            if event and event["type"] == "cancel_recording":
                # Only handle if not already cancelled
                if controller.current_state == PTTState.RECORDING:
                    await controller._handle_cancel_recording(event)
        except asyncio.TimeoutError:
            # Timeout already processed the event
            pass

        # Should have auto-cancelled
        assert not controller.is_recording

        controller.disable()

    @pytest.mark.asyncio
    async def test_timeout_in_toggle_mode(self, ptt_logger, reset_config):
        """Test timeout works correctly in toggle mode"""
        config.PTT_MODE = "toggle"
        config.PTT_TIMEOUT = 0.15

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # Toggle on
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        # Verify timeout task was created
        assert controller._timeout_task is not None

        # Wait for timeout to trigger and handle cancellation
        await asyncio.sleep(0.2)

        # The timeout should have triggered the cancel_recording event
        # Wait for and process that event
        try:
            event = await controller.wait_for_event(timeout=0.2)
            if event and event["type"] == "cancel_recording":
                # Only handle if not already cancelled
                if controller.current_state == PTTState.RECORDING:
                    await controller._handle_cancel_recording(event)
        except asyncio.TimeoutError:
            # Timeout already processed the event
            pass

        # Should have auto-cancelled
        assert not controller.is_recording
        assert not controller._toggle_active

        controller.disable()


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_multiple_recordings_same_controller(self, ptt_logger, reset_config):
        """Test multiple sequential recordings with same controller"""
        config.PTT_MODE = "hold"
        config.PTT_MIN_DURATION = 0.05

        controller = PTTController(logger=ptt_logger)
        controller.enable()

        # First recording
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        controller._recorder._recorder._audio_chunks = [
            np.array([1, 2, 3], dtype='int16')
        ]

        await asyncio.sleep(0.06)
        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Second recording
        controller._key_press_time = time.time()
        controller._on_key_press()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_start_recording(event)

        controller._recorder._recorder._audio_chunks = [
            np.array([4, 5, 6], dtype='int16')
        ]

        await asyncio.sleep(0.06)
        controller._on_key_release()
        event = await controller.wait_for_event(timeout=0.1)
        await controller._handle_stop_recording(event)

        # Both should succeed
        recording_events = [
            e for e in ptt_logger.events
            if e.event_type == "recording_started"
        ]
        assert len(recording_events) == 2

        controller.disable()

    @pytest.mark.asyncio
    async def test_mode_specific_behavior_consistency(self, ptt_logger, reset_config):
        """Test each mode maintains consistent behavior"""
        modes_to_test = ["hold", "toggle", "hybrid"]

        for mode in modes_to_test:
            reset_ptt_logger()
            logger = get_ptt_logger()

            config.PTT_MODE = mode
            config.PTT_MIN_DURATION = 0.05
            config.SILENCE_THRESHOLD_MS = 100

            controller = PTTController(logger=logger)
            if mode == "hybrid":
                controller._hybrid_silence_timeout = 0.1
            controller.enable()

            # Start recording
            controller._key_press_time = time.time()
            controller._on_key_press()
            event = await controller.wait_for_event(timeout=0.1)
            await controller._handle_start_recording(event)

            assert controller.is_recording, f"Failed to start recording in {mode} mode"

            # Clean up
            if mode == "toggle":
                controller._on_key_press()  # Toggle off
            elif mode == "hold":
                await asyncio.sleep(0.06)
                controller._on_key_release()
            else:  # hybrid
                await asyncio.sleep(0.15)  # Let silence trigger

            controller.disable()

            # Verify mode-specific events
            mode_events = [
                e for e in logger.events
                if mode in str(e.event_type) or mode in str(e.data)
            ]
            # Each mode should have logged mode-specific info
            assert len(mode_events) > 0, f"No mode-specific events for {mode}"
