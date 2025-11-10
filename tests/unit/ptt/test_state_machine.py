"""
Tests for PTT state machine.

This module tests the state machine implementation for Push-to-Talk,
including state transitions, validation, and error handling.
"""

import pytest
import time
from voice_mode.ptt import (
    PTTState,
    PTTStateMachine,
    StateTransition,
    create_ptt_state_machine
)


class TestPTTState:
    """Tests for PTTState enum"""

    def test_state_values(self):
        """Test that all states have correct string values"""
        assert PTTState.IDLE.value == "IDLE"
        assert PTTState.WAITING_FOR_KEY.value == "WAITING_FOR_KEY"
        assert PTTState.KEY_PRESSED.value == "KEY_PRESSED"
        assert PTTState.RECORDING.value == "RECORDING"
        assert PTTState.RECORDING_STOPPED.value == "RECORDING_STOPPED"
        assert PTTState.RECORDING_CANCELLED.value == "RECORDING_CANCELLED"
        assert PTTState.PROCESSING.value == "PROCESSING"

    def test_state_count(self):
        """Test that we have exactly 7 states"""
        assert len(PTTState) == 7


class TestStateTransition:
    """Tests for StateTransition dataclass"""

    def test_basic_transition(self):
        """Test creating a basic state transition"""
        transition = StateTransition(
            from_state=PTTState.IDLE,
            to_state=PTTState.WAITING_FOR_KEY,
            trigger="enable_ptt"
        )

        assert transition.from_state == PTTState.IDLE
        assert transition.to_state == PTTState.WAITING_FOR_KEY
        assert transition.trigger == "enable_ptt"
        assert transition.guard is None
        assert transition.action is None

    def test_transition_with_guard(self):
        """Test transition with guard condition"""
        guard_fn = lambda: True

        transition = StateTransition(
            from_state=PTTState.KEY_PRESSED,
            to_state=PTTState.RECORDING,
            trigger="start_recording",
            guard=guard_fn
        )

        assert transition.guard is guard_fn
        assert transition.guard() is True


