"""
PTT statistics tracking and reporting.

Tracks usage metrics, performance data, and provides session summaries
for analyzing PTT usage patterns and optimization opportunities.
"""

import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from voice_mode.ptt.logging import get_ptt_logger


class PTTOutcome(Enum):
    """Recording outcome types."""

    SUCCESS = "success"      # Recording completed successfully
    CANCELLED = "cancelled"  # User cancelled recording
    TIMEOUT = "timeout"      # Recording timed out
    ERROR = "error"          # Error occurred


@dataclass
class PTTRecordingStats:
    """Statistics for a single PTT recording."""

    timestamp: float
    mode: str  # hold, toggle, hybrid
    duration: float  # Recording duration in seconds
    sample_count: int  # Number of audio samples
    outcome: PTTOutcome

    # Performance metrics
    key_press_latency: Optional[float] = None  # Time from enable to key press
    recording_start_latency: Optional[float] = None  # Time from key press to recording start

    # Additional metadata
    key_combo: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PTTSessionStats:
    """Statistics for a PTT session."""

    session_start: float = field(default_factory=time.time)
    session_end: Optional[float] = None

    # Recording counts
    total_recordings: int = 0
    successful_recordings: int = 0
    cancelled_recordings: int = 0
    timeout_recordings: int = 0
    error_recordings: int = 0

    # Duration statistics
    total_recording_time: float = 0.0  # Total time spent recording (seconds)
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    avg_duration: Optional[float] = None

    # Mode usage
    mode_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Performance metrics
    avg_key_press_latency: Optional[float] = None
    avg_recording_start_latency: Optional[float] = None

    # Individual recordings
    recordings: List[PTTRecordingStats] = field(default_factory=list)

    def session_duration(self) -> float:
        """Get session duration in seconds."""
        end = self.session_end or time.time()
        return end - self.session_start

    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_recordings == 0:
            return 0.0
        return (self.successful_recordings / self.total_recordings) * 100

    def cancel_rate(self) -> float:
        """Get cancel rate as percentage."""
        if self.total_recordings == 0:
            return 0.0
        return (self.cancelled_recordings / self.total_recordings) * 100

    def error_rate(self) -> float:
        """Get error rate as percentage."""
        if self.total_recordings == 0:
            return 0.0
        return (self.error_recordings / self.total_recordings) * 100


