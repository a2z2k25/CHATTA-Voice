"""
PTT Transport Adapter

Bridges the PTT system with CHATTA's existing voice transport layer.
Provides a drop-in replacement for record_audio_with_silence_detection()
that adds keyboard-controlled recording while maintaining interface compatibility.
"""

import time
import logging
import queue
import threading
import asyncio
import numpy as np
from typing import Tuple, Optional, Callable
import voice_mode.config as config
from voice_mode.ptt.controller import PTTController
from voice_mode.ptt.state_machine import PTTState
from voice_mode.ptt.logging import get_ptt_logger
from voice_mode.ptt.visual_feedback import get_visual_feedback
from voice_mode.ptt.audio_feedback import get_audio_feedback

logger = logging.getLogger("voice_mode.ptt.transport_adapter")


class PTTRecordingSession:
    """
    Manages a single PTT recording session in a synchronous context.

    This class bridges the async PTT controller with the synchronous
    recording interface required by the transport layer's executor.
    """

    def __init__(
        self,
        controller: PTTController,
        max_duration: float,
        min_duration: float
    ):
        """
        Initialize recording session.

        Args:
            controller: PTT controller instance
            max_duration: Maximum recording duration (timeout)
            min_duration: Minimum recording duration
        """
        self.controller = controller
        self.max_duration = max_duration
        self.min_duration = min_duration
        self.audio_data: Optional[np.ndarray] = None
        self.speech_detected: bool = False
        self.error: Optional[Exception] = None
        self.completed = threading.Event()

        # Track timing
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def on_recording_start(self) -> None:
        """Callback invoked when recording starts."""
        self.start_time = time.time()
        logger.info("PTT recording started")

        # Show visual feedback
        if config.PTT_VISUAL_FEEDBACK:
            visual = get_visual_feedback()
            visual.on_recording_start()

        # Play audio feedback
        if config.PTT_AUDIO_FEEDBACK:
            audio = get_audio_feedback()
            audio.play_start()

    def on_recording_stop(self, audio_data: np.ndarray) -> None:
        """
        Callback invoked when recording stops successfully.

        Args:
            audio_data: Recorded audio data
        """
        self.audio_data = audio_data
        self.speech_detected = audio_data is not None and len(audio_data) > 0
        self.end_time = time.time()
        self.completed.set()

        if self.start_time:
            duration = self.end_time - self.start_time
            sample_count = len(audio_data) if audio_data is not None else 0
            logger.info(f"PTT recording completed: {duration:.1f}s, {sample_count} samples")

            # Show visual feedback
            if config.PTT_VISUAL_FEEDBACK:
                visual = get_visual_feedback()
                visual.on_recording_stop(duration, sample_count)

            # Play audio feedback
            if config.PTT_AUDIO_FEEDBACK:
                audio = get_audio_feedback()
                audio.play_stop()

    def on_recording_cancel(self) -> None:
        """Callback invoked when recording is cancelled."""
        self.audio_data = None
        self.speech_detected = False
        self.end_time = time.time()
        self.completed.set()

        if self.start_time:
            duration = self.end_time - self.start_time
            logger.info(f"PTT recording cancelled after {duration:.1f}s")

            # Show visual feedback
            if config.PTT_VISUAL_FEEDBACK:
                visual = get_visual_feedback()
                visual.on_recording_cancel(reason="user_cancelled")

            # Play audio feedback
            if config.PTT_AUDIO_FEEDBACK:
                audio = get_audio_feedback()
                audio.play_cancel()

    def on_error(self, error: Exception) -> None:
        """
        Callback invoked when an error occurs.

        Args:
            error: Exception that occurred
        """
        self.error = error
        self.audio_data = None
        self.speech_detected = False
        self.completed.set()
        logger.error(f"PTT recording error: {error}")

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for recording to complete.

        Args:
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if completed, False if timed out
        """
        return self.completed.wait(timeout=timeout)


def _run_event_loop_in_thread(controller: PTTController, stop_event: threading.Event) -> None:
    """
    Run the controller's async event processing loop in a background thread.

    Args:
        controller: PTT controller instance
        stop_event: Event to signal when to stop processing
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run process_events until stop_event is set
        loop.run_until_complete(controller.process_events())
    except Exception as e:
        logger.error(f"Event loop error: {e}")
    finally:
        loop.close()


