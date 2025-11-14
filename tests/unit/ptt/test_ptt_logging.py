"""
Unit tests for PTT logging infrastructure.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from voice_mode.ptt.logging import (
    PTTEvent,
    PTTLogger,
    get_ptt_logger,
    reset_ptt_logger
)


class TestPTTEvent:
    """Test PTT event structure"""

    def test_event_creation(self):
        """Test creating a PTT event"""
        event = PTTEvent(
            timestamp=time.time(),
            event_type="test_event",
            data={"key": "value"},
            duration_ms=10.5
        )

        assert event.event_type == "test_event"
        assert event.data == {"key": "value"}
        assert event.duration_ms == 10.5
        assert event.timestamp > 0

    def test_event_to_dict(self):
        """Test converting event to dictionary"""
        event = PTTEvent(
            timestamp=123.456,
            event_type="test",
            data={"test": True}
        )

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert event_dict["timestamp"] == 123.456
        assert event_dict["event_type"] == "test"
        assert event_dict["data"]["test"] is True

    def test_event_to_json(self):
        """Test converting event to JSON"""
        event = PTTEvent(
            timestamp=123.456,
            event_type="test",
            data={"key": "value"}
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "test"
        assert parsed["data"]["key"] == "value"


class TestPTTLogger:
    """Test PTT logger functionality"""

    def test_logger_initialization(self):
        """Test logger initialization"""
        logger = PTTLogger()

        assert logger.session_id is not None
        assert logger.session_id.startswith("ptt_")
        assert len(logger.events) == 0
        assert len(logger.timing_data) == 0

    def test_custom_session_id(self):
        """Test logger with custom session ID"""
        logger = PTTLogger(session_id="custom_session_123")

        assert logger.session_id == "custom_session_123"

    def test_log_event(self):
        """Test logging an event"""
        logger = PTTLogger()

        logger.log_event(
            "test_event",
            {"key": "value"},
            duration_ms=15.5
        )

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == "test_event"
        assert event.data["key"] == "value"
        assert event.duration_ms == 15.5

    def test_log_key_event_requires_flag(self, monkeypatch):
        """Test that key events only log when PTT_LOG_KEYS is True"""
        logger = PTTLogger()

        # Default: PTT_LOG_KEYS is False
        import voice_mode.config as config
        monkeypatch.setattr(config, "PTT_LOG_KEYS", False)

        logger.log_key_event("space", "press")
        assert len(logger.events) == 0  # Should not log

        # Enable key logging
        monkeypatch.setattr(config, "PTT_LOG_KEYS", True)

        logger.log_key_event("space", "press")
        assert len(logger.events) == 1  # Should log now

    def test_start_stop_timer(self):
        """Test timing operations"""
        logger = PTTLogger()

        timer_id = logger.start_timer("test_operation")
        assert timer_id in logger.timing_data

        time.sleep(0.01)  # 10ms

        duration = logger.stop_timer(timer_id)
        assert duration >= 10.0  # At least 10ms
        assert timer_id not in logger.timing_data  # Cleaned up

        # Should have timing event logged
        timing_events = [e for e in logger.events if e.event_type == "timing"]
        assert len(timing_events) == 1
        assert timing_events[0].data["operation"] == "test_operation"

    def test_log_performance_metrics(self):
        """Test logging performance metrics"""
        logger = PTTLogger()

        metrics = {
            "key_detection": 5.0,
            "recording_start": 85.0,
            "audio_processing": 30.0
        }

        logger.log_performance_metrics(metrics)

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == "performance_metrics"
        assert event.data == metrics

    def test_log_error(self):
        """Test error logging"""
        logger = PTTLogger()

        error = ValueError("Test error message")
        context = {"operation": "test", "details": "something went wrong"}

        logger.log_error(error, context)

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == "error"
        assert event.data["error_type"] == "ValueError"
        assert event.data["error_message"] == "Test error message"
        assert event.data["context"] == context

    def test_log_state_transition(self):
        """Test state transition logging"""
        logger = PTTLogger()

        logger.log_state_transition("IDLE", "RECORDING", "key_press")

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == "state_transition"
        assert event.data["from"] == "IDLE"
        assert event.data["to"] == "RECORDING"
        assert event.data["trigger"] == "key_press"

    def test_log_recording_session(self):
        """Test recording session logging"""
        logger = PTTLogger()

        logger.log_recording_session(
            duration=3.5,
            audio_length=56000,
            transcription="test transcription"
        )

        assert len(logger.events) == 1
        event = logger.events[0]
        assert event.event_type == "recording_session"
        assert event.data["duration_seconds"] == 3.5
        assert event.data["audio_bytes"] == 56000
        assert event.data["has_transcription"] is True

    def test_get_session_summary(self):
        """Test session summary generation"""
        logger = PTTLogger()

        # Log various events
        logger.log_event("event1", {}, duration_ms=10.0)
        logger.log_event("event2", {}, duration_ms=20.0)
        logger.log_event("event1", {}, duration_ms=15.0)

        summary = logger.get_session_summary()

        assert summary["session_id"] == logger.session_id
        assert summary["total_events"] == 3
        assert summary["event_types"]["event1"] == 2
        assert summary["event_types"]["event2"] == 1
        assert summary["total_duration_ms"] == 45.0

    def test_export_session(self, tmp_path):
        """Test exporting session to file"""
        logger = PTTLogger()

        # Log some events
        logger.log_event("test_event", {"data": "value"})
        logger.log_event("another_event", {"num": 42})

        # Export to temp file
        output_file = tmp_path / "test_session.json"
        result_path = logger.export_session(output_file)

        assert result_path == output_file
        assert output_file.exists()

        # Verify contents
        with open(output_file) as f:
            data = json.load(f)

        assert "summary" in data
        assert "events" in data
        assert len(data["events"]) == 2
        assert data["summary"]["total_events"] == 2


class TestGlobalLogger:
    """Test global logger instance management"""

    def test_get_ptt_logger(self):
        """Test getting global logger instance"""
        reset_ptt_logger()  # Start fresh

        logger1 = get_ptt_logger()
        logger2 = get_ptt_logger()

        # Should return same instance
        assert logger1 is logger2

    def test_reset_ptt_logger(self):
        """Test resetting global logger"""
        logger1 = get_ptt_logger()
        logger1.log_event("test", {})

        reset_ptt_logger()

        logger2 = get_ptt_logger()

        # Should be new instance
        assert logger1 is not logger2
        assert len(logger2.events) == 0
