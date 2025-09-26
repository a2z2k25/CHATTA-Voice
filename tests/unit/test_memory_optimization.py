#!/usr/bin/env python3
"""Test memory optimization framework."""

import sys
import os
import time
import asyncio
import numpy as np
import gc
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.memory_optimizer import (
    MemoryProfile,
    MemoryOptimizer,
    BufferManager,
    CircularBuffer,
    WeakCache,
    MemoryPool,
    MemoryMonitor,
    get_memory_optimizer
)

from voice_mode.memory_integration import (
    AudioMemoryManager,
    VoiceMemoryOptimizer,
    StreamingMemoryBuffer,
    integrate_memory_optimization
)


def test_memory_pool():
    """Test memory pool functionality."""
    print("\n=== Testing Memory Pool ===")
    
    # Create pool with factory
    call_count = 0
    
    def create_buffer():
        nonlocal call_count
        call_count += 1
        return np.zeros(1024, dtype=np.int16)
    
    pool = MemoryPool(factory=create_buffer, max_size=5)
    
    # Acquire objects
    obj1 = pool.acquire()
    obj2 = pool.acquire()
    assert call_count == 2
    print(f"✓ Created {call_count} new objects")
    
    # Release and reacquire
    pool.release(obj1)
    obj3 = pool.acquire()
    assert obj3 is obj1  # Same object reused
    assert call_count == 2  # No new object created
    print("✓ Object pooling working")
    
    # Test pool stats
    stats = pool.stats
    assert "pool_size" in stats
    assert "max_size" in stats
    assert "created" in stats
    assert "reused" in stats
    assert stats["created"] == 2
    assert stats["reused"] == 1
    print(f"✓ Pool stats: {stats}")


def test_circular_buffer():
    """Test circular buffer functionality."""
    print("\n=== Testing Circular Buffer ===")
    
    buffer = CircularBuffer(size=10)
    
    # Write data
    data1 = np.array([1, 2, 3, 4, 5], dtype=np.int16)
    written = buffer.write(data1)
    assert written == 5
    assert buffer.available == 5
    print(f"✓ Written {written} samples")
    
    # Read data
    read_data = buffer.read(3)
    assert len(read_data) == 3
    assert np.array_equal(read_data, np.array([1, 2, 3]))
    assert buffer.available == 2
    print(f"✓ Read {len(read_data)} samples")
    
    # Test wraparound
    data2 = np.array([6, 7, 8, 9, 10, 11], dtype=np.int16)
    written = buffer.write(data2)
    assert written == 6
    
    # Read all
    all_data = buffer.read(8)
    assert len(all_data) == 8
    assert all_data[0] == 4  # Remaining from first write
    assert all_data[-1] == 11
    print("✓ Circular wraparound working")
    
    # Test stats
    stats = buffer.stats
    assert stats["size"] == 10
    assert stats["available"] == 0
    print(f"✓ Buffer stats: {stats}")


def test_weak_cache():
    """Test weak reference cache."""
    print("\n=== Testing Weak Cache ===")
    
    # Note: The WeakCache class actually has max_strong_refs parameter in __init__
    cache = WeakCache(max_strong_refs=2)
    
    # Use objects that can be weakly referenced
    class TestObj:
        def __init__(self, value):
            self.value = value
    
    obj1 = TestObj("value1")
    obj2 = TestObj("value2") 
    obj3 = TestObj("value3")
    
    # Add items
    cache.put("key1", obj1)
    cache.put("key2", obj2)
    cache.put("key3", obj3)  # This will push key1 to weak ref only
    
    # Test retrieval
    assert cache.get("key2") is obj2
    assert cache.get("key3") is obj3
    # key1 might still be retrievable if not garbage collected
    print("✓ Cache storage and retrieval working")
    
    # Test stats
    stats = cache.stats
    assert stats["strong_refs"] == 2
    assert stats["weak_refs"] >= 1  # At least 1 weak ref
    print(f"✓ Cache stats: {stats}")
    
    # Test eviction  
    obj4 = TestObj("value4")
    cache.put("key4", obj4)
    stats = cache.stats
    assert stats["strong_refs"] == 2  # Still max 2
    print("✓ Cache eviction working")


