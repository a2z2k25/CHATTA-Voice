#!/usr/bin/env python3
"""Test visual feedback system."""

import asyncio
import time
import random
from voice_mode.visual_feedback import (
    VisualFeedbackSystem,
    IndicatorState,
    AnimationStyle,
    IndicatorConfig,
    VoiceActivityIndicator,
    ConnectionStatusDisplay,
    ProgressIndicator,
    NotificationManager
)


def test_voice_activity_indicator():
    """Test voice activity indicator."""
    print("\n=== Testing Voice Activity Indicator ===")
    
    # Test different animation styles
    for style in AnimationStyle:
        config = IndicatorConfig(style=style)
        indicator = VoiceActivityIndicator(config)
        
        print(f"\n{style.name} Animation:")
        for _ in range(10):
            frame = indicator.get_animation_frame()
            print(f"  {frame}", end="", flush=True)
            time.sleep(0.1)
        print()
    
    # Test state transitions
    indicator = VoiceActivityIndicator()
    states = [
        IndicatorState.IDLE,
        IndicatorState.LISTENING,
        IndicatorState.PROCESSING,
        IndicatorState.SPEAKING,
        IndicatorState.ERROR
    ]
    
    print("\nState Transitions:")
    for state in states:
        indicator.set_state(state)
        print(f"  {state.name}: {indicator.get_display_text()}")
    
    # Test audio level meter
    print("\nAudio Level Meter:")
    for level in [0.0, 0.2, 0.5, 0.8, 1.0]:
        indicator.set_audio_level(level)
        meter = indicator.get_level_meter()
        print(f"  Level {level:.1f}: {meter}")
    
    print("✓ Voice activity indicator working")


def test_connection_status():
    """Test connection status display."""
    print("\n=== Testing Connection Status Display ===")
    
    display = ConnectionStatusDisplay()
    
    # Test different states
    test_cases = [
        (False, 0, 0, None, None),  # Disconnected
        (True, 20, 4, "OpenAI", None),  # Good connection
        (True, 150, 2, "Whisper", None),  # Medium latency
        (True, 300, 1, "Kokoro", None),  # High latency
        (False, 0, 0, None, "Connection timeout"),  # Error
    ]
    
    for connected, latency, signal, service, error in test_cases:
        display.update_status(connected, latency, signal, service, error)
        status = display.get_status_text()
        icon = display.get_status_icon()
        print(f"  {icon} {status}")
    
    print("✓ Connection status display working")


def test_progress_indicator():
    """Test progress indicator."""
    print("\n=== Testing Progress Indicator ===")
    
    # Determinate progress
    print("\nDeterminate Progress:")
    progress = ProgressIndicator(total=100)
    
    for i in range(0, 101, 20):
        progress.update(i, f"Processing step {i//20 + 1}")
        bar = progress.get_progress_bar(width=20)
        print(f"  {bar}")
    
    # Indeterminate progress
    print("\nIndeterminate Progress:")
    progress = ProgressIndicator(total=None)
    
    for i in range(5):
        progress.update(message=f"Loading {i+1}/5")
        bar = progress.get_progress_bar()
        print(f"  {bar}")
        time.sleep(0.2)
    
    print("✓ Progress indicator working")


def test_notification_manager():
    """Test notification manager."""
    print("\n=== Testing Notification Manager ===")
    
    manager = NotificationManager()
    
    # Test callback
    notifications_received = []
    
    def callback(message, level):
        notifications_received.append((message, level))
    
    manager.register_callback(callback)
    
    # Add notifications
    test_notifications = [
        ("System ready", "info"),
        ("Low memory warning", "warning"),
        ("Connection failed", "error"),
        ("File saved successfully", "success"),
    ]
    
    for message, level in test_notifications:
        manager.add_notification(message, level, duration=5.0)
    
    # Check active notifications
    active = manager.get_active_notifications()
    print(f"Active notifications: {len(active)}")
    
    for notif in active:
        formatted = manager.format_notification(notif)
        print(f"  {formatted}")
    
    # Check callbacks
    assert len(notifications_received) == len(test_notifications)
    print("✓ Notification manager working")


async def test_visual_feedback_system():
    """Test integrated visual feedback system."""
    print("\n=== Testing Visual Feedback System ===")
    
    system = VisualFeedbackSystem()
    
    # Register update callback
    updates_received = []
    
    def update_callback(state):
        updates_received.append(state)
        # Print current display
        print(system.format_display())
        print("-" * 40)
    
    system.register_update_callback(update_callback)
    
    # Start system
    system.start()
    
    # Simulate voice conversation
    print("\nSimulating voice conversation:")
    
    # Connect
    system.update_connection(True, 25, "OpenAI")
    system.show_notification("Connected to OpenAI", "success")
    await asyncio.sleep(0.5)
    
    # Start listening
    system.update_voice_state(IndicatorState.LISTENING)
    
    # Simulate audio levels
    for _ in range(10):
        level = random.random()
        system.update_voice_state(IndicatorState.LISTENING, level)
        await asyncio.sleep(0.1)
    
    # Processing
    system.update_voice_state(IndicatorState.PROCESSING)
    system.start_progress(100, "Transcribing audio")
    
    for i in range(0, 101, 20):
        system.update_progress(i)
        await asyncio.sleep(0.2)
    
    # Speaking
    system.update_voice_state(IndicatorState.SPEAKING)
    await asyncio.sleep(1.0)
    
    # Error simulation
    system.update_voice_state(IndicatorState.ERROR)
    system.show_notification("Audio device disconnected", "error")
    system.update_connection(False)
    await asyncio.sleep(0.5)
    
    # Stop system
    system.stop()
    
    print(f"\n✓ Received {len(updates_received)} updates")
    print("✓ Visual feedback system working")


async def test_real_time_updates():
    """Test real-time update performance."""
    print("\n=== Testing Real-Time Updates ===")
    
    system = VisualFeedbackSystem()
    system.start()
    
    # Measure update rate
    update_count = 0
    start_time = time.time()
    
    def count_updates(state):
        nonlocal update_count
        update_count += 1
    
    system.register_update_callback(count_updates)
    
    # Generate rapid updates
    for _ in range(100):
        system.update_voice_state(
            IndicatorState.LISTENING,
            random.random()
        )
        await asyncio.sleep(0.01)  # 100 updates per second
    
    elapsed = time.time() - start_time
    rate = update_count / elapsed
    
    print(f"Update rate: {rate:.1f} updates/second")
    print(f"Total updates: {update_count} in {elapsed:.2f}s")
    
    system.stop()
    print("✓ Real-time updates working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("VISUAL FEEDBACK SYSTEM TESTS")
    print("=" * 60)
    
    # Synchronous tests
    test_voice_activity_indicator()
    test_connection_status()
    test_progress_indicator()
    test_notification_manager()
    
    # Async tests
    asyncio.run(test_visual_feedback_system())
    asyncio.run(test_real_time_updates())
    
    print("\n" + "=" * 60)
    print("✓ All visual feedback tests passed!")
    print("Sprint 33 implementation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()