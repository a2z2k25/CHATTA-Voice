"""
Interruption handling for voice conversations.

This module provides mechanisms to detect and handle interruptions
during TTS playback, enabling more natural conversation flow.
"""

import asyncio
import threading
import time
import logging
from enum import Enum, auto
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
import queue

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """States for conversation flow."""
    IDLE = auto()                    # Waiting for input
    LISTENING = auto()                # Recording user speech
    PROCESSING = auto()               # Processing STT
    RESPONDING = auto()               # Playing TTS response
    INTERRUPTED = auto()              # Response interrupted
    CANCELLING = auto()               # Cancelling current operation


class InterruptionType(Enum):
    """Types of interruptions."""
    USER_SPEECH = auto()              # User started speaking
    USER_COMMAND = auto()             # User issued command (e.g., stop)
    SYSTEM_CANCEL = auto()            # System-initiated cancel
    TIMEOUT = auto()                  # Operation timed out
    ERROR = auto()                    # Error occurred


@dataclass
class InterruptionEvent:
    """Event data for interruptions."""
    type: InterruptionType
    timestamp: float = field(default_factory=time.perf_counter)
    reason: Optional[str] = None
    data: Optional[Any] = None


class ConversationStateMachine:
    """Manages conversation state transitions."""
    
    def __init__(self):
        """Initialize state machine."""
        self.state = ConversationState.IDLE
        self.previous_state = ConversationState.IDLE
        self.state_lock = threading.Lock()
        self.transition_callbacks = {}
        self.state_history = []
        self.max_history = 100
        
    def register_callback(
        self,
        from_state: ConversationState,
        to_state: ConversationState,
        callback: Callable
    ):
        """Register callback for state transition.
        
        Args:
            from_state: Source state
            to_state: Target state
            callback: Function to call on transition
        """
        key = (from_state, to_state)
        if key not in self.transition_callbacks:
            self.transition_callbacks[key] = []
        self.transition_callbacks[key].append(callback)
    
    def transition_to(self, new_state: ConversationState, reason: str = "") -> bool:
        """Transition to new state.
        
        Args:
            new_state: Target state
            reason: Reason for transition
            
        Returns:
            True if transition successful
        """
        with self.state_lock:
            # Check if transition is valid
            if not self._is_valid_transition(self.state, new_state):
                logger.warning(
                    f"Invalid transition: {self.state.name} -> {new_state.name}"
                )
                return False
            
            old_state = self.state
            self.previous_state = old_state
            self.state = new_state
            
            # Record in history
            self.state_history.append({
                'from': old_state.name,
                'to': new_state.name,
                'timestamp': time.perf_counter(),
                'reason': reason
            })
            
            # Trim history
            if len(self.state_history) > self.max_history:
                self.state_history = self.state_history[-self.max_history:]
            
            logger.info(f"State transition: {old_state.name} -> {new_state.name} ({reason})")
            
            # Execute callbacks
            key = (old_state, new_state)
            if key in self.transition_callbacks:
                for callback in self.transition_callbacks[key]:
                    try:
                        callback(old_state, new_state, reason)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            
            return True
    
    def _is_valid_transition(
        self,
        from_state: ConversationState,
        to_state: ConversationState
    ) -> bool:
        """Check if state transition is valid.
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            ConversationState.IDLE: [
                ConversationState.LISTENING,
                ConversationState.PROCESSING
            ],
            ConversationState.LISTENING: [
                ConversationState.PROCESSING,
                ConversationState.IDLE,
                ConversationState.INTERRUPTED
            ],
            ConversationState.PROCESSING: [
                ConversationState.RESPONDING,
                ConversationState.IDLE,
                ConversationState.INTERRUPTED
            ],
            ConversationState.RESPONDING: [
                ConversationState.IDLE,
                ConversationState.INTERRUPTED,
                ConversationState.CANCELLING
            ],
            ConversationState.INTERRUPTED: [
                ConversationState.LISTENING,
                ConversationState.IDLE,
                ConversationState.CANCELLING
            ],
            ConversationState.CANCELLING: [
                ConversationState.IDLE
            ]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def get_state(self) -> ConversationState:
        """Get current state."""
        with self.state_lock:
            return self.state
    
    def is_interruptible(self) -> bool:
        """Check if current state can be interrupted."""
        with self.state_lock:
            return self.state in [
                ConversationState.RESPONDING,
                ConversationState.PROCESSING
            ]


class InterruptionDetector:
    """Detects interruptions during conversation."""
    
    def __init__(self, threshold_db: float = -30.0):
        """Initialize interruption detector.
        
        Args:
            threshold_db: Audio level threshold for detection (dB)
        """
        self.threshold_db = threshold_db
        self.is_monitoring = False
        self.monitor_thread = None
        self.audio_queue = queue.Queue()
        self.callbacks = []
        self.detection_window_ms = 100  # Time window for detection
        
    def register_callback(self, callback: Callable[[InterruptionEvent], None]):
        """Register interruption callback.
        
        Args:
            callback: Function to call on interruption
        """
        self.callbacks.append(callback)
    
    def start_monitoring(self):
        """Start monitoring for interruptions."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.debug("Started interruption monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring for interruptions."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.debug("Stopped interruption monitoring")
    
    def feed_audio(self, audio_data: bytes):
        """Feed audio data for interruption detection.
        
        Args:
            audio_data: Audio bytes to analyze
        """
        if self.is_monitoring:
            try:
                self.audio_queue.put_nowait(audio_data)
            except queue.Full:
                # Drop oldest data if queue full
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(audio_data)
                except queue.Empty:
                    pass
    
    def _monitor_loop(self):
        """Monitor loop for interruption detection."""
        import numpy as np
        
        while self.is_monitoring:
            try:
                # Get audio data with timeout
                audio_data = self.audio_queue.get(timeout=0.1)
                
                # Convert to numpy array (assume 16-bit PCM)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Calculate RMS level
                if len(audio_array) > 0:
                    rms = np.sqrt(np.mean(audio_array.astype(float) ** 2))
                    
                    # Convert to dB
                    if rms > 0:
                        db = 20 * np.log10(rms / 32768.0)  # 16-bit max
                        
                        # Check threshold
                        if db > self.threshold_db:
                            self._trigger_interruption(
                                InterruptionType.USER_SPEECH,
                                f"Audio level: {db:.1f}dB"
                            )
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
    
    def _trigger_interruption(self, type: InterruptionType, reason: str):
        """Trigger interruption event.
        
        Args:
            type: Type of interruption
            reason: Reason for interruption
        """
        event = InterruptionEvent(type=type, reason=reason)
        logger.info(f"Interruption detected: {type.name} - {reason}")
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")