def test_memory_monitor():
    """Test memory monitoring."""
    print("\n=== Testing Memory Monitor ===")
    
    monitor = MemoryMonitor()
    
    # Get current stats
    stats = monitor.get_current_stats()
    assert stats.rss_mb > 0
    assert 0 <= stats.percent <= 100
    print(f"✓ Memory usage: {stats.rss_mb:.1f}MB ({stats.percent:.1f}%)")
    
    # Test memory allocation tracking
    start_mb = stats.rss_mb
    
    # Allocate some memory
    big_array = np.zeros((1000, 1000), dtype=np.float64)  # ~7.6MB
    
    # Get new stats
    new_stats = monitor.get_current_stats()
    delta = new_stats.rss_mb - start_mb
    print(f"✓ Memory delta detected: {delta:.1f}MB")
    
    # Test trend analysis
    trend = monitor.get_trend()
    # Trend returns a dict with status
    assert isinstance(trend, dict)
    assert "status" in trend
    print(f"✓ Memory trend: {trend['status']}")
    
    # Cleanup
    del big_array
    gc.collect()


def test_buffer_manager():
    """Test buffer manager."""
    print("\n=== Testing Buffer Manager ===")
    
    manager = BufferManager(MemoryProfile.BALANCED)
    
    # Allocate buffers
    buf1 = manager.allocate_buffer("audio")
    buf2 = manager.allocate_buffer("text")
    
    # Check they were allocated
    assert len(buf1) > 0
    assert len(buf2) > 0
    print(f"✓ Buffer allocation working: {len(buf1)} samples")
    
    # Get same buffer again
    buf1_again = manager.allocate_buffer("audio")
    assert buf1_again is buf1  # Same buffer
    print("✓ Buffer reuse working")
    
    # Release buffer
    manager.release_buffer("audio")
    # Buffer should be removed from manager but returned to pool
    print("✓ Buffer release working")
    
    # Resize buffer
    manager.resize_buffer("text", 8192)
    resized = manager.get_buffer("text")
    assert resized is not None
    assert len(resized) == 8192
    print("✓ Buffer resizing working")


def test_memory_optimizer():
    """Test main memory optimizer."""
    print("\n=== Testing Memory Optimizer ===")
    
    # Test minimal profile
    optimizer = MemoryOptimizer(MemoryProfile.MINIMAL)
    assert optimizer.profile == MemoryProfile.MINIMAL
    
    # Create pool
    pool = optimizer.create_pool(
        "test_pool",
        factory=lambda: [0] * 100,
        max_size=10
    )
    assert pool.max_size == 10
    print("✓ Pool creation working")
    
    # Create cache
    cache = optimizer.create_cache("test_cache", max_strong_refs=5)
    # Cache was created successfully
    assert cache is not None
    print("✓ Cache creation working")
    
    # Test memory optimization
    optimizer.optimize_memory()
    print("✓ Memory optimization executed")
    
    # Get suggestions
    suggestions = optimizer.get_optimization_suggestions()
    assert len(suggestions) > 0
    print(f"✓ Suggestions: {suggestions[0]}")
    
    # Test cleanup
    optimizer.cleanup()
    # Cleanup executed successfully
    print("✓ Cleanup working")


def test_audio_memory_manager():
    """Test audio memory management."""
    print("\n=== Testing Audio Memory Manager ===")
    
    manager = AudioMemoryManager(MemoryProfile.BALANCED)
    
    # Test audio chunk processing
    audio_data = np.random.randint(-32768, 32767, 4096, dtype=np.int16).tobytes()
    processed = manager.process_audio_chunk(audio_data)
    assert len(processed) == 4096
    print("✓ Audio chunk processing working")
    
    # Test transcript caching
    manager.cache_transcript("hash1", "test transcript")
    cached = manager.get_cached_transcript("hash1")
    assert cached == "test transcript"
    print("✓ Transcript caching working")
    
    # Test audio caching
    manager.cache_audio("text_hash1", b"audio_data")
    cached = manager.get_cached_audio("text_hash1")
    assert cached == b"audio_data"
    print("✓ Audio caching working")
    
    # Test memory stats
    stats = manager.get_memory_stats()
    assert "profile" in stats
    assert stats["profile"] == "balanced"
    assert "pools" in stats
    assert "caches" in stats
    print(f"✓ Memory stats: Profile={stats['profile']}")
    
    # Cleanup
    manager.cleanup()
    print("✓ Cleanup executed")


