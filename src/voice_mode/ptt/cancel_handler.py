"""
PTT cancel handler with enhanced feedback and tracking.

Provides improved cancel functionality with visual/audio feedback
and detailed cancel reason tracking.
"""

import time
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass

from voice_mode.ptt.logging import get_ptt_logger


class CancelReason(Enum):
    """Reasons for recording cancellation."""

    USER_CANCEL_KEY = "user_cancel_key"        # User pressed cancel key
    USER_INTERRUPT = "user_interrupt"          # Ctrl+C or similar
    TIMEOUT = "timeout"                        # Recording timeout exceeded
    ERROR = "error"                            # Error during recording
    MIN_DURATION = "min_duration"              # Recording too short
    STATE_ERROR = "state_error"                # Invalid state
    MANUAL = "manual"                          # Programmatic cancel


@dataclass
class CancelEvent:
    """A recording cancellation event."""

    timestamp: float
    reason: CancelReason
    duration: float                            # How long recording lasted
    message: Optional[str] = None              # Optional cancel message
    context: Optional[Dict[str, Any]] = None   # Additional context


class PTTCancelHandler:
    """
    PTT cancel handler.

    Manages recording cancellation with enhanced feedback and tracking.
    """

    def __init__(
        self,
        cancel_key: Optional[str] = None,
        on_cancel_visual: Optional[Callable[[CancelEvent], None]] = None,
        on_cancel_audio: Optional[Callable[[CancelEvent], None]] = None,
        on_cancel_stats: Optional[Callable[[CancelEvent], None]] = None
    ):
        """
        Initialize cancel handler.

        Args:
            cancel_key: Cancel key name (e.g., 'escape')
            on_cancel_visual: Visual feedback callback
            on_cancel_audio: Audio feedback callback
            on_cancel_stats: Statistics callback
        """
        self.logger = get_ptt_logger()
        self.cancel_key = cancel_key
        self.on_cancel_visual = on_cancel_visual
        self.on_cancel_audio = on_cancel_audio
        self.on_cancel_stats = on_cancel_stats

        # Cancel tracking
        self._cancel_requested = False
        self._cancel_reason: Optional[CancelReason] = None
        self._recording_start: Optional[float] = None
        self._cancel_history: list[CancelEvent] = []

    def reset(self):
        """Reset cancel state."""
        self._cancel_requested = False
        self._cancel_reason = None
        self._recording_start = None

    def start_recording(self):
        """Mark recording start for duration tracking."""
        self._recording_start = time.time()
        self._cancel_requested = False
        self._cancel_reason = None

    def request_cancel(
        self,
        reason: CancelReason,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Request recording cancellation.

        Args:
            reason: Cancellation reason
            message: Optional message
            context: Additional context
        """
        if self._cancel_requested:
            # Already cancelled
            return

        self._cancel_requested = True
        self._cancel_reason = reason

        # Calculate duration
        duration = 0.0
        if self._recording_start:
            duration = time.time() - self._recording_start

        # Create cancel event
        event = CancelEvent(
            timestamp=time.time(),
            reason=reason,
            duration=duration,
            message=message,
            context=context
        )

        # Store in history
        self._cancel_history.append(event)

        # Trigger callbacks
        self._trigger_cancel_feedback(event)

        self.logger.log_event("cancel_requested", {
            "reason": reason.value,
            "duration": duration,
            "message": message
        })

    def _trigger_cancel_feedback(self, event: CancelEvent):
        """Trigger cancel feedback callbacks."""
        # Visual feedback
        if self.on_cancel_visual:
            try:
                self.on_cancel_visual(event)
            except Exception as e:
                self.logger.log_error(e, {"context": "cancel_visual_feedback"})

        # Audio feedback
        if self.on_cancel_audio:
            try:
                self.on_cancel_audio(event)
            except Exception as e:
                self.logger.log_error(e, {"context": "cancel_audio_feedback"})

        # Statistics
        if self.on_cancel_stats:
            try:
                self.on_cancel_stats(event)
            except Exception as e:
                self.logger.log_error(e, {"context": "cancel_stats"})

    def is_cancelled(self) -> bool:
        """Check if cancel was requested."""
        return self._cancel_requested

    def get_cancel_reason(self) -> Optional[CancelReason]:
        """Get cancellation reason."""
        return self._cancel_reason

    def get_cancel_message(self) -> str:
        """
        Get user-friendly cancel message.

        Returns:
            Formatted cancel message
        """
        if not self._cancel_requested or not self._cancel_reason:
            return "Recording not cancelled"

        reason = self._cancel_reason

        messages = {
            CancelReason.USER_CANCEL_KEY: f"Recording cancelled by user (cancel key: {self.cancel_key})",
            CancelReason.USER_INTERRUPT: "Recording interrupted by user (Ctrl+C)",
            CancelReason.TIMEOUT: "Recording cancelled: timeout exceeded",
            CancelReason.ERROR: "Recording cancelled due to error",
            CancelReason.MIN_DURATION: "Recording cancelled: too short",
            CancelReason.STATE_ERROR: "Recording cancelled: invalid state",
            CancelReason.MANUAL: "Recording cancelled programmatically",
        }

        return messages.get(reason, f"Recording cancelled: {reason.value}")

    def get_cancel_history(self) -> list[CancelEvent]:
        """
        Get cancel history.

        Returns:
            List of cancel events
        """
        return self._cancel_history.copy()

    def get_cancel_stats(self) -> Dict[str, Any]:
        """
        Get cancel statistics.

        Returns:
            Dictionary with cancel stats
        """
        if not self._cancel_history:
            return {
                "total_cancels": 0,
                "by_reason": {},
                "avg_duration_before_cancel": 0.0
            }

        # Count by reason
        by_reason = {}
        for event in self._cancel_history:
            reason_key = event.reason.value
            by_reason[reason_key] = by_reason.get(reason_key, 0) + 1

        # Average duration
        avg_duration = sum(e.duration for e in self._cancel_history) / len(self._cancel_history)

        return {
            "total_cancels": len(self._cancel_history),
            "by_reason": by_reason,
            "avg_duration_before_cancel": avg_duration,
            "most_common_reason": max(by_reason.items(), key=lambda x: x[1])[0] if by_reason else None
        }


class CancelFeedbackManager:
    """
    Manages cancel feedback integration with visual and audio systems.
    """

    def __init__(self):
        """Initialize cancel feedback manager."""
        self.logger = get_ptt_logger()

    def create_visual_callback(self) -> Callable[[CancelEvent], None]:
        """
        Create visual feedback callback for cancel events.

        Returns:
            Visual callback function
        """
        def visual_callback(event: CancelEvent):
            """Display cancel visual feedback."""
            try:
                from voice_mode.ptt.status_display import get_status_display

                display = get_status_display()
                cancel_msg = self._format_cancel_message(event)

                # Format cancel display
                formatted = display.format_recording_cancel(cancel_msg)
                print(formatted)

            except ImportError:
                # Fallback to simple message
                print(f"❌ {self._format_cancel_message(event)}")

        return visual_callback

    def create_audio_callback(self) -> Callable[[CancelEvent], None]:
        """
        Create audio feedback callback for cancel events.

        Returns:
            Audio callback function
        """
        def audio_callback(event: CancelEvent):
            """Play cancel audio feedback."""
            try:
                from voice_mode.ptt.audio_feedback import get_audio_feedback

                feedback = get_audio_feedback()
                feedback.play_cancel(blocking=False)

            except ImportError:
                # Audio feedback not available
                pass

        return audio_callback

    def create_stats_callback(self) -> Callable[[CancelEvent], None]:
        """
        Create statistics callback for cancel events.

        Returns:
            Statistics callback function
        """
        def stats_callback(event: CancelEvent):
            """Record cancel in statistics."""
            try:
                from voice_mode.ptt.statistics import get_ptt_statistics, PTTOutcome

                stats = get_ptt_statistics()
                stats.on_recording_stop(
                    duration=event.duration,
                    sample_count=0,
                    outcome=PTTOutcome.CANCELLED,
                    error_message=event.message
                )

            except ImportError:
                # Statistics not available
                pass

        return stats_callback

    def _format_cancel_message(self, event: CancelEvent) -> str:
        """Format cancel event message."""
        reason_messages = {
            CancelReason.USER_CANCEL_KEY: "Cancelled by user",
            CancelReason.USER_INTERRUPT: "Interrupted by user",
            CancelReason.TIMEOUT: "Timeout exceeded",
            CancelReason.ERROR: "Error occurred",
            CancelReason.MIN_DURATION: "Recording too short",
            CancelReason.STATE_ERROR: "Invalid state",
            CancelReason.MANUAL: "Cancelled",
        }

        msg = reason_messages.get(event.reason, "Cancelled")

        if event.message:
            msg += f": {event.message}"

        return msg


# Global cancel handler
_global_cancel_handler: Optional[PTTCancelHandler] = None


def get_cancel_handler(
    cancel_key: Optional[str] = None,
    with_feedback: bool = True,
    with_stats: bool = True
) -> PTTCancelHandler:
    """
    Get or create global cancel handler.

    Args:
        cancel_key: Cancel key name
        with_feedback: Enable visual/audio feedback
        with_stats: Enable statistics tracking

    Returns:
        PTTCancelHandler instance
    """
    global _global_cancel_handler

    if _global_cancel_handler is None:
        # Create feedback callbacks
        feedback_mgr = CancelFeedbackManager()

        visual_callback = feedback_mgr.create_visual_callback() if with_feedback else None
        audio_callback = feedback_mgr.create_audio_callback() if with_feedback else None
        stats_callback = feedback_mgr.create_stats_callback() if with_stats else None

        _global_cancel_handler = PTTCancelHandler(
            cancel_key=cancel_key,
            on_cancel_visual=visual_callback,
            on_cancel_audio=audio_callback,
            on_cancel_stats=stats_callback
        )

    return _global_cancel_handler


def reset_cancel_handler():
    """Reset global cancel handler."""
    global _global_cancel_handler

    if _global_cancel_handler:
        _global_cancel_handler.reset()
    else:
        _global_cancel_handler = None


def create_cancel_callbacks(
    cancel_key: Optional[str] = None
) -> Dict[str, Callable]:
    """
    Create cancel callback functions for PTT controller integration.

    Args:
        cancel_key: Cancel key name

    Returns:
        Dictionary of callback functions
    """
    handler = get_cancel_handler(cancel_key=cancel_key)

    return {
        'on_recording_start': lambda: handler.start_recording(),
        'on_cancel_user': lambda: handler.request_cancel(CancelReason.USER_CANCEL_KEY),
        'on_cancel_interrupt': lambda: handler.request_cancel(CancelReason.USER_INTERRUPT),
        'on_cancel_timeout': lambda timeout: handler.request_cancel(
            CancelReason.TIMEOUT,
            message=f"Timeout: {timeout}s"
        ),
        'on_cancel_error': lambda error: handler.request_cancel(
            CancelReason.ERROR,
            message=str(error)
        ),
        'on_cancel_manual': lambda msg: handler.request_cancel(
            CancelReason.MANUAL,
            message=msg
        ),
        'is_cancelled': lambda: handler.is_cancelled(),
        'get_cancel_reason': lambda: handler.get_cancel_reason(),
        'reset': lambda: handler.reset()
    }


def format_cancel_stats(stats: Optional[Dict[str, Any]] = None) -> str:
    """
    Format cancel statistics as human-readable string.

    Args:
        stats: Cancel stats dict (uses global handler if None)

    Returns:
        Formatted stats string
    """
    if stats is None:
        handler = get_cancel_handler()
        stats = handler.get_cancel_stats()

    if stats['total_cancels'] == 0:
        return "No cancellations recorded"

    lines = [
        "Cancel Statistics",
        "=" * 50,
        "",
        f"Total Cancellations: {stats['total_cancels']}",
        f"Avg Duration Before Cancel: {stats['avg_duration_before_cancel']:.2f}s",
        ""
    ]

    if stats['by_reason']:
        lines.append("Cancellations by Reason:")
        for reason, count in sorted(stats['by_reason'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {reason}: {count}")

    if stats.get('most_common_reason'):
        lines.extend([
            "",
            f"Most Common: {stats['most_common_reason']}"
        ])

    return "\n".join(lines)
