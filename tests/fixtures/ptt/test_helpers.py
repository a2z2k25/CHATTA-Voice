"""
Helper utilities for PTT testing.

Provides common assertion and utility functions for PTT tests.
"""

import time
from typing import List, Callable, Optional, Any
from dataclasses import dataclass


def assert_ptt_event_logged(logger, event_type: str, expected_count: int = 1):
    """
    Assert that a specific PTT event was logged.

    Args:
        logger: PTTLogger instance
        event_type: Type of event to check for
        expected_count: Expected number of occurrences

    Raises:
        AssertionError: If event count doesn't match
    """
    matching_events = [e for e in logger.events if e.event_type == event_type]
    actual_count = len(matching_events)

    assert actual_count == expected_count, (
        f"Expected {expected_count} '{event_type}' events, "
        f"but found {actual_count}"
    )


def assert_timing_within_threshold(
    duration_ms: float,
    threshold_ms: float,
    operation: str = "operation"
):
    """
    Assert that an operation completed within a time threshold.

    Args:
        duration_ms: Actual duration in milliseconds
        threshold_ms: Maximum acceptable duration
        operation: Name of operation for error message

    Raises:
        AssertionError: If duration exceeds threshold
    """
    assert duration_ms <= threshold_ms, (
        f"{operation} took {duration_ms:.2f}ms, "
        f"exceeding threshold of {threshold_ms:.2f}ms"
    )


@dataclass
class MockKey:
    """Mock keyboard key for testing"""
    name: str = None
    char: str = None

    def __str__(self):
        return self.name or self.char or "unknown"


def create_mock_key_sequence(key_names: List[str]) -> List[MockKey]:
    """
    Create a sequence of mock keyboard keys.

    Args:
        key_names: List of key names

    Returns:
        List of MockKey objects

    Example:
        >>> keys = create_mock_key_sequence(["ctrl", "space"])
        >>> # Use in tests to simulate key presses
    """
    return [MockKey(name=name) for name in key_names]


def wait_for_callback(
    callback_tracker,
    expected_type: str,
    timeout: float = 1.0,
    poll_interval: float = 0.01
) -> bool:
    """
    Wait for a callback to be invoked.

    Args:
        callback_tracker: CallbackTracker instance
        expected_type: Type of callback ("press" or "release")
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check in seconds

    Returns:
        True if callback was invoked, False if timeout

    Example:
        >>> tracker = CallbackTracker()
        >>> # ... trigger action ...
        >>> assert wait_for_callback(tracker, "press")
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        for call_type, _ in callback_tracker.calls:
            if call_type == expected_type:
                return True
        time.sleep(poll_interval)

    return False


def simulate_key_press_sequence(
    handler,
    key_sequence: List[str],
    press_duration: float = 0.1
):
    """
    Simulate pressing and releasing a sequence of keys.

    Args:
        handler: KeyboardHandler instance
        key_sequence: List of key names to press in order
        press_duration: How long to hold each key (seconds)

    Example:
        >>> from voice_mode.ptt.keyboard import KeyboardHandler
        >>> handler = KeyboardHandler("space")
        >>> simulate_key_press_sequence(handler, ["space"])
    """
    # Press all keys
    for key_name in key_sequence:
        mock_key = MockKey(name=key_name)
        handler._on_press(mock_key)
        time.sleep(press_duration / len(key_sequence))

    # Release all keys in reverse order
    for key_name in reversed(key_sequence):
        mock_key = MockKey(name=key_name)
        handler._on_release(mock_key)


def assert_state_transition(
    logger,
    from_state: str,
    to_state: str,
    trigger: Optional[str] = None
):
    """
    Assert that a state transition was logged.

    Args:
        logger: PTTLogger instance
        from_state: Expected previous state
        to_state: Expected new state
        trigger: Optional trigger event name

    Raises:
        AssertionError: If transition not found
    """
    state_events = [
        e for e in logger.events
        if e.event_type == "state_transition"
    ]

    matching = [
        e for e in state_events
        if e.data["from"] == from_state and e.data["to"] == to_state
    ]

    if trigger:
        matching = [
            e for e in matching
            if e.data.get("trigger") == trigger
        ]

    assert len(matching) > 0, (
        f"No state transition found from {from_state} to {to_state}"
        + (f" with trigger {trigger}" if trigger else "")
    )


def get_event_data(logger, event_type: str, field: str) -> List[Any]:
    """
    Extract data field values from logged events.

    Args:
        logger: PTTLogger instance
        event_type: Type of events to search
        field: Data field to extract

    Returns:
        List of field values from matching events

    Example:
        >>> durations = get_event_data(logger, "timing", "operation")
        >>> assert "recording_start" in durations
    """
    matching_events = [e for e in logger.events if e.event_type == event_type]
    return [e.data.get(field) for e in matching_events if field in e.data]


def assert_performance_acceptable(
    logger,
    operation: str,
    max_duration_ms: float
):
    """
    Assert that all timing events for an operation are within threshold.

    Args:
        logger: PTTLogger instance
        operation: Name of operation to check
        max_duration_ms: Maximum acceptable duration

    Raises:
        AssertionError: If any timing exceeds threshold
    """
    timing_events = [
        e for e in logger.events
        if e.event_type == "timing" and e.data.get("operation") == operation
    ]

    assert len(timing_events) > 0, f"No timing events found for {operation}"

    for event in timing_events:
        duration = event.duration_ms
        assert duration <= max_duration_ms, (
            f"{operation} took {duration:.2f}ms, "
            f"exceeding max of {max_duration_ms:.2f}ms"
        )


def create_test_audio(
    sample_rate: int = 16000,
    duration: float = 1.0,
    noise_level: int = 0
):
    """
    Create test audio data.

    Args:
        sample_rate: Sample rate in Hz
        duration: Duration in seconds
        noise_level: Amplitude of random noise (0 = silence)

    Returns:
        numpy array of audio samples
    """
    import numpy as np

    num_samples = int(sample_rate * duration)

    if noise_level == 0:
        # Silence
        audio = np.zeros(num_samples, dtype=np.int16)
    else:
        # Random noise
        audio = np.random.randint(
            -noise_level,
            noise_level,
            num_samples,
            dtype=np.int16
        )

    return audio


def assert_logger_session_valid(logger):
    """
    Assert that logger session is in a valid state.

    Args:
        logger: PTTLogger instance

    Raises:
        AssertionError: If session is invalid
    """
    assert logger.session_id is not None, "Session ID is None"
    assert logger.session_id.startswith("ptt_"), "Invalid session ID format"
    assert isinstance(logger.events, list), "Events is not a list"
    assert isinstance(logger.timing_data, dict), "Timing data is not a dict"


def clear_logger_events(logger):
    """
    Clear all events from logger (useful for test isolation).

    Args:
        logger: PTTLogger instance
    """
    logger.events.clear()
    logger.timing_data.clear()