class TestPTTStateMachine:
    """Tests for PTTStateMachine class"""

    def test_initial_state(self):
        """Test state machine starts in IDLE state"""
        sm = PTTStateMachine()
        assert sm.current_state == PTTState.IDLE
        assert sm.current_state_name == "IDLE"
        assert sm.previous_state is None

    def test_valid_transition_idle_to_waiting(self):
        """Test valid transition from IDLE to WAITING_FOR_KEY"""
        sm = PTTStateMachine()
        result = sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable_ptt")

        assert result is True
        assert sm.current_state == PTTState.WAITING_FOR_KEY
        assert sm.previous_state == PTTState.IDLE

    def test_valid_transition_sequence(self):
        """Test full valid transition sequence"""
        sm = PTTStateMachine()

        # IDLE → WAITING_FOR_KEY
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        assert sm.current_state == PTTState.WAITING_FOR_KEY

        # WAITING_FOR_KEY → KEY_PRESSED
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")
        assert sm.current_state == PTTState.KEY_PRESSED

        # KEY_PRESSED → RECORDING
        sm.transition(PTTState.RECORDING, trigger="start_recording")
        assert sm.current_state == PTTState.RECORDING

        # RECORDING → RECORDING_STOPPED
        sm.transition(PTTState.RECORDING_STOPPED, trigger="key_up")
        assert sm.current_state == PTTState.RECORDING_STOPPED

        # RECORDING_STOPPED → PROCESSING
        sm.transition(PTTState.PROCESSING, trigger="process_audio")
        assert sm.current_state == PTTState.PROCESSING

        # PROCESSING → IDLE
        sm.transition(PTTState.IDLE, trigger="complete")
        assert sm.current_state == PTTState.IDLE

    def test_invalid_transition_raises_error(self):
        """Test that invalid transitions raise ValueError"""
        sm = PTTStateMachine()

        # Cannot go directly from IDLE to RECORDING
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(PTTState.RECORDING, trigger="invalid")

    def test_can_transition(self):
        """Test can_transition method"""
        sm = PTTStateMachine()

        # From IDLE
        assert sm.can_transition(PTTState.WAITING_FOR_KEY) is True
        assert sm.can_transition(PTTState.RECORDING) is False
        assert sm.can_transition(PTTState.PROCESSING) is False

        # After transitioning to WAITING_FOR_KEY
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        assert sm.can_transition(PTTState.KEY_PRESSED) is True
        assert sm.can_transition(PTTState.IDLE) is True
        assert sm.can_transition(PTTState.RECORDING) is False

    def test_cancel_flow(self):
        """Test cancellation flow"""
        sm = PTTStateMachine()

        # Get to RECORDING state
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")
        sm.transition(PTTState.RECORDING, trigger="start")

        # Cancel recording
        sm.transition(PTTState.RECORDING_CANCELLED, trigger="esc_key")
        assert sm.current_state == PTTState.RECORDING_CANCELLED

        # Return to IDLE
        sm.transition(PTTState.IDLE, trigger="cleanup")
        assert sm.current_state == PTTState.IDLE

    def test_state_history(self):
        """Test state history tracking"""
        sm = PTTStateMachine()

        # Initial history should have IDLE
        history = sm.state_history
        assert len(history) == 1
        assert history[0][0] == PTTState.IDLE

        # Make some transitions
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")

        # Check history
        history = sm.state_history
        assert len(history) == 3
        assert history[0][0] == PTTState.IDLE
        assert history[1][0] == PTTState.WAITING_FOR_KEY
        assert history[2][0] == PTTState.KEY_PRESSED

    def test_time_in_current_state(self):
        """Test time_in_current_state property"""
        sm = PTTStateMachine()

        # Should be very small initially
        assert sm.time_in_current_state < 0.1

        # Wait a bit
        time.sleep(0.01)

        # Should have increased
        assert sm.time_in_current_state >= 0.01

    def test_is_active(self):
        """Test is_active method"""
        sm = PTTStateMachine()

        # Not active in IDLE
        assert sm.is_active() is False

        # Active in WAITING_FOR_KEY
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        assert sm.is_active() is True

        # Active in KEY_PRESSED
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")
        assert sm.is_active() is True

        # Active in RECORDING
        sm.transition(PTTState.RECORDING, trigger="start")
        assert sm.is_active() is True

        # Not active in RECORDING_STOPPED
        sm.transition(PTTState.RECORDING_STOPPED, trigger="stop")
        assert sm.is_active() is False

        # Active in PROCESSING
        sm.transition(PTTState.PROCESSING, trigger="process")
        assert sm.is_active() is True

        # Not active back in IDLE
        sm.transition(PTTState.IDLE, trigger="complete")
        assert sm.is_active() is False

    def test_is_recording(self):
        """Test is_recording method"""
        sm = PTTStateMachine()

        # Not recording initially
        assert sm.is_recording() is False

        # Navigate to RECORDING
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")
        sm.transition(PTTState.RECORDING, trigger="start")

        # Now recording
        assert sm.is_recording() is True

        # Stop recording
        sm.transition(PTTState.RECORDING_STOPPED, trigger="stop")
        assert sm.is_recording() is False

    def test_get_valid_transitions(self):
        """Test get_valid_transitions method"""
        sm = PTTStateMachine()

        # From IDLE
        valid = sm.get_valid_transitions()
        assert PTTState.WAITING_FOR_KEY in valid
        assert len(valid) == 1

        # From WAITING_FOR_KEY
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        valid = sm.get_valid_transitions()
        assert PTTState.KEY_PRESSED in valid
        assert PTTState.IDLE in valid
        assert len(valid) == 2

    def test_reset(self):
        """Test reset method"""
        sm = PTTStateMachine()

        # Get to some state
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        sm.transition(PTTState.KEY_PRESSED, trigger="key_down")

        # Reset
        sm.reset()

        # Should be back in IDLE
        assert sm.current_state == PTTState.IDLE

    def test_get_state_summary(self):
        """Test get_state_summary method"""
        sm = PTTStateMachine()

        summary = sm.get_state_summary()

        assert summary["current_state"] == "IDLE"
        assert summary["previous_state"] is None
        assert summary["is_active"] is False
        assert summary["is_recording"] is False
        assert isinstance(summary["time_in_state"], float)
        assert isinstance(summary["valid_transitions"], list)
        assert isinstance(summary["state_history_length"], int)

    def test_state_change_callback(self):
        """Test state change callback"""
        callback_calls = []

        def on_state_change(from_state, to_state, trigger):
            callback_calls.append((from_state, to_state, trigger))

        sm = PTTStateMachine(on_state_change=on_state_change)

        # Make a transition
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")

        # Callback should have been called
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == PTTState.IDLE
        assert callback_calls[0][1] == PTTState.WAITING_FOR_KEY
        assert callback_calls[0][2] == "enable"

    def test_logging_integration(self, ptt_logger):
        """Test that state machine logs transitions"""
        sm = PTTStateMachine(logger=ptt_logger)

        # Make a transition
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable_ptt")

        # Check that transition was logged
        state_events = [
            e for e in ptt_logger.events
            if e.event_type == "state_transition"
        ]

        assert len(state_events) == 1
        assert state_events[0].data["from"] == "IDLE"
        assert state_events[0].data["to"] == "WAITING_FOR_KEY"
        assert state_events[0].data["trigger"] == "enable_ptt"

    def test_invalid_transition_logging(self, ptt_logger):
        """Test that invalid transitions are logged as errors"""
        sm = PTTStateMachine(logger=ptt_logger)

        # Attempt invalid transition
        with pytest.raises(ValueError):
            sm.transition(PTTState.RECORDING, trigger="invalid")

        # Check error was logged
        error_events = [
            e for e in ptt_logger.events
            if e.event_type == "error"
        ]

        assert len(error_events) == 1
        assert error_events[0].data["error_type"] == "ValueError"
        assert error_events[0].data["context"]["from"] == "IDLE"
        assert error_events[0].data["context"]["to"] == "RECORDING"