def record_with_ptt(
    max_duration: float = 120.0,
    disable_silence_detection: bool = False,
    min_duration: float = 2.0,
    vad_aggressiveness: int = 2
) -> Tuple[np.ndarray, bool]:
    """
    Record audio using PTT keyboard control.

    This function provides a drop-in replacement for record_audio_with_silence_detection()
    that adds keyboard-triggered recording while maintaining interface compatibility.

    The function operates synchronously and blocks until recording completes or times out.
    This makes it suitable for use with asyncio.get_event_loop().run_in_executor().

    Recording Flow:
    1. Enable PTT controller
    2. Wait for user to press configured key combination
    3. Start recording on key press
    4. Stop recording based on PTT mode:
       - Hold: User releases key (after min_duration)
       - Toggle: User presses key again
       - Hybrid: User releases key OR silence detected
    5. Return audio data

    Args:
        max_duration: Maximum recording duration in seconds (becomes PTT timeout)
        disable_silence_detection: If True, disables VAD in hybrid mode
        min_duration: Minimum recording duration in seconds
        vad_aggressiveness: VAD sensitivity (0-3) for hybrid mode

    Returns:
        Tuple of (audio_data, speech_detected):
        - audio_data: numpy array with dtype='int16', or empty array if no audio
        - speech_detected: True if audio was recorded, False otherwise

    Raises:
        Exception: If PTT system fails to initialize or recording fails unrecoverably

    Example:
        >>> # Use in async context with executor
        >>> audio_data, speech = await loop.run_in_executor(
        ...     None, record_with_ptt, 30.0, False, 2.0, 2
        ... )
    """
    ptt_logger = get_ptt_logger()
    ptt_logger.log_event("transport_adapter_start", {
        "max_duration": max_duration,
        "disable_silence_detection": disable_silence_detection,
        "min_duration": min_duration,
        "vad_aggressiveness": vad_aggressiveness,
        "ptt_mode": config.PTT_MODE
    })

    logger.info(f"Starting PTT recording session (mode={config.PTT_MODE}, max_duration={max_duration}s)")

    # Determine effective mode based on config and parameters
    effective_mode = config.PTT_MODE
    if effective_mode == "hybrid" and disable_silence_detection:
        # If silence detection is explicitly disabled, use hold mode instead
        effective_mode = "hold"
        logger.info("Silence detection disabled - switching from hybrid to hold mode")

    # Create session object for state management
    session: Optional[PTTRecordingSession] = None
    controller: Optional[PTTController] = None

    try:
        # Create PTT controller with appropriate configuration
        controller = PTTController(
            key_combo=config.PTT_KEY_COMBO,
            cancel_key=config.PTT_CANCEL_KEY,
            timeout=max_duration
        )

        # Create session to manage this recording
        session = PTTRecordingSession(controller, max_duration, min_duration)

        # Register callbacks (use underscore for internal attributes)
        controller._on_recording_start = session.on_recording_start
        controller._on_recording_stop = session.on_recording_stop
        controller._on_recording_cancel = session.on_recording_cancel

        # Enable controller
        if not controller.enable():
            raise RuntimeError("Failed to enable PTT controller")

        # Start event processing loop in background thread
        event_thread = threading.Thread(
            target=_run_event_loop_in_thread,
            args=(controller, controller._stop_event),
            daemon=True
        )
        event_thread.start()
        logger.debug("PTT event processing thread started")

        logger.info("PTT controller enabled - waiting for key press...")
        ptt_logger.log_event("waiting_for_key_press", {
            "key_combo": config.PTT_KEY_COMBO,
            "cancel_key": config.PTT_CANCEL_KEY
        })

        # Show visual feedback that PTT is ready and waiting
        if config.PTT_VISUAL_FEEDBACK:
            visual = get_visual_feedback()
            visual.enable(
                mode=config.PTT_MODE,
                key_combo=config.PTT_KEY_COMBO,
                cancel_key=config.PTT_CANCEL_KEY
            )

        # Play audio feedback that PTT is ready
        if config.PTT_AUDIO_FEEDBACK:
            audio = get_audio_feedback()
            audio.play_waiting()

        # Wait for recording to complete
        # (start_time will be set by on_recording_start callback)
        # Add extra time to max_duration for key press delay
        total_timeout = max_duration + 30.0  # 30s buffer for user to press key

        if not session.wait_for_completion(timeout=total_timeout):
            logger.warning(f"PTT recording timed out after {total_timeout}s")
            controller.disable()

            ptt_logger.log_event("transport_adapter_timeout", {
                "timeout": total_timeout
            })

            return (np.array([], dtype='int16'), False)

        # Check for errors
        if session.error:
            logger.error(f"PTT recording failed: {session.error}")
            raise session.error

        # Get results
        audio_data = session.audio_data if session.audio_data is not None else np.array([], dtype='int16')
        speech_detected = session.speech_detected

        # Log completion
        ptt_logger.log_event("transport_adapter_complete", {
            "audio_samples": len(audio_data),
            "speech_detected": speech_detected,
            "duration": session.end_time - session.start_time if session.start_time and session.end_time else 0
        })

        logger.info(f"PTT recording complete: {len(audio_data)} samples, speech_detected={speech_detected}")

        return (audio_data, speech_detected)

    except Exception as e:
        logger.error(f"PTT recording error: {e}")
        ptt_logger.log_error(e, {
            "context": "transport_adapter",
            "max_duration": max_duration,
            "min_duration": min_duration
        })

        # Re-raise the exception for caller to handle
        raise

    finally:
        # Always cleanup
        if controller:
            try:
                controller.disable()
                logger.debug("PTT controller disabled")
            except Exception as cleanup_error:
                logger.error(f"Error during PTT cleanup: {cleanup_error}")

        # Disable visual feedback
        if config.PTT_VISUAL_FEEDBACK:
            try:
                visual = get_visual_feedback()
                visual.disable()
            except Exception as visual_cleanup_error:
                logger.error(f"Error during visual feedback cleanup: {visual_cleanup_error}")