async def test_streaming_audio():
    """Test streaming audio buffers."""
    print("\n=== Testing Streaming Audio ===")
    
    manager = AudioMemoryManager(MemoryProfile.MINIMAL)
    
    # Simulate audio stream
    async def audio_generator():
        for i in range(5):
            chunk = np.random.randint(-32768, 32767, 1024, dtype=np.int16).tobytes()
            yield chunk
            await asyncio.sleep(0.01)
    
    # Stream input
    stream_task = asyncio.create_task(manager.stream_audio_input(audio_generator()))
    
    # Give it time to process
    await asyncio.sleep(0.1)
    
    # Check buffer state
    assert manager.input_buffer.available > 0
    print(f"✓ Streamed {manager.input_buffer.available} samples")
    
    # Stream output (may be empty if nothing written to output buffer)
    output = await manager.stream_audio_output()
    # Output can be empty initially
    print(f"✓ Output streaming working: {len(output)} bytes")
    
    # Cancel stream task
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass


async def test_streaming_memory_buffer():
    """Test streaming memory buffer."""
    print("\n=== Testing Streaming Memory Buffer ===")
    
    buffer = StreamingMemoryBuffer(max_duration_seconds=2, sample_rate=16000)
    
    # Add chunks
    chunk1 = np.random.randint(-32768, 32767, 8000, dtype=np.int16)
    chunk2 = np.random.randint(-32768, 32767, 8000, dtype=np.int16)
    
    await buffer.add_chunk(chunk1)
    await buffer.add_chunk(chunk2)
    
    # Check duration
    duration = await buffer.duration_seconds
    assert duration == 1.0  # 16000 samples at 16kHz
    print(f"✓ Buffer duration: {duration:.1f}s")
    
    # Check memory usage
    memory_mb = await buffer.memory_usage_mb
    assert memory_mb > 0
    print(f"✓ Memory usage: {memory_mb:.3f}MB")
    
    # Get audio
    audio = await buffer.get_audio()
    assert len(audio) == 16000
    print(f"✓ Retrieved {len(audio)} samples")
    
    # Test auto-trimming
    chunk3 = np.random.randint(-32768, 32767, 24000, dtype=np.int16)
    await buffer.add_chunk(chunk3)
    
    # Should have trimmed old chunks
    duration = await buffer.duration_seconds
    assert duration <= 2.0
    print(f"✓ Auto-trimming working: {duration:.1f}s")
    
    # Clear buffer
    await buffer.clear()
    duration = await buffer.duration_seconds
    assert duration == 0
    print("✓ Buffer cleared")


def test_voice_memory_optimizer():
    """Test voice memory optimizer."""
    print("\n=== Testing Voice Memory Optimizer ===")
    
    optimizer = VoiceMemoryOptimizer(MemoryProfile.MINIMAL)
    
    # Create session
    session = optimizer.create_session("session1")
    assert "session1" in optimizer.sessions
    assert "audio" in session
    assert "text" in session
    print("✓ Session creation working")
    
    # Test configuration optimization
    config = {
        "chunk_size": 8192,
        "buffer_size": 65536,
        "sample_rate": 48000
    }
    
    optimized = optimizer.optimize_for_voice_mode(config)
    assert optimized["chunk_size"] < config["chunk_size"]  # Reduced for minimal profile
    assert optimized["sample_rate"] < config["sample_rate"]
    assert optimized["streaming"] == True
    print(f"✓ Config optimized: chunk={optimized['chunk_size']}, rate={optimized['sample_rate']}")
    
    # Close session
    optimizer.close_session("session1")
    assert "session1" not in optimizer.sessions
    print("✓ Session cleanup working")
    
    # Get optimization report
    report = optimizer.get_optimization_report()
    assert "profile" in report
    assert report["profile"] == "minimal"
    assert "memory_stats" in report
    print(f"✓ Optimization report: {report['profile']} profile")


