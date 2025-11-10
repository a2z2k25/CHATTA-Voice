"""
PTT State Machine Implementation.

This module provides the state machine for managing Push-to-Talk lifecycle,
including state transitions, validation, and event handling.
"""

from enum import Enum, auto
from typing import Dict, Set, Optional, Callable, Any
from dataclasses import dataclass
import time

from .logging import get_ptt_logger, PTTLogger


class PTTState(Enum):
    """Push-to-Talk state machine states.

    State Flow:
        IDLE → WAITING_FOR_KEY → KEY_PRESSED → RECORDING →
        RECORDING_STOPPED → PROCESSING → IDLE

    Cancel Flow:
        RECORDING → RECORDING_CANCELLED → IDLE
    """

    IDLE = "IDLE"                         # Not in PTT mode
    WAITING_FOR_KEY = "WAITING_FOR_KEY"   # Listening for PTT key combo
    KEY_PRESSED = "KEY_PRESSED"           # Key combo detected, preparing
    RECORDING = "RECORDING"               # Actively recording audio
    RECORDING_STOPPED = "RECORDING_STOPPED"   # Recording ended, cleanup
    RECORDING_CANCELLED = "RECORDING_CANCELLED"  # Recording cancelled by user
    PROCESSING = "PROCESSING"             # Processing recorded audio


@dataclass
class StateTransition:
    """Definition of a state transition.

    Attributes:
        from_state: Source state
        to_state: Target state
        trigger: Event that triggers this transition
        guard: Optional condition that must be true (callable returning bool)
        action: Optional action to execute during transition
    """

    from_state: PTTState
    to_state: PTTState
    trigger: str
    guard: Optional[Callable[[], bool]] = None
    action: Optional[Callable[[], None]] = None


