"""
PTT audio feedback system.

Provides audio cues for PTT events using generated tones.
Integrates with existing voice_mode audio feedback system.
"""

import threading
import numpy as np
from typing import Optional
from enum import Enum

from voice_mode.ptt.audio_tones import (
    ptt_start_tone,
    ptt_stop_tone,
    ptt_cancel_tone,
    ptt_waiting_tone,
    ptt_error_tone
)
from voice_mode.ptt.logging import get_ptt_logger


class PTTAudioEvent(Enum):
    """PTT audio events."""

    WAITING = "waiting"        # PTT enabled, waiting for key press
    START = "start"            # Recording started
    STOP = "stop"              # Recording stopped normally
    CANCEL = "cancel"          # Recording cancelled
    ERROR = "error"            # Error occurred


class PTTAudioFeedback:
    """
    Manages audio feedback for PTT events.

    Generates and plays audio cues for PTT state changes with
    configurable volume and enable/disable control.
    """

    def __init__(
        self,
        enabled: bool = True,
        volume: float = 0.7,
        sample_rate: int = 44100
    ):
        """
        Initialize PTT audio feedback.

        Args:
            enabled: Enable audio feedback
            volume: Volume level 0.0-1.0
            sample_rate: Audio sample rate
        """
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))  # Clamp to 0-1
        self.sample_rate = sample_rate
        self.logger = get_ptt_logger()

        # Audio cache
        self._tone_cache = {}
        self._cache_lock = threading.Lock()

        # Pre-generate tones
        if self.enabled:
            self._pregenerate_tones()

    def _pregenerate_tones(self):
        """Pre-generate all tones for faster playback."""
        try:
            with self._cache_lock:
                self._tone_cache = {
                    PTTAudioEvent.WAITING: ptt_waiting_tone(self.volume, self.sample_rate),
                    PTTAudioEvent.START: ptt_start_tone(self.volume, self.sample_rate),
                    PTTAudioEvent.STOP: ptt_stop_tone(self.volume, self.sample_rate),
                    PTTAudioEvent.CANCEL: ptt_cancel_tone(self.volume, self.sample_rate),
                    PTTAudioEvent.ERROR: ptt_error_tone(self.volume, self.sample_rate),
                }

            self.logger.log_event("audio_tones_pregenerated", {
                "count": len(self._tone_cache),
                "sample_rate": self.sample_rate
            })

        except Exception as e:
            self.logger.log_error(e, {"context": "pregenerate_tones"})

    def play_event(self, event: PTTAudioEvent, blocking: bool = False):
        """
        Play audio cue for PTT event.

        Args:
            event: PTT audio event
            blocking: Wait for playback to complete (default: non-blocking)
        """
        if not self.enabled:
            return

        try:
            # Get tone from cache
            with self._cache_lock:
                tone = self._tone_cache.get(event)

            if tone is None:
                self.logger.log_event("audio_tone_not_found", {"event": event.value})
                return

            # Play tone using sounddevice
            self._play_audio(tone, blocking=blocking)

            self.logger.log_event("audio_feedback_played", {
                "event": event.value,
                "blocking": blocking,
                "samples": len(tone)
            })

        except Exception as e:
            self.logger.log_error(e, {
                "context": "play_event",
                "event": event.value
            })

    def _play_audio(self, audio: np.ndarray, blocking: bool = False):
        """
        Play audio samples.

        Args:
            audio: Audio samples (int16)
            blocking: Wait for playback to complete
        """
        try:
            import sounddevice as sd

            # Normalize to float32 for sounddevice
            audio_float = audio.astype(np.float32) / 32767.0

            # Play audio
            sd.play(audio_float, samplerate=self.sample_rate, blocking=blocking)

        except ImportError:
            self.logger.log_event("sounddevice_not_available")
        except Exception as e:
            self.logger.log_error(e, {"context": "play_audio"})

    def play_waiting(self, blocking: bool = False):
        """Play waiting/ready tone."""
        self.play_event(PTTAudioEvent.WAITING, blocking=blocking)

    def play_start(self, blocking: bool = False):
        """Play recording start tone."""
        self.play_event(PTTAudioEvent.START, blocking=blocking)

    def play_stop(self, blocking: bool = False):
        """Play recording stop tone."""
        self.play_event(PTTAudioEvent.STOP, blocking=blocking)

    def play_cancel(self, blocking: bool = False):
        """Play recording cancel tone."""
        self.play_event(PTTAudioEvent.CANCEL, blocking=blocking)

    def play_error(self, blocking: bool = False):
        """Play error tone."""
        self.play_event(PTTAudioEvent.ERROR, blocking=blocking)

    def set_volume(self, volume: float):
        """
        Set volume and regenerate tones.

        Args:
            volume: Volume level 0.0-1.0
        """
        self.volume = max(0.0, min(1.0, volume))

        if self.enabled:
            self._pregenerate_tones()

        self.logger.log_event("volume_changed", {"volume": self.volume})

    def enable(self):
        """Enable audio feedback."""
        if not self.enabled:
            self.enabled = True
            self._pregenerate_tones()
            self.logger.log_event("audio_feedback_enabled")

    def disable(self):
        """Disable audio feedback."""
        if self.enabled:
            self.enabled = False

            # Clear cache to free memory
            with self._cache_lock:
                self._tone_cache.clear()

            self.logger.log_event("audio_feedback_disabled")

    def stop_all(self):
        """Stop all currently playing audio."""
        try:
            import sounddevice as sd
            sd.stop()
        except (ImportError, Exception) as e:
            pass


