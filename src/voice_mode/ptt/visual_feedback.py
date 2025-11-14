"""
PTT visual feedback system.

Provides terminal-based visual indicators for PTT status with support
for real-time updates and configurable display styles.
"""

import sys
import time
import threading
from typing import Optional, Callable
from dataclasses import dataclass

from voice_mode.ptt.status_display import PTTStatusDisplay, DisplayStyle, get_status_display
from voice_mode.ptt.logging import get_ptt_logger


@dataclass
class PTTVisualState:
    """Current visual feedback state."""

    is_enabled: bool = False
    is_recording: bool = False
    current_mode: str = "hold"
    key_combo: str = "down+right"
    cancel_key: str = "escape"
    recording_start_time: Optional[float] = None
    last_update_time: float = 0.0


class PTTVisualFeedback:
    """
    Manages visual feedback for PTT operations.

    Displays real-time status updates in the terminal with support for
    different display styles and live duration updates during recording.
    """

    def __init__(
        self,
        display_style: Optional[DisplayStyle] = None,
        show_duration: bool = True,
        update_interval: float = 0.5
    ):
        """
        Initialize visual feedback system.

        Args:
            display_style: Display style to use (None = from config)
            show_duration: Show live duration counter during recording
            update_interval: Update interval for live updates (seconds)
        """
        self.display = get_status_display(style=display_style)
        self.show_duration = show_duration
        self.update_interval = update_interval

        self.state = PTTVisualState()
        self.logger = get_ptt_logger()

        # Live update thread
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()

    def enable(self, mode: str, key_combo: str, cancel_key: str = "escape"):
        """
        Enable visual feedback.

        Args:
            mode: PTT mode (hold/toggle/hybrid)
            key_combo: Active key combination
            cancel_key: Cancel key
        """
        self.state.is_enabled = True
        self.state.current_mode = mode
        self.state.key_combo = key_combo
        self.state.cancel_key = cancel_key

        # Display initial waiting message
        self._print_status(
            self.display.format_waiting(key_combo, mode)
        )

        self.logger.log_event("visual_feedback_enabled", {
            "mode": mode,
            "key_combo": key_combo
        })

    def disable(self):
        """Disable visual feedback."""
        if not self.state.is_enabled:
            return

        # Stop any live updates
        self._stop_live_updates()

        self.state.is_enabled = False
        self.state.is_recording = False
        self.state.recording_start_time = None

        self.logger.log_event("visual_feedback_disabled", {})

    def on_recording_start(self):
        """Handle recording start event."""
        if not self.state.is_enabled:
            return

        self.state.is_recording = True
        self.state.recording_start_time = time.time()

        # Display recording start message
        self._print_status(
            self.display.format_recording_start(
                self.state.key_combo,
                self.state.current_mode
            )
        )

        # Start live duration updates if enabled
        if self.show_duration and self.display.style != DisplayStyle.MINIMAL:
            self._start_live_updates()

    def on_recording_stop(self, duration: float, sample_count: int):
        """
        Handle recording stop event.

        Args:
            duration: Recording duration in seconds
            sample_count: Number of audio samples
        """
        if not self.state.is_enabled:
            return

        # Stop live updates
        self._stop_live_updates()

        self.state.is_recording = False
        self.state.recording_start_time = None

        # Display stop message
        self._print_status(
            self.display.format_recording_stop(duration, sample_count)
        )

        # Show waiting message again
        self._print_status(
            self.display.format_waiting(
                self.state.key_combo,
                self.state.current_mode
            )
        )

    def on_recording_cancel(self, reason: str = "user"):
        """
        Handle recording cancel event.

        Args:
            reason: Cancellation reason
        """
        if not self.state.is_enabled:
            return

        # Stop live updates
        self._stop_live_updates()

        self.state.is_recording = False
        self.state.recording_start_time = None

        # Display cancel message
        self._print_status(
            self.display.format_recording_cancel(reason)
        )

        # Show waiting message again
        self._print_status(
            self.display.format_waiting(
                self.state.key_combo,
                self.state.current_mode
            )
        )

    def on_error(self, error_message: str):
        """
        Handle error event.

        Args:
            error_message: Error description
        """
        if not self.state.is_enabled:
            return

        # Stop live updates if recording
        if self.state.is_recording:
            self._stop_live_updates()
            self.state.is_recording = False
            self.state.recording_start_time = None

        # Display error message
        self._print_status(
            self.display.format_error(error_message)
        )

    def _print_status(self, message: str):
        """
        Print status message to stdout.

        Args:
            message: Message to print
        """
        if not message:
            return

        # Always flush to ensure immediate display
        print(message, flush=True)

        self.state.last_update_time = time.time()

    def _start_live_updates(self):
        """Start live duration update thread."""
        if self._update_thread is not None and self._update_thread.is_alive():
            return  # Already running

        self._stop_updates.clear()
        self._update_thread = threading.Thread(
            target=self._live_update_loop,
            daemon=True
        )
        self._update_thread.start()

    def _stop_live_updates(self):
        """Stop live duration update thread."""
        if self._update_thread is None:
            return

        self._stop_updates.set()

        # Wait for thread to finish (with timeout)
        self._update_thread.join(timeout=1.0)
        self._update_thread = None

    def _live_update_loop(self):
        """Live update loop (runs in background thread)."""
        try:
            while not self._stop_updates.is_set():
                if self.state.is_recording and self.state.recording_start_time:
                    duration = time.time() - self.state.recording_start_time
                    duration_display = self.display.format_recording_duration(duration)

                    if duration_display:
                        # Print duration update (overwrites previous line in compact mode)
                        if self.display.style == DisplayStyle.COMPACT:
                            # Simple update without overwriting
                            sys.stdout.write(f"\r{duration_display}  ")
                            sys.stdout.flush()
                        else:
                            # Detailed mode - just print updates
                            self._print_status(duration_display)

                # Sleep for update interval
                self._stop_updates.wait(self.update_interval)

        except Exception as e:
            self.logger.log_error(e, {"context": "live_update_loop"})

        finally:
            # Ensure we end with a newline if we were using \r
            if self.display.style == DisplayStyle.COMPACT:
                sys.stdout.write("\n")
                sys.stdout.flush()


# Global instance
_global_visual_feedback: Optional[PTTVisualFeedback] = None


def get_visual_feedback() -> PTTVisualFeedback:
    """
    Get or create global visual feedback instance.

    Returns:
        PTTVisualFeedback instance
    """
    global _global_visual_feedback

    if _global_visual_feedback is None:
        from voice_mode import config

        # Get configuration
        show_duration = getattr(config, 'PTT_SHOW_DURATION', True)

        _global_visual_feedback = PTTVisualFeedback(
            show_duration=show_duration
        )

    return _global_visual_feedback


def reset_visual_feedback():
    """Reset global visual feedback instance."""
    global _global_visual_feedback

    if _global_visual_feedback is not None:
        _global_visual_feedback.disable()

    _global_visual_feedback = None


def create_visual_feedback_callbacks():
    """
    Create callback functions for PTT controller integration.

    Returns:
        Dictionary of callback functions
    """
    feedback = get_visual_feedback()

    return {
        'on_recording_start': lambda: feedback.on_recording_start(),
        'on_recording_stop': lambda audio_data: feedback.on_recording_stop(
            duration=time.time() - (feedback.state.recording_start_time or time.time()),
            sample_count=len(audio_data) if audio_data is not None else 0
        ),
        'on_recording_cancel': lambda: feedback.on_recording_cancel(),
        'on_error': lambda error: feedback.on_error(str(error))
    }