class PTTStateMachine:
    """State machine for PTT lifecycle management.

    This class manages the Push-to-Talk state machine, including:
    - Valid state transitions
    - State change validation
    - Transition callbacks
    - State history tracking
    - Error handling

    Example:
        >>> sm = PTTStateMachine()
        >>> sm.current_state
        <PTTState.IDLE: 'IDLE'>

        >>> sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable_ptt")
        True

        >>> sm.can_transition(PTTState.RECORDING)
        False  # Must go through KEY_PRESSED first
    """

    # Valid state transitions
    # Format: {from_state: {to_state1, to_state2, ...}}
    VALID_TRANSITIONS: Dict[PTTState, Set[PTTState]] = {
        PTTState.IDLE: {
            PTTState.WAITING_FOR_KEY,  # Enable PTT
        },
        PTTState.WAITING_FOR_KEY: {
            PTTState.KEY_PRESSED,      # Key combo detected
            PTTState.IDLE,             # Disable PTT
        },
        PTTState.KEY_PRESSED: {
            PTTState.RECORDING,        # Start recording
            PTTState.IDLE,             # Quick release (too short)
        },
        PTTState.RECORDING: {
            PTTState.RECORDING_STOPPED,    # Normal end
            PTTState.RECORDING_CANCELLED,  # User cancelled (ESC)
        },
        PTTState.RECORDING_STOPPED: {
            PTTState.PROCESSING,       # Process audio
            PTTState.IDLE,             # Skip processing (empty/invalid)
        },
        PTTState.RECORDING_CANCELLED: {
            PTTState.IDLE,             # Clean up and reset
        },
        PTTState.PROCESSING: {
            PTTState.IDLE,             # Complete
        },
    }

    def __init__(
        self,
        logger: Optional[PTTLogger] = None,
        on_state_change: Optional[Callable[[PTTState, PTTState, str], None]] = None
    ) -> None:
        """Initialize state machine.

        Args:
            logger: PTTLogger instance for logging state changes
            on_state_change: Optional callback for state changes
                            Called with (from_state, to_state, trigger)
        """
        self._current_state = PTTState.IDLE
        self._previous_state: Optional[PTTState] = None
        self._state_history: list[tuple[PTTState, float]] = []
        self._logger = logger or get_ptt_logger()
        self._on_state_change = on_state_change

        # Track state entry time for duration calculations
        self._state_entry_time = time.time()

        # Record initial state
        self._record_state_entry(PTTState.IDLE)

    @property
    def current_state(self) -> PTTState:
        """Get current state."""
        return self._current_state

    @property
    def current_state_name(self) -> str:
        """Get current state as string."""
        return self._current_state.value

    @property
    def previous_state(self) -> Optional[PTTState]:
        """Get previous state."""
        return self._previous_state

    @property
    def state_history(self) -> list[tuple[PTTState, float]]:
        """Get state history as list of (state, timestamp) tuples."""
        return self._state_history.copy()

    @property
    def time_in_current_state(self) -> float:
        """Get time spent in current state (seconds)."""
        return time.time() - self._state_entry_time

    def can_transition(self, to_state: PTTState) -> bool:
        """Check if transition to target state is valid.

        Args:
            to_state: Target state

        Returns:
            True if transition is valid, False otherwise
        """
        return to_state in self.VALID_TRANSITIONS[self._current_state]

    def transition(
        self,
        to_state: PTTState,
        trigger: str = "unknown",
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Transition to new state.

        Args:
            to_state: Target state
            trigger: Event that triggered transition
            data: Optional additional data for logging

        Returns:
            True if transition successful, False if invalid

        Raises:
            ValueError: If transition is invalid

        Example:
            >>> sm = PTTStateMachine()
            >>> sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable_ptt")
            True

            >>> sm.transition(PTTState.PROCESSING, trigger="invalid")
            ValueError: Invalid transition from WAITING_FOR_KEY to PROCESSING
        """
        # Validate transition
        if not self.can_transition(to_state):
            error_msg = (
                f"Invalid transition from {self.current_state_name} "
                f"to {to_state.value}"
            )

            # Create and log error
            error = ValueError(error_msg)
            self._logger.log_error(error, {
                "from": self.current_state_name,
                "to": to_state.value,
                "trigger": trigger
            })

            raise error

        # Calculate duration in current state
        duration = self.time_in_current_state

        # Perform transition
        old_state = self._current_state
        self._previous_state = old_state
        self._current_state = to_state

        # Update entry time
        self._state_entry_time = time.time()

        # Record in history
        self._record_state_entry(to_state)

        # Log state transition
        self._logger.log_state_transition(
            from_state=old_state.value,
            to_state=to_state.value,
            trigger=trigger
        )

        # Log additional duration data if significant
        if duration > 0.001:  # More than 1ms
            self._logger.log_event("state_duration", {
                "state": old_state.value,
                "duration_seconds": duration,
                "next_state": to_state.value,
                **(data or {})
            })

        # Call callback if provided
        if self._on_state_change:
            try:
                self._on_state_change(old_state, to_state, trigger)
            except Exception as e:
                self._logger.log_error(e, {
                    "callback_type": "state_change",
                    "from": old_state.value,
                    "to": to_state.value,
                    "trigger": trigger
                })

        return True

    def reset(self) -> None:
        """Reset state machine to IDLE state.

        This is useful for error recovery or cancellation scenarios.
        Does not clear state history.
        """
        if self._current_state != PTTState.IDLE:
            self.transition(
                PTTState.IDLE,
                trigger="reset",
                data={"forced_reset": True}
            )

    def is_active(self) -> bool:
        """Check if PTT is in an active state.

        Returns:
            True if in WAITING_FOR_KEY, KEY_PRESSED, RECORDING, or PROCESSING
        """
        return self._current_state in {
            PTTState.WAITING_FOR_KEY,
            PTTState.KEY_PRESSED,
            PTTState.RECORDING,
            PTTState.PROCESSING
        }

    def is_recording(self) -> bool:
        """Check if currently recording.

        Returns:
            True if in RECORDING state
        """
        return self._current_state == PTTState.RECORDING

    def get_valid_transitions(self) -> Set[PTTState]:
        """Get set of valid target states from current state.

        Returns:
            Set of PTTState values that are valid transitions
        """
        return self.VALID_TRANSITIONS[self._current_state].copy()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state machine status.

        Returns:
            Dictionary containing:
                - current_state: Current state name
                - previous_state: Previous state name (or None)
                - time_in_state: Time in current state (seconds)
                - is_active: Whether PTT is active
                - is_recording: Whether currently recording
                - valid_transitions: List of valid next states
                - state_history_length: Number of state changes
        """
        return {
            "current_state": self.current_state_name,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "time_in_state": self.time_in_current_state,
            "is_active": self.is_active(),
            "is_recording": self.is_recording(),
            "valid_transitions": [s.value for s in self.get_valid_transitions()],
            "state_history_length": len(self._state_history)
        }

    def _record_state_entry(self, state: PTTState) -> None:
        """Record state entry in history.

        Args:
            state: State being entered
        """
        self._state_history.append((state, time.time()))


def create_ptt_state_machine(
    logger: Optional[PTTLogger] = None,
    on_state_change: Optional[Callable[[PTTState, PTTState, str], None]] = None
) -> PTTStateMachine:
    """Factory function to create PTT state machine.

    This is the recommended way to create a state machine instance.

    Args:
        logger: Optional PTTLogger instance
        on_state_change: Optional state change callback

    Returns:
        Configured PTTStateMachine instance

    Example:
        >>> sm = create_ptt_state_machine()
        >>> sm.transition(PTTState.WAITING_FOR_KEY, trigger="enable")
    """
    return PTTStateMachine(logger=logger, on_state_change=on_state_change)