class PTTStatistics:
    """
    PTT statistics collector and reporter.

    Tracks recording statistics, performance metrics, and usage patterns
    for PTT operations.
    """

    def __init__(self):
        """Initialize PTT statistics."""
        self.logger = get_ptt_logger()
        self.current_session = PTTSessionStats()
        self._enabled = False

        # Current recording state
        self._current_recording_start: Optional[float] = None
        self._current_key_press_time: Optional[float] = None
        self._current_enable_time: Optional[float] = None
        self._current_mode: Optional[str] = None
        self._current_key_combo: Optional[str] = None

    def enable(self, mode: str, key_combo: str):
        """
        Enable statistics tracking.

        Args:
            mode: PTT mode (hold/toggle/hybrid)
            key_combo: Active key combination
        """
        self._enabled = True
        self._current_enable_time = time.time()
        self._current_mode = mode
        self._current_key_combo = key_combo

        self.logger.log_event("statistics_enabled", {
            "mode": mode,
            "key_combo": key_combo
        })

    def disable(self):
        """Disable statistics tracking and end session."""
        if self._enabled:
            self._enabled = False
            self.current_session.session_end = time.time()

            self.logger.log_event("statistics_disabled", {
                "total_recordings": self.current_session.total_recordings,
                "session_duration": self.current_session.session_duration()
            })

    def on_key_press(self):
        """Record key press event."""
        if not self._enabled:
            return

        self._current_key_press_time = time.time()

    def on_recording_start(self):
        """Record recording start event."""
        if not self._enabled:
            return

        self._current_recording_start = time.time()

    def on_recording_stop(
        self,
        duration: float,
        sample_count: int,
        outcome: PTTOutcome = PTTOutcome.SUCCESS,
        error_message: Optional[str] = None
    ):
        """
        Record recording completion.

        Args:
            duration: Recording duration in seconds
            sample_count: Number of audio samples
            outcome: Recording outcome
            error_message: Error message if outcome is ERROR
        """
        if not self._enabled:
            return

        # Calculate latencies
        key_press_latency = None
        if self._current_enable_time and self._current_key_press_time:
            key_press_latency = self._current_key_press_time - self._current_enable_time

        recording_start_latency = None
        if self._current_key_press_time and self._current_recording_start:
            recording_start_latency = self._current_recording_start - self._current_key_press_time

        # Create recording stats
        recording_stats = PTTRecordingStats(
            timestamp=time.time(),
            mode=self._current_mode or "unknown",
            duration=duration,
            sample_count=sample_count,
            outcome=outcome,
            key_press_latency=key_press_latency,
            recording_start_latency=recording_start_latency,
            key_combo=self._current_key_combo,
            error_message=error_message
        )

        # Update session stats
        self._update_session_stats(recording_stats)

        # Reset current recording state
        self._reset_current_recording()

        self.logger.log_event("recording_stats_recorded", {
            "outcome": outcome.value,
            "duration": duration,
            "samples": sample_count
        })

    def _update_session_stats(self, recording: PTTRecordingStats):
        """Update session statistics with new recording."""
        session = self.current_session

        # Add to recordings list
        session.recordings.append(recording)

        # Update counts
        session.total_recordings += 1

        if recording.outcome == PTTOutcome.SUCCESS:
            session.successful_recordings += 1
        elif recording.outcome == PTTOutcome.CANCELLED:
            session.cancelled_recordings += 1
        elif recording.outcome == PTTOutcome.TIMEOUT:
            session.timeout_recordings += 1
        elif recording.outcome == PTTOutcome.ERROR:
            session.error_recordings += 1

        # Update duration stats
        session.total_recording_time += recording.duration

        if session.min_duration is None or recording.duration < session.min_duration:
            session.min_duration = recording.duration

        if session.max_duration is None or recording.duration > session.max_duration:
            session.max_duration = recording.duration

        if session.total_recordings > 0:
            session.avg_duration = session.total_recording_time / session.total_recordings

        # Update mode usage
        session.mode_usage[recording.mode] += 1

        # Update performance metrics
        latencies_key_press = [r.key_press_latency for r in session.recordings if r.key_press_latency is not None]
        if latencies_key_press:
            session.avg_key_press_latency = sum(latencies_key_press) / len(latencies_key_press)

        latencies_recording_start = [r.recording_start_latency for r in session.recordings if r.recording_start_latency is not None]
        if latencies_recording_start:
            session.avg_recording_start_latency = sum(latencies_recording_start) / len(latencies_recording_start)

    def _reset_current_recording(self):
        """Reset current recording state."""
        self._current_recording_start = None
        self._current_key_press_time = None
        # Keep enable time for multiple recordings in same session

    def get_summary(self) -> Dict[str, Any]:
        """
        Get session statistics summary.

        Returns:
            Dictionary with session statistics
        """
        session = self.current_session

        return {
            "session": {
                "start": session.session_start,
                "end": session.session_end,
                "duration_seconds": session.session_duration(),
                "is_active": session.session_end is None
            },
            "recordings": {
                "total": session.total_recordings,
                "successful": session.successful_recordings,
                "cancelled": session.cancelled_recordings,
                "timeout": session.timeout_recordings,
                "errors": session.error_recordings
            },
            "rates": {
                "success_rate": session.success_rate(),
                "cancel_rate": session.cancel_rate(),
                "error_rate": session.error_rate()
            },
            "duration": {
                "total_time": session.total_recording_time,
                "min": session.min_duration,
                "max": session.max_duration,
                "average": session.avg_duration
            },
            "mode_usage": dict(session.mode_usage),
            "performance": {
                "avg_key_press_latency": session.avg_key_press_latency,
                "avg_recording_start_latency": session.avg_recording_start_latency
            }
        }

    def get_detailed_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics including individual recordings.

        Returns:
            Dictionary with detailed statistics
        """
        summary = self.get_summary()

        # Add individual recording details
        summary["recording_history"] = [
            {
                "timestamp": r.timestamp,
                "mode": r.mode,
                "duration": r.duration,
                "samples": r.sample_count,
                "outcome": r.outcome.value,
                "key_press_latency": r.key_press_latency,
                "recording_start_latency": r.recording_start_latency,
                "key_combo": r.key_combo,
                "error": r.error_message
            }
            for r in self.current_session.recordings
        ]

        return summary

    def export_to_json(self, filepath: Optional[str] = None) -> str:
        """
        Export statistics to JSON.

        Args:
            filepath: Optional file path to save JSON

        Returns:
            JSON string of statistics
        """
        stats = self.get_detailed_stats()
        json_str = json.dumps(stats, indent=2)

        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write(json_str)

                self.logger.log_event("stats_exported", {"filepath": filepath})

            except Exception as e:
                self.logger.log_error(e, {"context": "export_stats", "filepath": filepath})

        return json_str

    def reset(self):
        """Reset statistics and start a new session."""
        self.current_session = PTTSessionStats()
        self._reset_current_recording()
        self._current_enable_time = None

        self.logger.log_event("statistics_reset")

    def format_summary(self) -> str:
        """
        Format statistics summary as human-readable string.

        Returns:
            Formatted statistics string
        """
        summary = self.get_summary()
        session = summary["session"]
        recordings = summary["recordings"]
        rates = summary["rates"]
        duration = summary["duration"]
        performance = summary["performance"]

        lines = [
            "PTT Session Statistics",
            "=" * 50,
            "",
            f"Session Duration: {session['duration_seconds']:.1f}s",
            f"Status: {'Active' if session['is_active'] else 'Ended'}",
            "",
            "Recordings:",
            f"  Total: {recordings['total']}",
            f"  Successful: {recordings['successful']} ({rates['success_rate']:.1f}%)",
            f"  Cancelled: {recordings['cancelled']} ({rates['cancel_rate']:.1f}%)",
            f"  Errors: {recordings['errors']} ({rates['error_rate']:.1f}%)",
            "",
        ]

        if duration['average'] is not None:
            lines.extend([
                "Recording Duration:",
                f"  Total Time: {duration['total_time']:.1f}s",
                f"  Average: {duration['average']:.2f}s",
                f"  Min: {duration['min']:.2f}s",
                f"  Max: {duration['max']:.2f}s",
                "",
            ])

        if summary['mode_usage']:
            lines.extend([
                "Mode Usage:",
                *[f"  {mode}: {count}" for mode, count in summary['mode_usage'].items()],
                "",
            ])

        if performance['avg_key_press_latency'] is not None:
            lines.extend([
                "Performance:",
                f"  Avg Key Press Latency: {performance['avg_key_press_latency']*1000:.1f}ms",
            ])

        if performance['avg_recording_start_latency'] is not None:
            lines.append(f"  Avg Recording Start Latency: {performance['avg_recording_start_latency']*1000:.1f}ms")

        return "\n".join(lines)


# Global instance
_global_statistics: Optional[PTTStatistics] = None


def get_ptt_statistics() -> PTTStatistics:
    """
    Get or create global PTT statistics instance.

    Returns:
        PTTStatistics instance
    """
    global _global_statistics

    if _global_statistics is None:
        _global_statistics = PTTStatistics()

    return _global_statistics


def reset_ptt_statistics():
    """Reset global PTT statistics instance."""
    global _global_statistics

    if _global_statistics is not None:
        _global_statistics.reset()
    else:
        _global_statistics = PTTStatistics()


def create_statistics_callbacks():
    """
    Create callback functions for PTT controller integration.

    Returns:
        Dictionary of callback functions
    """
    stats = get_ptt_statistics()

    return {
        'on_enabled': lambda mode, key_combo: stats.enable(mode, key_combo),
        'on_key_press': lambda: stats.on_key_press(),
        'on_recording_start': lambda: stats.on_recording_start(),
        'on_recording_stop': lambda audio_data: stats.on_recording_stop(
            duration=len(audio_data) / 16000 if audio_data is not None else 0,  # Assume 16kHz
            sample_count=len(audio_data) if audio_data is not None else 0,
            outcome=PTTOutcome.SUCCESS
        ),
        'on_recording_cancel': lambda: stats.on_recording_stop(
            duration=0,
            sample_count=0,
            outcome=PTTOutcome.CANCELLED
        ),
        'on_error': lambda error: stats.on_recording_stop(
            duration=0,
            sample_count=0,
            outcome=PTTOutcome.ERROR,
            error_message=str(error)
        ),
        'on_disabled': lambda: stats.disable()
    }