def record_with_ptt_fallback(
    max_duration: float = 120.0,
    disable_silence_detection: bool = False,
    min_duration: float = 2.0,
    vad_aggressiveness: int = 2
) -> Tuple[np.ndarray, bool]:
    """
    Attempt PTT recording with automatic fallback to standard recording.

    This function wraps record_with_ptt() with error handling that falls back
    to the standard record_audio_with_silence_detection() if PTT fails.

    Args:
        max_duration: Maximum recording duration
        disable_silence_detection: Disable VAD
        min_duration: Minimum recording duration
        vad_aggressiveness: VAD sensitivity

    Returns:
        Tuple of (audio_data, speech_detected)
    """
    try:
        return record_with_ptt(max_duration, disable_silence_detection, min_duration, vad_aggressiveness)
    except Exception as e:
        logger.warning(f"PTT recording failed, falling back to standard recording: {e}")

        # Import standard recording function
        from voice_mode.tools.converse import record_audio_with_silence_detection

        # Fall back to standard recording
        return record_audio_with_silence_detection(
            max_duration=max_duration,
            disable_silence_detection=disable_silence_detection,
            min_duration=min_duration,
            vad_aggressiveness=vad_aggressiveness
        )


def get_recording_function(
    ptt_enabled: bool = None
) -> Callable[[float, bool, float, int], Tuple[np.ndarray, bool]]:
    """
    Get the appropriate recording function based on PTT configuration.

    This function returns either the PTT recording function or the standard
    recording function based on configuration.

    Args:
        ptt_enabled: Override for PTT_ENABLED config (None = use config value)

    Returns:
        Recording function with signature:
        (max_duration, disable_silence_detection, min_duration, vad_aggressiveness)
        -> (audio_data, speech_detected)

    Example:
        >>> record_func = get_recording_function()
        >>> audio_data, speech = await loop.run_in_executor(
        ...     None, record_func, 30.0, False, 2.0, 2
        ... )
    """
    # Determine if PTT is enabled
    if ptt_enabled is None:
        ptt_enabled = config.PTT_ENABLED

    if ptt_enabled:
        logger.debug("Using PTT recording function")
        return record_with_ptt_fallback
    else:
        logger.debug("Using standard recording function")
        from voice_mode.tools.converse import record_audio_with_silence_detection
        return record_audio_with_silence_detection


# Module-level export for convenience
__all__ = [
    'record_with_ptt',
    'record_with_ptt_fallback',
    'get_recording_function',
    'PTTRecordingSession'
]
