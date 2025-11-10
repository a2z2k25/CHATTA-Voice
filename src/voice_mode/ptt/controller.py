"""
PTT Controller - Orchestrates all PTT components.

This module provides the main PTTController class that coordinates
keyboard handling, state management, and logging for Push-to-Talk.
"""

import asyncio
import time
from typing import Optional, Callable, Dict, Any
from queue import Queue, Empty
from threading import Event

from voice_mode import config
from .keyboard import KeyboardHandler
from .state_machine import PTTStateMachine, PTTState
from .logging import PTTLogger, get_ptt_logger
from .recorder import AsyncPTTRecorder


class PTTController:
    """Main PTT controller that orchestrates all components.

    The PTTController coordinates:
    - Keyboard event handling (KeyboardHandler)
    - State machine management (PTTStateMachine)
    - Event logging (PTTLogger)
    - Audio recording callbacks (provided by caller)

    It provides both sync keyboard event handling and async audio
    integration through a thread-safe event queue.

    Example:
        >>> async def record_callback():
        ...     # Your recording logic
        ...     return audio_data

        >>> controller = PTTController(
        ...     key_combo="down+right",
        ...     on_recording_start=record_callback
        ... )

        >>> # Enable PTT
        >>> controller.enable()

        >>> # Wait for events
        >>> await controller.wait_for_completion()

        >>> # Disable PTT
        >>> controller.disable()
    """

    def __init__(
        self,
        key_combo: Optional[str] = None,
        cancel_key: Optional[str] = None,
        on_recording_start: Optional[Callable[[], Any]] = None,
        on_recording_stop: Optional[Callable[[Any], None]] = None,
        on_recording_cancel: Optional[Callable[[], None]] = None,
        logger: Optional[PTTLogger] = None,
        timeout: Optional[float] = None
    ):
        """Initialize PTT controller.

        Args:
            key_combo: Key combination for PTT (default from config)
            cancel_key: Key to cancel recording (default from config)
            on_recording_start: Callback when recording starts
            on_recording_stop: Callback when recording stops (receives audio data)
            on_recording_cancel: Callback when recording is cancelled
            logger: PTTLogger instance (default: global logger)
            timeout: Maximum recording duration in seconds (default from config)
        """
        # Configuration
        self._key_combo = key_combo or config.PTT_KEY_COMBO
        self._cancel_key = cancel_key or config.PTT_CANCEL_KEY
        self._timeout = timeout or config.PTT_TIMEOUT
        self._mode = config.PTT_MODE
        self._min_duration = config.PTT_MIN_DURATION

        # Components
        self._logger = logger or get_ptt_logger()
        self._state_machine = PTTStateMachine(
            logger=self._logger,
            on_state_change=self._on_state_change
        )
        self._keyboard: Optional[KeyboardHandler] = None
        self._recorder = AsyncPTTRecorder(logger=self._logger)

        # Callbacks
        self._on_recording_start = on_recording_start
        self._on_recording_stop = on_recording_stop
        self._on_recording_cancel = on_recording_cancel

        # Thread coordination
        self._event_queue: Queue = Queue()
        self._stop_event = Event()
        self._enabled = False

        # Recording state
        self._recording_start_time: Optional[float] = None
        self._recording_task: Optional[asyncio.Task] = None
        self._timeout_task: Optional[asyncio.Task] = None
        self._key_press_time: Optional[float] = None

        # Toggle mode state
        self._toggle_active = False  # True when recording via toggle mode

        # Hybrid mode state
        self._hybrid_silence_timeout = config.SILENCE_THRESHOLD_MS / 1000.0  # Convert ms to seconds
        self._hybrid_silence_task: Optional[asyncio.Task] = None

        # Error recovery
        self._max_retries = 3
        self._retry_count = 0

        # Log initialization
        self._logger.log_event("controller_initialized", {
            "key_combo": self._key_combo,
            "cancel_key": self._cancel_key,
            "timeout": self._timeout
        })

    @property
    def is_enabled(self) -> bool:
        """Check if PTT is currently enabled."""
        return self._enabled

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._state_machine.is_recording()

    @property
    def current_state(self) -> PTTState:
        """Get current state machine state."""
        return self._state_machine.current_state

    @property
    def current_state_name(self) -> str:
        """Get current state as string."""
        return self._state_machine.current_state_name

    def enable(self) -> bool:
        """Enable PTT mode.

        Starts keyboard listener and transitions to WAITING_FOR_KEY state.

        Returns:
            True if enabled successfully, False if already enabled

        Example:
            >>> controller = PTTController()
            >>> controller.enable()
            True
            >>> controller.is_enabled
            True
        """
        if self._enabled:
            self._logger.log_event("enable_skipped", {
                "reason": "already_enabled"
            })
            return False

        # Create keyboard handler
        self._keyboard = KeyboardHandler(
            key_combo=self._key_combo,
            on_press_callback=self._on_key_press,
            on_release_callback=self._on_key_release
        )

        # Start keyboard listener
        if not self._keyboard.start():
            self._logger.log_error(
                RuntimeError("Failed to start keyboard listener"),
                {"key_combo": self._key_combo}
            )
            return False

        # Transition to waiting state
        self._state_machine.transition(
            PTTState.WAITING_FOR_KEY,
            trigger="enable_ptt"
        )

        self._enabled = True
        self._stop_event.clear()

        self._logger.log_event("ptt_enabled", {
            "key_combo": self._key_combo,
            "state": self.current_state_name
        })

        return True

    def disable(self) -> bool:
        """Disable PTT mode.

        Stops keyboard listener and returns to IDLE state.

        Returns:
            True if disabled successfully, False if not enabled

        Example:
            >>> controller.disable()
            True
            >>> controller.is_enabled
            False
        """
        if not self._enabled:
            return False

        # Stop keyboard listener
        if self._keyboard:
            self._keyboard.stop()
            self._keyboard = None

        # Cancel any ongoing recording
        if self.is_recording:
            self._cancel_recording()

        # Transition to IDLE
        if self._state_machine.current_state != PTTState.IDLE:
            # May need to go through intermediate states
            if self._state_machine.can_transition(PTTState.IDLE):
                self._state_machine.transition(PTTState.IDLE, trigger="disable_ptt")
            else:
                # Force reset
                self._state_machine.reset()

        self._enabled = False
        self._stop_event.set()

        self._logger.log_event("ptt_disabled", {
            "final_state": self.current_state_name
        })

        return True

    def _on_key_press(self) -> None:
        """Handle key combo press event (called by KeyboardHandler).

        Behavior depends on configured mode:
        - Hold mode: Records press time, queues recording start on press
        - Toggle mode: Toggles recording on/off with each press
        - Hybrid mode: Like hold mode, but with automatic silence detection
        """
        if not self._enabled:
            return

        current_state = self._state_machine.current_state

        # Toggle mode: press once to start, press again to stop
        if self._mode == "toggle":
            if current_state == PTTState.WAITING_FOR_KEY and not self._toggle_active:
                # Start recording (first press)
                self._toggle_active = True

                # Transition to KEY_PRESSED
                self._state_machine.transition(
                    PTTState.KEY_PRESSED,
                    trigger="key_down"
                )

                # Queue recording start
                self._event_queue.put({
                    "type": "start_recording",
                    "timestamp": time.time()
                })

                self._logger.log_event("toggle_started", {
                    "mode": "toggle"
                })

            elif current_state == PTTState.RECORDING and self._toggle_active:
                # Stop recording (second press)
                self._toggle_active = False

                # Transition to RECORDING_STOPPED
                self._state_machine.transition(
                    PTTState.RECORDING_STOPPED,
                    trigger="toggle_off"
                )

                # Queue recording stop
                self._event_queue.put({
                    "type": "stop_recording",
                    "timestamp": time.time()
                })

                self._logger.log_event("toggle_stopped", {
                    "mode": "toggle"
                })

        # Hold or Hybrid mode: press and hold to record
        else:
            if current_state == PTTState.WAITING_FOR_KEY:
                # Record press time for minimum duration check (hold/hybrid)
                self._key_press_time = time.time()

                # Transition to KEY_PRESSED
                self._state_machine.transition(
                    PTTState.KEY_PRESSED,
                    trigger="key_down"
                )

                # Queue recording start
                self._event_queue.put({
                    "type": "start_recording",
                    "timestamp": self._key_press_time
                })

                # Log mode-specific event
                if self._mode == "hybrid":
                    self._logger.log_event("hybrid_started", {
                        "mode": "hybrid",
                        "silence_timeout": self._hybrid_silence_timeout
                    })

    def _on_key_release(self) -> None:
        """Handle key combo release event (called by KeyboardHandler).

        Behavior depends on configured mode:
        - Hold mode: Checks minimum hold duration, stops recording on release
        - Toggle mode: Ignores release events (toggle on press only)
        """
        if not self._enabled:
            return

        # Toggle mode: ignore release events
        if self._mode == "toggle":
            return

        # Hold mode: handle release with minimum duration check
        current_state = self._state_machine.current_state

        # Calculate hold duration
        hold_duration = 0.0
        if self._key_press_time:
            hold_duration = time.time() - self._key_press_time

        if current_state == PTTState.RECORDING:
            # Stop recording
            self._state_machine.transition(
                PTTState.RECORDING_STOPPED,
                trigger="key_up"
            )

            # Queue recording stop
            self._event_queue.put({
                "type": "stop_recording",
                "timestamp": time.time()
            })

            self._logger.log_event("key_released", {
                "hold_duration_seconds": hold_duration,
                "state": "recording"
            })

        elif current_state == PTTState.KEY_PRESSED:
            # Check if minimum duration was met
            if hold_duration < self._min_duration:
                # Released too quickly - below minimum duration
                self._state_machine.transition(
                    PTTState.IDLE,
                    trigger="quick_release",
                    data={"reason": "below_minimum_duration"}
                )

                self._logger.log_event("quick_release", {
                    "hold_duration_seconds": hold_duration,
                    "min_duration_seconds": self._min_duration,
                    "duration_ms": hold_duration * 1000
                })
            else:
                # Released before recording actually started, but met minimum duration
                # This is a rare edge case - log it
                self._state_machine.transition(
                    PTTState.IDLE,
                    trigger="released_before_recording",
                    data={"reason": "released_before_recording_started"}
                )

                self._logger.log_event("released_before_recording", {
                    "hold_duration_seconds": hold_duration
                })

            # Clear press time
            self._key_press_time = None

    def _cancel_recording(self) -> None:
        """Cancel ongoing recording."""
        if not self.is_recording:
            return

        # Reset toggle mode flag if active
        if self._toggle_active:
            self._toggle_active = False

        self._state_machine.transition(
            PTTState.RECORDING_CANCELLED,
            trigger="cancel"
        )

        # Queue cancel event
        self._event_queue.put({
            "type": "cancel_recording",
            "timestamp": time.time()
        })

    def _on_state_change(
        self,
        from_state: PTTState,
        to_state: PTTState,
        trigger: str
    ) -> None:
        """Handle state machine transitions.

        Args:
            from_state: Previous state
            to_state: New state
            trigger: Event that triggered transition
        """
        self._logger.log_event("state_change_callback", {
            "from": from_state.value,
            "to": to_state.value,
            "trigger": trigger
        })

        # Handle state-specific actions
        if to_state == PTTState.RECORDING:
            self._recording_start_time = time.time()

        elif to_state == PTTState.RECORDING_STOPPED:
            if self._recording_start_time:
                duration = time.time() - self._recording_start_time
                self._logger.log_event("recording_duration", {
                    "duration_seconds": duration
                })
                self._recording_start_time = None

        elif to_state == PTTState.RECORDING_CANCELLED:
            self._recording_start_time = None

    async def wait_for_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Wait for next PTT event from queue.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            Event dictionary or None if timeout

        Example:
            >>> event = await controller.wait_for_event(timeout=1.0)
            >>> if event:
            ...     print(f"Event: {event['type']}")
        """
        loop = asyncio.get_event_loop()

        try:
            # Run queue.get in executor to not block event loop
            event = await asyncio.wait_for(
                loop.run_in_executor(None, self._event_queue.get, True, timeout or 0.1),
                timeout=timeout
            )
            return event
        except (Empty, asyncio.TimeoutError):
            return None

    async def process_events(self) -> None:
        """Process PTT events asynchronously.

        This method runs in a loop, processing events from the queue
        and executing appropriate callbacks.

        Example:
            >>> # In your async code
            >>> task = asyncio.create_task(controller.process_events())
            >>> # Events will be processed automatically
            >>> # ...
            >>> controller.disable()  # Stops event processing
        """
        while not self._stop_event.is_set():
            event = await self.wait_for_event(timeout=0.1)

            if event is None:
                continue

            event_type = event.get("type")

            try:
                if event_type == "start_recording":
                    await self._handle_start_recording(event)

                elif event_type == "stop_recording":
                    await self._handle_stop_recording(event)

                elif event_type == "cancel_recording":
                    await self._handle_cancel_recording(event)

            except Exception as e:
                self._logger.log_error(e, {
                    "event_type": event_type,
                    "event": event
                })

    async def _monitor_hybrid_silence(self) -> None:
        """Monitor for silence in hybrid mode.

        In hybrid mode, automatically stops recording if silence timeout
        is reached, even if user is still holding the key.

        This provides automatic stop on silence while maintaining
        the hold-to-talk physical control.
        """
        try:
            await asyncio.sleep(self._hybrid_silence_timeout)

            # If still recording after silence timeout, stop automatically
            if self.is_recording and self._mode == "hybrid":
                self._logger.log_event("hybrid_silence_detected", {
                    "silence_timeout_seconds": self._hybrid_silence_timeout
                })

                # Transition to RECORDING_STOPPED
                self._state_machine.transition(
                    PTTState.RECORDING_STOPPED,
                    trigger="silence_detected"
                )

                # Queue recording stop
                self._event_queue.put({
                    "type": "stop_recording",
                    "timestamp": time.time()
                })

        except asyncio.CancelledError:
            # Silence task was cancelled (normal flow when recording stops manually)
            pass
        except Exception as e:
            self._logger.log_error(e, {
                "operation": "monitor_hybrid_silence"
            })

    async def _monitor_timeout(self) -> None:
        """Monitor recording timeout and cancel if exceeded.

        This coroutine runs in parallel with recording and cancels
        the recording if it exceeds the configured timeout.
        """
        try:
            await asyncio.sleep(self._timeout)

            # If still recording after timeout, cancel it
            if self.is_recording:
                self._logger.log_event("recording_timeout", {
                    "timeout_seconds": self._timeout,
                    "actual_duration": time.time() - self._recording_start_time if self._recording_start_time else 0
                })

                # Cancel recording
                self._cancel_recording()

        except asyncio.CancelledError:
            # Timeout task was cancelled (normal flow when recording stops)
            pass
        except Exception as e:
            self._logger.log_error(e, {
                "operation": "monitor_timeout"
            })

    async def _recover_from_error(self, operation: str, error: Exception) -> bool:
        """Attempt to recover from recording error.

        Args:
            operation: The operation that failed
            error: The exception that occurred

        Returns:
            True if recovery successful, False otherwise
        """
        if self._retry_count >= self._max_retries:
            self._logger.log_event("recovery_failed", {
                "operation": operation,
                "retry_count": self._retry_count,
                "max_retries": self._max_retries,
                "error": str(error)
            })
            self._retry_count = 0
            return False

        self._retry_count += 1

        self._logger.log_event("attempting_recovery", {
            "operation": operation,
            "retry_attempt": self._retry_count,
            "error": str(error)
        })

        # Wait a bit before retry
        await asyncio.sleep(0.1 * self._retry_count)

        # Try to reset recorder state
        try:
            if self._recorder.is_recording:
                await self._recorder.cancel()
        except Exception as cancel_error:
            self._logger.log_error(cancel_error, {
                "operation": "recovery_cancel"
            })

        return True

    async def _handle_start_recording(self, event: Dict[str, Any]) -> None:
        """Handle start recording event.

        Args:
            event: Event data
        """
        # Check we're in a valid state for starting recording
        # Accept both KEY_PRESSED and RECORDING states (race condition handling)
        current_state = self._state_machine.current_state
        if current_state not in (PTTState.KEY_PRESSED, PTTState.RECORDING):
            return

        # Start recording with error recovery
        retry_attempted = False
        try:
            await self._recorder.start()
        except Exception as e:
            self._logger.log_error(e, {
                "operation": "start_recorder"
            })

            # Attempt recovery
            if await self._recover_from_error("start_recorder", e):
                retry_attempted = True
                try:
                    await self._recorder.start()
                except Exception as retry_error:
                    self._logger.log_error(retry_error, {
                        "operation": "start_recorder_retry"
                    })
                    # Return to IDLE state
                    self._state_machine.transition(
                        PTTState.IDLE,
                        trigger="start_failed"
                    )
                    return
            else:
                # Recovery failed, return to IDLE
                self._state_machine.transition(
                    PTTState.IDLE,
                    trigger="start_failed"
                )
                return

        # Reset retry count on success
        if not retry_attempted:
            self._retry_count = 0

        # Transition to RECORDING
        self._state_machine.transition(
            PTTState.RECORDING,
            trigger="recording_started"
        )

        # Start timeout monitor
        if self._timeout > 0:
            self._timeout_task = asyncio.create_task(self._monitor_timeout())

        # Start hybrid silence monitor
        if self._mode == "hybrid" and self._hybrid_silence_timeout > 0:
            self._hybrid_silence_task = asyncio.create_task(self._monitor_hybrid_silence())

        # Call callback if provided
        if self._on_recording_start:
            try:
                result = self._on_recording_start()
                # If callback returns awaitable, await it
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.log_error(e, {
                    "callback": "on_recording_start"
                })

    async def _handle_stop_recording(self, event: Dict[str, Any]) -> None:
        """Handle stop recording event.

        Args:
            event: Event data
        """
        # Cancel timeout monitor
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

        # Cancel hybrid silence monitor
        if self._hybrid_silence_task and not self._hybrid_silence_task.done():
            self._hybrid_silence_task.cancel()
            try:
                await self._hybrid_silence_task
            except asyncio.CancelledError:
                pass

        # Stop recording and get audio data
        audio_data = None
        try:
            audio_data = await self._recorder.stop()
            # Reset retry count on successful stop
            self._retry_count = 0
        except Exception as e:
            self._logger.log_error(e, {
                "operation": "stop_recorder"
            })

            # Attempt recovery
            if await self._recover_from_error("stop_recorder", e):
                try:
                    audio_data = await self._recorder.stop()
                except Exception as retry_error:
                    self._logger.log_error(retry_error, {
                        "operation": "stop_recorder_retry"
                    })
                    # Continue with None audio data

        # Transition to PROCESSING
        self._state_machine.transition(
            PTTState.PROCESSING,
            trigger="processing_audio"
        )

        # Call callback if provided
        if self._on_recording_stop:
            try:
                result = self._on_recording_stop(audio_data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.log_error(e, {
                    "callback": "on_recording_stop"
                })

        # Return to IDLE first (PROCESSING can only transition to IDLE)
        if self._state_machine.current_state != PTTState.IDLE:
            self._state_machine.transition(
                PTTState.IDLE,
                trigger="complete"
            )

        # If still enabled, transition back to WAITING_FOR_KEY
        if self._enabled:
            self._state_machine.transition(
                PTTState.WAITING_FOR_KEY,
                trigger="ready_for_next"
            )

    async def _handle_cancel_recording(self, event: Dict[str, Any]) -> None:
        """Handle cancel recording event.

        Args:
            event: Event data
        """
        # Cancel timeout monitor
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass

        # Cancel hybrid silence monitor
        if self._hybrid_silence_task and not self._hybrid_silence_task.done():
            self._hybrid_silence_task.cancel()
            try:
                await self._hybrid_silence_task
            except asyncio.CancelledError:
                pass

        # Reset toggle mode flag if active
        if self._toggle_active:
            self._toggle_active = False

        # Cancel recording
        try:
            await self._recorder.cancel()
            # Reset retry count on successful cancel
            self._retry_count = 0
        except Exception as e:
            self._logger.log_error(e, {
                "operation": "cancel_recorder"
            })

            # Attempt recovery for cancel operation
            if await self._recover_from_error("cancel_recorder", e):
                try:
                    await self._recorder.cancel()
                except Exception as retry_error:
                    self._logger.log_error(retry_error, {
                        "operation": "cancel_recorder_retry"
                    })
                    # Continue anyway - best effort

        # Call callback if provided
        if self._on_recording_cancel:
            try:
                result = self._on_recording_cancel()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.log_error(e, {
                    "callback": "on_recording_cancel"
                })

        # Transition to RECORDING_CANCELLED first
        self._state_machine.transition(
            PTTState.RECORDING_CANCELLED,
            trigger="cancelled"
        )

        # Then transition to IDLE (RECORDING_CANCELLED can only transition to IDLE)
        if self._state_machine.current_state != PTTState.IDLE:
            self._state_machine.transition(
                PTTState.IDLE,
                trigger="complete"
            )

        # If still enabled, transition back to WAITING_FOR_KEY
        if self._enabled:
            self._state_machine.transition(
                PTTState.WAITING_FOR_KEY,
                trigger="ready_after_cancel"
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current PTT controller status.

        Returns:
            Dictionary containing:
                - enabled: Whether PTT is enabled
                - state: Current state name
                - is_recording: Whether currently recording
                - key_combo: Configured key combination
                - cancel_key: Configured cancel key
                - timeout: Configured timeout
                - mode: PTT mode (hold/toggle/hybrid)
                - toggle_active: Toggle mode flag

        Example:
            >>> status = controller.get_status()
            >>> print(f"PTT enabled: {status['enabled']}")
            >>> print(f"Current state: {status['state']}")
        """
        return {
            "enabled": self._enabled,
            "state": self.current_state_name,
            "is_recording": self.is_recording,
            "key_combo": self._key_combo,
            "cancel_key": self._cancel_key,
            "timeout": self._timeout,
            "mode": self._mode,
            "toggle_active": self._toggle_active,
            "state_machine": self._state_machine.get_state_summary()
        }

    def __enter__(self):
        """Context manager entry."""
        self.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disable()
        return False


def create_ptt_controller(
    key_combo: Optional[str] = None,
    on_recording_start: Optional[Callable[[], Any]] = None,
    on_recording_stop: Optional[Callable[[Any], None]] = None,
    logger: Optional[PTTLogger] = None
) -> PTTController:
    """Factory function to create PTT controller.

    Args:
        key_combo: Key combination for PTT
        on_recording_start: Recording start callback
        on_recording_stop: Recording stop callback
        logger: PTTLogger instance

    Returns:
        Configured PTTController instance

    Example:
        >>> controller = create_ptt_controller(
        ...     key_combo="space",
        ...     on_recording_start=lambda: print("Recording!")
        ... )
    """
    return PTTController(
        key_combo=key_combo,
        on_recording_start=on_recording_start,
        on_recording_stop=on_recording_stop,
        logger=logger
    )