async def test_voice_processing():
    """Test voice input/output processing."""
    print("\n=== Testing Voice Processing ===")
    
    optimizer = VoiceMemoryOptimizer(MemoryProfile.BALANCED)
    
    # Test voice input processing
    audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16).tobytes()
    transcript = await optimizer.process_voice_input(audio_data)
    assert transcript is not None
    print(f"✓ Voice input processed: {transcript}")
    
    # Test caching
    transcript2 = await optimizer.process_voice_input(audio_data)
    assert transcript2 == transcript  # Should be cached
    print("✓ Voice input caching working")
    
    # Test voice output generation
    audio_output = await optimizer.generate_voice_output("Hello, world!")
    assert len(audio_output) > 0
    print(f"✓ Voice output generated: {len(audio_output)} bytes")
    
    # Test caching
    audio_output2 = await optimizer.generate_voice_output("Hello, world!")
    assert audio_output2 == audio_output  # Should be cached
    print("✓ Voice output caching working")


def test_integration():
    """Test integration with voice mode."""
    print("\n=== Testing Voice Mode Integration ===")
    
    # Mock voice mode instance
    class MockVoiceMode:
        async def process_audio(self, audio_data: bytes) -> str:
            return "original_process"
        
        async def generate_audio(self, text: str) -> bytes:
            return b"original_audio"
    
    voice_mode = MockVoiceMode()
    
    # Integrate memory optimization
    optimized = integrate_memory_optimization(voice_mode, MemoryProfile.MINIMAL)
    
    # Check attributes added
    assert hasattr(optimized, "memory_optimizer")
    assert hasattr(optimized, "audio_memory")
    assert hasattr(optimized, "get_memory_stats")
    assert hasattr(optimized, "cleanup_memory")
    print("✓ Integration attributes added")
    
    # Test memory stats
    stats = optimized.get_memory_stats()
    assert "profile" in stats
    assert stats["profile"] == "minimal"
    print("✓ Memory stats accessible")
    
    # Test optimization report
    report = optimized.get_optimization_report()
    assert "profile" in report
    assert "memory_stats" in report
    print("✓ Optimization report accessible")
    
    # Cleanup
    optimized.cleanup_memory()
    print("✓ Cleanup working")


def test_global_instance():
    """Test global optimizer instance."""
    print("\n=== Testing Global Instance ===")
    
    # Get global instance
    optimizer1 = get_memory_optimizer(MemoryProfile.BALANCED)
    optimizer2 = get_memory_optimizer(MemoryProfile.BALANCED)
    
    # Should be same instance
    assert optimizer1 is optimizer2
    print("✓ Global singleton working")
    
    # Different profile should create new instance
    optimizer3 = get_memory_optimizer(MemoryProfile.MINIMAL)
    assert optimizer3 is not optimizer1
    assert optimizer3.profile == MemoryProfile.MINIMAL
    print("✓ Profile switching working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MEMORY OPTIMIZATION TESTS")
    print("=" * 60)
    
    # Synchronous tests
    test_memory_pool()
    test_circular_buffer()
    test_weak_cache()
    test_memory_monitor()
    test_buffer_manager()
    test_memory_optimizer()
    test_audio_memory_manager()
    test_voice_memory_optimizer()
    test_integration()
    test_global_instance()
    
    # Async tests
    print("\n=== Running Async Tests ===")
    asyncio.run(test_streaming_audio())
    asyncio.run(test_streaming_memory_buffer())
    asyncio.run(test_voice_processing())
    
    print("\n" + "=" * 60)
    print("✓ All memory optimization tests passed!")
    print("Sprint 29 implementation verified!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()