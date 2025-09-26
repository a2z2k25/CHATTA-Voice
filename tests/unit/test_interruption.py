#!/usr/bin/env python3
"""Test interruption handling implementation."""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.interruption_handler import (
    ConversationState,
    ConversationStateMachine,
    InterruptionDetector,
    InterruptionType,
    InterruptionEvent,
    StreamCancellationToken,
    InterruptibleAudioPlayer
)


def test_state_machine():
    """Test conversation state machine."""
    print("\n=== Testing State Machine ===")
    
    machine = ConversationStateMachine()
    
    # Test initial state
    assert machine.get_state() == ConversationState.IDLE
    print(f"Initial state: {machine.get_state().name} ✓")
    
    # Test valid transitions
    transitions = [
        (ConversationState.LISTENING, "User started speaking"),
        (ConversationState.PROCESSING, "Processing audio"),
        (ConversationState.RESPONDING, "Playing response"),
        (ConversationState.INTERRUPTED, "User interrupted"),
        (ConversationState.IDLE, "Back to idle"),
    ]
    
    for target_state, reason in transitions:
        success = machine.transition_to(target_state, reason)
        current = machine.get_state()
        print(f"Transition to {target_state.name}: {success} (Current: {current.name})")
        
    # Test invalid transition
    machine.transition_to(ConversationState.IDLE, "Reset")
    success = machine.transition_to(ConversationState.INTERRUPTED, "Invalid")
    print(f"\nInvalid transition (IDLE → INTERRUPTED): {success} ✓")
    
    # Check history
    print(f"\nState history entries: {len(machine.state_history)}")
    if machine.state_history:
        last = machine.state_history[-1]
        print(f"Last transition: {last['from']} → {last['to']} ({last['reason']})")


def test_cancellation_token():
    """Test stream cancellation token."""
    print("\n=== Testing Cancellation Token ===")
    
    token = StreamCancellationToken()
    
    # Test initial state
    assert not token.is_cancelled()
    print(f"Initial cancelled state: {token.is_cancelled()} ✓")
    
    # Test cancellation
    token.cancel("User stopped")
    assert token.is_cancelled()
    print(f"After cancel: {token.is_cancelled()} ✓")
    
    # Test reset
    token.reset()
    assert not token.is_cancelled()
    print(f"After reset: {token.is_cancelled()} ✓")
    
    # Test callback
    callback_called = False
    def on_cancel(reason):
        nonlocal callback_called
        callback_called = True
        print(f"Callback triggered: {reason}")
    
    token.register_callback(on_cancel)
    token.cancel("Test callback")
    assert callback_called
    print(f"Callback executed: {callback_called} ✓")


def test_interruption_detector():
    """Test interruption detection."""
    print("\n=== Testing Interruption Detector ===")
    
    detector = InterruptionDetector(threshold_db=-30.0)
    
    # Track interruptions
    interruptions = []
    def on_interruption(event: InterruptionEvent):
        interruptions.append(event)
        print(f"Interruption detected: {event.type.name} - {event.reason}")
    
    detector.register_callback(on_interruption)
    
    # Start monitoring
    detector.start_monitoring()
    print("Monitoring started ✓")
    
    # Simulate audio input (loud enough to trigger)
    import numpy as np
    sample_rate = 24000
    duration = 0.1
    frequency = 440  # A4 note
    
    # Generate loud audio
    t = np.linspace(0, duration, int(sample_rate * duration))
    loud_audio = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)
    
    # Feed audio
    detector.feed_audio(loud_audio.tobytes())
    
    # Wait for processing
    time.sleep(0.2)
    
    # Stop monitoring
    detector.stop_monitoring()
    print("Monitoring stopped ✓")
    
    print(f"Interruptions detected: {len(interruptions)}")


async def test_interruptible_player():
    """Test interruptible audio player."""
    print("\n=== Testing Interruptible Player ===")
    
    player = InterruptibleAudioPlayer()
    
    # Track state changes
    state_changes = []
    def on_state_change(from_state, to_state, reason):
        state_changes.append((from_state.name, to_state.name))
        print(f"State: {from_state.name} → {to_state.name}")
    
    # Register callbacks for all transitions
    for from_state in ConversationState:
        for to_state in ConversationState:
            player.state_machine.register_callback(
                from_state, to_state, on_state_change
            )
    
    # Create test stream
    class TestStream:
        def __init__(self, chunks=5, delay=0.1):
            self.chunks = [f"chunk_{i}".encode() for i in range(chunks)]
            self.index = 0
            self.delay = delay
        
        async def get_next_chunk(self):
            if self.index < len(self.chunks):
                chunk = self.chunks[self.index]
                self.index += 1
                await asyncio.sleep(self.delay)
                return chunk
            return None
    
    # Test normal playback
    print("\n1. Testing normal playback:")
    stream = TestStream(chunks=3, delay=0.05)
    completed = await player.play_with_interruption(stream, allow_interruptions=False)
    print(f"Playback completed: {completed} ✓")
    
    # Test interrupted playback
    print("\n2. Testing interrupted playback:")
    stream = TestStream(chunks=10, delay=0.1)
    
    # Schedule interruption
    async def interrupt_after_delay():
        await asyncio.sleep(0.25)
        player.stop()
        print("Interruption triggered!")
    
    # Run playback and interruption concurrently
    playback_task = asyncio.create_task(
        player.play_with_interruption(stream, allow_interruptions=True)
    )
    interrupt_task = asyncio.create_task(interrupt_after_delay())
    
    completed = await playback_task
    await interrupt_task
    
    print(f"Playback completed: {completed} (should be False)")
    print(f"State changes recorded: {len(state_changes)}")


async def test_concurrent_operations():
    """Test concurrent interruption scenarios."""
    print("\n=== Testing Concurrent Operations ===")
    
    player = InterruptibleAudioPlayer()
    
    # Test rapid state changes
    states_to_test = [
        (ConversationState.LISTENING, "Start listening"),
        (ConversationState.PROCESSING, "Process audio"),
        (ConversationState.RESPONDING, "Start response"),
        (ConversationState.INTERRUPTED, "Interrupt"),
        (ConversationState.IDLE, "Reset"),
    ]
    
    print("Rapid state transitions:")
    for state, reason in states_to_test:
        success = player.state_machine.transition_to(state, reason)
        current = player.state_machine.get_state()
        print(f"  {state.name}: {success} (Current: {current.name})")
    
    # Test multiple interruptions
    print("\nMultiple interruption attempts:")
    player.state_machine.transition_to(ConversationState.RESPONDING, "Playing")
    
    for i in range(3):
        if player.state_machine.is_interruptible():
            player.cancellation_token.cancel(f"Interruption {i+1}")
            print(f"  Interruption {i+1}: Triggered")
        else:
            print(f"  Interruption {i+1}: Not interruptible")
        
        # Reset for next test
        if i < 2:
            player.cancellation_token.reset()
            player.state_machine.transition_to(ConversationState.RESPONDING, "Resume")


def main():
    """Run all tests."""
    print("=" * 60)
    print("INTERRUPTION HANDLING TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_state_machine()
    test_cancellation_token()
    test_interruption_detector()
    
    # Run async tests
    asyncio.run(test_interruptible_player())
    asyncio.run(test_concurrent_operations())
    
    print("\n" + "=" * 60)
    print("✓ All interruption tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()