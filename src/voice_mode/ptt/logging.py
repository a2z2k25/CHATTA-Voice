"""
Logging infrastructure for Push-to-Talk module.

Provides structured logging for PTT events, keyboard monitoring,
performance metrics, and debugging support.
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import voice_mode.config as config

# PTT-specific logger
logger = logging.getLogger("voice_mode.ptt")


@dataclass
class PTTEvent:
    """Structured PTT event for logging"""
    timestamp: float
    event_type: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class PTTLogger:
    """
    Centralized logging for PTT operations.

    Handles debug logging, event logging, and performance metrics
    with configurable verbosity levels.
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize PTT logger.

        Args:
            session_id: Optional session identifier for grouping logs
        """
        self.session_id = session_id or self._generate_session_id()
        self.events = []
        self.timing_data = {}
        self._setup_logger()

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID"""
        return f"ptt_{int(time.time() * 1000)}"

    def _setup_logger(self):
        """Configure logger based on config settings"""
        # Set log level based on debug flags
        if config.PTT_DEBUG:
            logger.setLevel(logging.DEBUG)
        elif config.DEBUG:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.WARNING)

        # Add file handler if event logging is enabled
        if config.EVENT_LOG_ENABLED:
            self._add_file_handler()

    def _add_file_handler(self):
        """Add file handler for PTT event logging"""
        log_dir = Path(config.EVENT_LOG_DIR) / "ptt"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log rotation
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"ptt_events_{date_str}.jsonl"

        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)

        # JSON format for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": %(message)s}'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        duration_ms: Optional[float] = None
    ):
        """
        Log a PTT event.

        Args:
            event_type: Type of event (e.g., "key_press", "recording_start")
            data: Event-specific data
            duration_ms: Optional duration in milliseconds
        """
        event = PTTEvent(
            timestamp=time.time(),
            event_type=event_type,
            data=data,
            duration_ms=duration_ms,
            session_id=self.session_id
        )

        # Store event for session analysis
        self.events.append(event)

        # Log to file if enabled
        if config.EVENT_LOG_ENABLED:
            logger.info(event.to_json())

        # Console debug output
        if config.PTT_DEBUG:
            self._log_to_console(event)

    def _log_to_console(self, event: PTTEvent):
        """Format and log event to console"""
        msg = f"[PTT] {event.event_type}"
        if event.duration_ms:
            msg += f" ({event.duration_ms:.1f}ms)"
        if event.data:
            msg += f" | {event.data}"
        logger.debug(msg)

    def log_key_event(self, key: str, action: str, metadata: Optional[Dict] = None):
        """
        Log keyboard event.

        Args:
            key: Key name
            action: "press" or "release"
            metadata: Additional event metadata
        """
        # Only log if key logging is enabled (verbose)
        if not config.PTT_LOG_KEYS:
            return

        data = {
            "key": key,
            "action": action
        }
        if metadata:
            data.update(metadata)

        self.log_event(f"key_{action}", data)

    def start_timer(self, operation: str) -> str:
        """
        Start timing an operation.

        Args:
            operation: Operation name

        Returns:
            Timer ID for stopping the timer
        """
        timer_id = f"{operation}_{time.time()}"
        self.timing_data[timer_id] = {
            "operation": operation,
            "start_time": time.time()
        }
        return timer_id

    def stop_timer(self, timer_id: str) -> float:
        """
        Stop timing an operation and log the result.

        Args:
            timer_id: ID returned from start_timer

        Returns:
            Duration in milliseconds
        """
        if timer_id not in self.timing_data:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0

        timing = self.timing_data[timer_id]
        duration_ms = (time.time() - timing["start_time"]) * 1000

        self.log_event(
            "timing",
            {"operation": timing["operation"]},
            duration_ms=duration_ms
        )

        del self.timing_data[timer_id]
        return duration_ms

    def log_performance_metrics(self, metrics: Dict[str, float]):
        """
        Log performance metrics.

        Args:
            metrics: Dictionary of metric name -> value (in ms)
        """
        self.log_event("performance_metrics", metrics)

        # Log warnings for slow operations
        thresholds = {
            "key_detection": 10.0,  # Should be < 10ms
            "recording_start": 100.0,  # Should be < 100ms
            "audio_processing": 50.0  # Should be < 50ms
        }

        for metric_name, value in metrics.items():
            threshold = thresholds.get(metric_name)
            if threshold and value > threshold:
                logger.warning(
                    f"Performance: {metric_name} took {value:.1f}ms "
                    f"(threshold: {threshold:.1f}ms)"
                )

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """
        Log an error with context.

        Args:
            error: Exception that occurred
            context: Additional context about the error
        """
        data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        self.log_event("error", data)
        logger.error(f"PTT Error: {error}", exc_info=config.PTT_DEBUG)

    def log_state_transition(self, from_state: str, to_state: str, trigger: str):
        """
        Log state machine transition.

        Args:
            from_state: Previous state
            to_state: New state
            trigger: What triggered the transition
        """
        data = {
            "from": from_state,
            "to": to_state,
            "trigger": trigger
        }
        self.log_event("state_transition", data)
        logger.debug(f"PTT State: {from_state} -> {to_state} ({trigger})")

    def log_recording_session(
        self,
        duration: float,
        audio_length: int,
        transcription: Optional[str] = None
    ):
        """
        Log completed recording session.

        Args:
            duration: Recording duration in seconds
            audio_length: Length of audio data in bytes
            transcription: Optional transcribed text
        """
        data = {
            "duration_seconds": duration,
            "audio_bytes": audio_length,
            "has_transcription": transcription is not None
        }
        if transcription and config.SAVE_TRANSCRIPTIONS:
            data["transcription_length"] = len(transcription)

        self.log_event("recording_session", data, duration_ms=duration * 1000)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session events.

        Returns:
            Dictionary with session statistics
        """
        event_counts = {}
        total_duration = 0.0

        for event in self.events:
            event_type = event.event_type
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            if event.duration_ms:
                total_duration += event.duration_ms

        return {
            "session_id": self.session_id,
            "total_events": len(self.events),
            "event_types": event_counts,
            "total_duration_ms": total_duration,
            "session_start": self.events[0].timestamp if self.events else None,
            "session_end": self.events[-1].timestamp if self.events else None
        }

    def export_session(self, output_path: Optional[Path] = None) -> Path:
        """
        Export session events to JSON file.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to exported file
        """
        if output_path is None:
            log_dir = Path(config.LOGS_DIR) / "ptt" / "sessions"
            log_dir.mkdir(parents=True, exist_ok=True)
            output_path = log_dir / f"{self.session_id}.json"

        session_data = {
            "summary": self.get_session_summary(),
            "events": [event.to_dict() for event in self.events]
        }

        with open(output_path, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"Session exported to {output_path}")
        return output_path


# Global PTT logger instance (will be initialized when PTT is enabled)
_ptt_logger: Optional[PTTLogger] = None


def get_ptt_logger() -> PTTLogger:
    """
    Get or create the global PTT logger instance.

    Returns:
        PTT logger instance
    """
    global _ptt_logger
    if _ptt_logger is None:
        _ptt_logger = PTTLogger()
    return _ptt_logger


def reset_ptt_logger():
    """Reset the global PTT logger (useful for testing)"""
    global _ptt_logger
    _ptt_logger = None