class TestStateMachineFactory:
    """Tests for create_ptt_state_machine factory"""

    def test_factory_creates_instance(self):
        """Test factory creates valid instance"""
        sm = create_ptt_state_machine()

        assert isinstance(sm, PTTStateMachine)
        assert sm.current_state == PTTState.IDLE

    def test_factory_with_logger(self, ptt_logger):
        """Test factory with custom logger"""
        sm = create_ptt_state_machine(logger=ptt_logger)

        sm.transition(PTTState.WAITING_FOR_KEY, trigger="test")

        # Verify logging works
        assert len(ptt_logger.events) > 0

    def test_factory_with_callback(self):
        """Test factory with callback"""
        calls = []

        def callback(from_state, to_state, trigger):
            calls.append(True)

        sm = create_ptt_state_machine(on_state_change=callback)
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="test")

        assert len(calls) == 1


class TestStateMachineEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_transition_to_same_state_invalid(self):
        """Test that transitioning to same state is invalid"""
        sm = PTTStateMachine()

        # IDLE is not a valid transition from IDLE
        with pytest.raises(ValueError):
            sm.transition(PTTState.IDLE, trigger="stay")

    def test_rapid_transitions(self):
        """Test rapid state transitions"""
        sm = PTTStateMachine()

        # Rapid transitions should all work
        for _ in range(10):
            sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
            sm.transition(PTTState.IDLE, trigger="disable")

        assert sm.current_state == PTTState.IDLE

    def test_state_history_does_not_mutate(self):
        """Test that returned state history is a copy"""
        sm = PTTStateMachine()

        history1 = sm.state_history
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
        history2 = sm.state_history

        # Original history should not have changed
        assert len(history1) == 1
        assert len(history2) == 2

    def test_callback_exception_handled(self, ptt_logger):
        """Test that callback exceptions are logged and don't crash"""
        def bad_callback(from_state, to_state, trigger):
            raise RuntimeError("Callback failed!")

        sm = PTTStateMachine(
            logger=ptt_logger,
            on_state_change=bad_callback
        )

        # Should not raise, just log the error
        sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")

        # Check error was logged
        errors = [e for e in ptt_logger.events if e.event_type == "error"]
        assert len(errors) == 1
        assert errors[0].data["error_type"] == "RuntimeError"
        assert "Callback failed!" in errors[0].data["error_message"]
        assert errors[0].data["context"]["callback_type"] == "state_change"
