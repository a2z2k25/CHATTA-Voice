#!/usr/bin/env python3
"""Test TTS streaming and adaptive buffer implementation."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.adaptive_streaming import (
    AdaptiveStreamBuffer,
    PlaybackRateController,
    estimate_speech_duration,
    calculate_optimal_chunk_size
)


def test_duration_estimation():
    """Test speech duration estimation."""
    print("\n=== Testing Duration Estimation ===")
    
    test_cases = [
        ("Hello world", "nova", 0.7),
        ("This is a longer sentence with multiple words.", "nova", 2.8),
        ("Quick test.", "echo", 0.8),
        ("The quick brown fox jumps over the lazy dog. This is a classic pangram.", "alloy", 4.5),
    ]
    
    for text, voice, expected in test_cases:
        estimated = estimate_speech_duration(text, voice)
        print(f"Text: '{text[:30]}...' ({len(text.split())} words)")
        print(f"Voice: {voice}")
        print(f"Estimated: {estimated:.2f}s, Expected: ~{expected:.1f}s")
        print(f"Difference: {abs(estimated - expected):.2f}s\n")


def test_adaptive_buffer():
    """Test adaptive buffer logic."""
    print("\n=== Testing Adaptive Buffer ===")
    
    # Create buffer with 35% target
    buffer = AdaptiveStreamBuffer(target_percentage=0.35, min_buffer_ms=500)
    buffer.total_expected_duration = 10.0  # Expect 10 second audio
    
    print(f"Expected duration: {buffer.total_expected_duration}s")
    print(f"Target percentage: {buffer.target_percentage * 100}%")
    print(f"Min buffer: {buffer.min_buffer_seconds}s\n")
    
    # Simulate adding chunks
    chunk_duration = 0.5  # 500ms chunks
    for i in range(8):
        buffer.add_chunk(b"dummy_audio_data", chunk_duration)
        percentage = buffer.get_buffered_percentage()
        should_start = buffer.should_start_playback()
        
        print(f"Chunk {i+1}: Buffered {buffer.buffered_duration:.1f}s ({percentage:.1%})")
        
        if should_start and not buffer.playback_started:
            buffer.start_playback()
            print(f"  ✓ PLAYBACK STARTED at {percentage:.1%}")
            print(f"  TTFA: {buffer.metrics.ttfa:.3f}s")
        elif should_start:
            print(f"  (Already playing)")
        else:
            print(f"  Waiting... (need {buffer.target_percentage * 100:.0f}%)")


def test_playback_rate_control():
    """Test playback rate controller."""
    print("\n=== Testing Playback Rate Control ===")
    
    controller = PlaybackRateController(base_rate=1.0)
    
    # Test different buffer health scenarios
    scenarios = [
        (0.1, "Critical - Buffer almost empty"),
        (0.3, "Low - Buffer getting low"),
        (0.5, "Normal - Buffer adequate"),
        (0.7, "Good - Buffer healthy"),
        (0.9, "Excellent - Buffer very full"),
    ]
    
    for health, description in scenarios:
        rate = controller.calculate_rate(health)
        print(f"Buffer health: {health:.1%} - {description}")
        print(f"Playback rate: {rate:.3f}x ({(rate - 1.0) * 100:+.1f}% adjustment)\n")


def test_chunk_size_optimization():
    """Test chunk size calculation."""
    print("\n=== Testing Chunk Size Optimization ===")
    
    test_cases = [
        (50, None, "Very short text"),
        (250, 30, "Medium text, excellent network"),
        (500, 150, "Long text, fair network"),
        (1500, 250, "Very long text, poor network"),
    ]
    
    for text_len, latency, description in test_cases:
        chunk_size = calculate_optimal_chunk_size(text_len, latency)
        print(f"{description}:")
        print(f"  Text length: {text_len} chars")
        print(f"  Network latency: {latency}ms" if latency else "  Network: Unknown")
        print(f"  Optimal chunk: {chunk_size} bytes\n")


async def test_buffer_simulation():
    """Simulate realistic buffering scenario."""
    print("\n=== Simulating Realistic Buffering ===")
    
    text = "This is a test of the emergency broadcast system. This is only a test. If this had been an actual emergency, you would have been instructed where to tune in your area for news and official information."
    
    # Estimate duration
    duration = estimate_speech_duration(text, "nova")
    print(f"Text: {len(text)} chars, {len(text.split())} words")
    print(f"Estimated duration: {duration:.2f}s\n")
    
    # Create adaptive buffer
    buffer = AdaptiveStreamBuffer(target_percentage=0.35)
    buffer.total_expected_duration = duration
    
    # Simulate streaming chunks
    chunk_count = 20
    chunk_duration = duration / chunk_count
    
    print("Simulating streaming:")
    for i in range(chunk_count):
        # Simulate network delay
        await asyncio.sleep(0.05)
        
        # Add chunk
        buffer.add_chunk(b"audio_chunk", chunk_duration)
        
        # Check if should start
        if buffer.should_start_playback() and not buffer.playback_started:
            buffer.start_playback()
            print(f"✓ Started playback at chunk {i+1}/{chunk_count}")
            print(f"  Buffered: {buffer.buffered_duration:.2f}s ({buffer.get_buffered_percentage():.1%})")
            print(f"  TTFA: {buffer.metrics.ttfa:.3f}s")
            break
    
    print(f"\nFinal metrics:")
    print(f"  Chunks buffered before start: {buffer.metrics.chunks_buffered_before_start}")
    print(f"  Early start percentage: {buffer.metrics.early_start_percentage:.1%}")
    print(f"  Target was: {buffer.target_percentage:.1%}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TTS STREAMING TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_duration_estimation()
    test_adaptive_buffer()
    test_playback_rate_control()
    test_chunk_size_optimization()
    
    # Run async simulation
    asyncio.run(test_buffer_simulation())
    
    print("\n" + "=" * 60)
    print("✓ All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()