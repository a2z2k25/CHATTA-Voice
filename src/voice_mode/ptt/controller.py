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

        # Components
        self._logger = logger or get_ptt_logger()
        self._state_machine = PTTStateMachine(
            logger=self._logger,
            on_state_change=self._on_state_change
        )
        self._keyboard: Optional[KeyboardHandler] = None

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
        """Handle key combo press event (called by KeyboardHandler)."""
        if not self._enabled:
            return

        current_state = self._state_machine.current_state

        if current_state == PTTState.WAITING_FOR_KEY:
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

    def _on_key_release(self) -> None:
        """Handle key combo release event (called by KeyboardHandler)."""
        if not self._enabled:
            return

        current_state = self._state_machine.current_state

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

        elif current_state == PTTState.KEY_PRESSED:
            # Released too quickly - cancel
            self._state_machine.transition(
                PTTState.IDLE,
                trigger="quick_release",
                data={"reason": "released_before_recording_started"}
            )

            self._logger.log_event("quick_release", {
                "duration_ms": self._state_machine.time_in_current_state * 1000
            })

    def _cancel_recording(self) -> None:
        """Cancel ongoing recording."""
        if not self.is_recording:
            return

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

    async def _handle_start_recording(self, event: Dict[str, Any]) -> None:
        """Handle start recording event.

        Args:
            event: Event data
        """
        # Check minimum duration hasn't elapsed yet
        if self._state_machine.current_state != PTTState.KEY_PRESSED:
            return

        # Transition to RECORDING
        self._state_machine.transition(
            PTTState.RECORDING,
            trigger="recording_started"
        )

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
        # Transition to PROCESSING
        self._state_machine.transition(
            PTTState.PROCESSING,
            trigger="processing_audio"
        )

        # Call callback if provided
        if self._on_recording_stop:
            try:
                # In real implementation, audio_data would come from recorder
                audio_data = None  # Placeholder
                result = self._on_recording_stop(audio_data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._logger.log_error(e, {
                    "callback": "on_recording_stop"
                })

        # Return to IDLE first (PROCESSING can only transition to IDLE)
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

        # Return to IDLE first (RECORDING_CANCELLED can only transition to IDLE)
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
                - timeout: Configured timeout

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