# Global instance
_global_audio_feedback: Optional[PTTAudioFeedback] = None


def get_audio_feedback() -> PTTAudioFeedback:
    """
    Get or create global PTT audio feedback instance.

    Returns:
        PTTAudioFeedback instance
    """
    global _global_audio_feedback

    if _global_audio_feedback is None:
        from voice_mode import config

        # Get configuration
        enabled = getattr(config, 'PTT_AUDIO_FEEDBACK', True)
        volume = getattr(config, 'PTT_FEEDBACK_VOLUME', 0.7)

        _global_audio_feedback = PTTAudioFeedback(
            enabled=enabled,
            volume=volume
        )

    return _global_audio_feedback


def reset_audio_feedback():
    """Reset global audio feedback instance."""
    global _global_audio_feedback

    if _global_audio_feedback is not None:
        _global_audio_feedback.stop_all()
        _global_audio_feedback.disable()

    _global_audio_feedback = None


def create_audio_feedback_callbacks():
    """
    Create callback functions for PTT controller integration.

    Returns:
        Dictionary of callback functions
    """
    feedback = get_audio_feedback()

    return {
        'on_enabled': lambda: feedback.play_waiting(blocking=False),
        'on_recording_start': lambda: feedback.play_start(blocking=False),
        'on_recording_stop': lambda audio_data: feedback.play_stop(blocking=False),
        'on_recording_cancel': lambda: feedback.play_cancel(blocking=False),
        'on_error': lambda error: feedback.play_error(blocking=False)
    }


def play_ptt_tone(event: str, volume: Optional[float] = None, blocking: bool = False):
    """
    Convenience function to play a PTT tone.

    Args:
        event: Event name ("waiting", "start", "stop", "cancel", "error")
        volume: Optional volume override
        blocking: Wait for playback to complete

    Example:
        play_ptt_tone("start")
        play_ptt_tone("stop", volume=0.5)
    """
    feedback = get_audio_feedback()

    # Temporarily override volume if provided
    original_volume = None
    if volume is not None:
        original_volume = feedback.volume
        feedback.set_volume(volume)

    try:
        # Map event name to enum
        event_map = {
            'waiting': PTTAudioEvent.WAITING,
            'start': PTTAudioEvent.START,
            'stop': PTTAudioEvent.STOP,
            'cancel': PTTAudioEvent.CANCEL,
            'error': PTTAudioEvent.ERROR
        }

        audio_event = event_map.get(event.lower())
        if audio_event:
            feedback.play_event(audio_event, blocking=blocking)

    finally:
        # Restore original volume
        if original_volume is not None:
            feedback.set_volume(original_volume)