class StreamCancellationToken:
    """Token for cancelling audio streams."""
    
    def __init__(self):
        """Initialize cancellation token."""
        self._cancelled = False
        self._lock = threading.Lock()
        self._callbacks = []
        
    def cancel(self, reason: str = ""):
        """Cancel the operation.
        
        Args:
            reason: Reason for cancellation
        """
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                logger.info(f"Stream cancelled: {reason}")
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(reason)
                    except Exception as e:
                        logger.error(f"Cancellation callback error: {e}")
    
    def is_cancelled(self) -> bool:
        """Check if cancelled."""
        with self._lock:
            return self._cancelled
    
    def register_callback(self, callback: Callable[[str], None]):
        """Register cancellation callback.
        
        Args:
            callback: Function to call on cancellation
        """
        self._callbacks.append(callback)
    
    def reset(self):
        """Reset cancellation state."""
        with self._lock:
            self._cancelled = False


class InterruptibleAudioPlayer:
    """Audio player with interruption support."""
    
    def __init__(self):
        """Initialize interruptible player."""
        self.cancellation_token = StreamCancellationToken()
        self.state_machine = ConversationStateMachine()
        self.detector = InterruptionDetector()
        self.current_stream = None
        self.playback_lock = asyncio.Lock()
        
        # Register interruption handler
        self.detector.register_callback(self._handle_interruption)
        
    async def play_with_interruption(
        self,
        audio_stream,
        allow_interruptions: bool = True
    ) -> bool:
        """Play audio with interruption support.
        
        Args:
            audio_stream: Audio stream to play
            allow_interruptions: Whether to allow interruptions
            
        Returns:
            True if completed, False if interrupted
        """
        async with self.playback_lock:
            # Reset cancellation token
            self.cancellation_token.reset()
            
            # Start monitoring if interruptions allowed
            if allow_interruptions:
                self.detector.start_monitoring()
            
            # Transition to responding state
            self.state_machine.transition_to(
                ConversationState.RESPONDING,
                "Starting TTS playback"
            )
            
            try:
                # Play audio with cancellation check
                self.current_stream = audio_stream
                
                while not self.cancellation_token.is_cancelled():
                    # Get next chunk
                    chunk = await audio_stream.get_next_chunk()
                    if chunk is None:
                        break
                    
                    # Play chunk (simplified)
                    await self._play_chunk(chunk)
                    
                    # Check for interruption
                    if self.cancellation_token.is_cancelled():
                        logger.info("Playback interrupted")
                        return False
                
                # Completed successfully
                self.state_machine.transition_to(
                    ConversationState.IDLE,
                    "Playback completed"
                )
                return True
                
            finally:
                # Stop monitoring
                if allow_interruptions:
                    self.detector.stop_monitoring()
                
                self.current_stream = None
    
    async def _play_chunk(self, chunk: bytes):
        """Play audio chunk (simplified).
        
        Args:
            chunk: Audio data to play
        """
        # This would interface with actual audio output
        # For now, just simulate playback time
        await asyncio.sleep(0.01)
    
    def _handle_interruption(self, event: InterruptionEvent):
        """Handle interruption event.
        
        Args:
            event: Interruption event
        """
        if self.state_machine.is_interruptible():
            # Cancel current playback
            self.cancellation_token.cancel(event.reason)
            
            # Transition to interrupted state
            self.state_machine.transition_to(
                ConversationState.INTERRUPTED,
                f"Interrupted: {event.type.name}"
            )
    
    def stop(self):
        """Stop playback immediately."""
        self.cancellation_token.cancel("User stop command")
        self.state_machine.transition_to(
            ConversationState.CANCELLING,
            "Stopping playback"
        )


# Example usage pattern
async def example_usage():
    """Example of using interruption handling."""
    
    # Create interruptible player
    player = InterruptibleAudioPlayer()
    
    # Register state change callback
    def on_state_change(from_state, to_state, reason):
        print(f"State changed: {from_state.name} -> {to_state.name}")
    
    player.state_machine.register_callback(
        ConversationState.RESPONDING,
        ConversationState.INTERRUPTED,
        on_state_change
    )
    
    # Simulate audio stream
    class DummyStream:
        def __init__(self):
            self.chunks = [b"chunk1", b"chunk2", b"chunk3"]
            self.index = 0
        
        async def get_next_chunk(self):
            if self.index < len(self.chunks):
                chunk = self.chunks[self.index]
                self.index += 1
                await asyncio.sleep(0.5)  # Simulate streaming delay
                return chunk
            return None
    
    # Play with interruption support
    stream = DummyStream()
    completed = await player.play_with_interruption(stream, allow_interruptions=True)
    
    if completed:
        print("Playback completed successfully")
    else:
        print("Playback was interrupted")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())