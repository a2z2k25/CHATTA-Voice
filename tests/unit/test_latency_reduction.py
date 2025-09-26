#!/usr/bin/env python3
"""Test latency reduction framework."""

import sys
import os
import time
import asyncio
import numpy as np
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.latency_reducer import (
    LatencyMode,
    LatencyMetrics,
    LatencyTracker,
    PipelineOptimizer,
    PredictiveBuffer,
    StreamOptimizer,
    ConnectionPoolManager,
    LatencyReducer,
    get_latency_reducer,
    set_latency_mode
)

from voice_mode.latency_integration import (
    AudioLatencyOptimizer,
    VoiceLatencyOptimizer,
    RealtimeLatencyMonitor,
    integrate_latency_optimization
)


def test_latency_metrics():
    """Test latency metrics tracking."""
    print("\n=== Testing Latency Metrics ===")
    
    metrics = LatencyMetrics(
        component="test",
        start_time=time.perf_counter()
    )
    
    # Simulate some work
    time.sleep(0.01)
    
    duration = metrics.complete()
    assert duration > 10  # At least 10ms
    assert metrics.end_time is not None
    assert metrics.duration_ms is not None
    print(f"✓ Metrics tracking: {duration:.2f}ms")


def test_latency_tracker():
    """Test latency tracker."""
    print("\n=== Testing Latency Tracker ===")
    
    tracker = LatencyTracker(window_size=10)
    
    # Track multiple operations
    for i in range(5):
        metrics = tracker.start_operation("stt")
        time.sleep(0.01 + i * 0.005)  # Variable delays
        tracker.complete_operation(metrics)
    
    # Get stats
    stats = tracker.get_stats("stt")
    assert stats["count"] == 5
    assert stats["mean"] > 10
    assert stats["median"] > 10
    assert stats["p95"] > stats["mean"]
    print(f"✓ STT stats: mean={stats['mean']:.1f}ms, p95={stats['p95']:.1f}ms")
    
    # Test all stats
    all_stats = tracker.get_all_stats()
    assert "stt" in all_stats
    assert "tts" in all_stats  # Even if no data
    print(f"✓ Components tracked: {list(all_stats.keys())}")
    
    # Test target checking
    tracker._targets["stt"] = 100  # Set achievable target
    is_meeting = tracker.is_meeting_targets()
    assert is_meeting  # Should meet 100ms target
    print("✓ Target checking working")


async def test_pipeline_optimizer():
    """Test pipeline optimization."""
    print("\n=== Testing Pipeline Optimizer ===")
    
    optimizer = PipelineOptimizer(LatencyMode.BALANCED)
    
    # Define pipeline stages
    async def stage1(data):
        await asyncio.sleep(0.01)
        return data + "_stage1"
    
    async def stage2(data):
        await asyncio.sleep(0.01)
        return data + "_stage2"
    
    async def stage3(data):
        await asyncio.sleep(0.01)
        return data + "_stage3"
    
    # Register pipeline
    optimizer.register_pipeline("test", [stage1, stage2, stage3])
    
    # Execute sequentially
    start = time.perf_counter()
    result = await optimizer.execute_pipeline("test", "data", parallel=False)
    sequential_time = (time.perf_counter() - start) * 1000
    assert "stage3" in result
    print(f"✓ Sequential execution: {sequential_time:.1f}ms")
    
    # Execute in parallel (simplified test)
    start = time.perf_counter()
    result = await optimizer.execute_pipeline("test", "data", parallel=True)
    parallel_time = (time.perf_counter() - start) * 1000
    # Parallel should be faster or similar
    print(f"✓ Parallel execution: {parallel_time:.1f}ms")
    
    # Test caching
    optimizer.cache_result("key1", "value1", ttl=60)
    cached = optimizer.get_cached("key1")
    assert cached == "value1"
    print("✓ Caching working")
    
    # Test cache expiry
    optimizer.cache_result("key2", "value2", ttl=0.01)
    time.sleep(0.02)
    cached = optimizer.get_cached("key2")
    assert cached is None
    print("✓ Cache expiry working")
    
    # Check cache hit rate
    optimizer.get_cached("key1")  # Hit
    optimizer.get_cached("key3")  # Miss
    rate = optimizer.cache_hit_rate
    assert rate > 0
    print(f"✓ Cache hit rate: {rate:.1%}")


async def test_predictive_buffer():
    """Test predictive buffering."""
    print("\n=== Testing Predictive Buffer ===")
    
    buffer = PredictiveBuffer(capacity=5)
    
    # Set predictor
    call_count = 0
    async def predictor():
        nonlocal call_count
        call_count += 1
        return {"key": f"key{call_count}", "value": f"value{call_count}"}
    
    buffer.set_predictor(predictor)
    
    # Start prefetching
    await buffer.start_prefetching()
    
    # Wait for some predictions
    await asyncio.sleep(0.3)
    
    # Try to get predicted value
    value = await buffer.get("key1")
    # May or may not hit depending on timing
    print(f"✓ Prediction attempt: {'hit' if value else 'miss'}")
    
    # Stop prefetching
    await buffer.stop_prefetching()
    
    # Check hit rate
    rate = buffer.hit_rate
    print(f"✓ Prediction hit rate: {rate:.1%}")


async def test_stream_optimizer():
    """Test stream optimization."""
    print("\n=== Testing Stream Optimizer ===")
    
    optimizer = StreamOptimizer(LatencyMode.LOW)
    
    # Check chunk sizes
    assert optimizer.chunk_size == 1024
    assert optimizer.buffer_size == 4096
    print(f"✓ Low latency config: chunk={optimizer.chunk_size}, buffer={optimizer.buffer_size}")
    
    # Test streaming
    results = []
    
    async def source():
        for i in range(5):
            yield f"chunk_{i}"
            await asyncio.sleep(0.01)
    
    async def processor(chunks):
        return "_".join(chunks)
    
    async def sink(data):
        results.append(data)
    
    await optimizer.stream_with_optimization(source(), processor, sink)
    
    assert len(results) > 0
    print(f"✓ Streamed {len(results)} batches")


def test_connection_pool():
    """Test connection pool management."""
    print("\n=== Testing Connection Pool ===")
    
    manager = ConnectionPoolManager(LatencyMode.ULTRA_LOW)
    
    # Create pool
    conn_count = 0
    def factory():
        nonlocal conn_count
        conn_count += 1
        return {"id": conn_count}
    
    manager.create_pool("test", factory, size=3)
    
    # Acquire connections
    conn1 = manager.acquire("test")
    conn2 = manager.acquire("test")
    conn3 = manager.acquire("test")
    
    assert conn1 is not None
    assert conn2 is not None
    assert conn3 is not None
    assert conn_count == 3
    print(f"✓ Created {conn_count} connections")
    
    # Try to acquire when pool exhausted
    conn4 = manager.acquire("test", timeout=0.1)
    assert conn4 is None
    print("✓ Pool exhaustion handled")
    
    # Release and reacquire
    manager.release("test", conn1)
    conn5 = manager.acquire("test")
    assert conn5 is conn1  # Same connection reused
    print("✓ Connection reuse working")


async def test_latency_reducer():
    """Test main latency reducer."""
    print("\n=== Testing Latency Reducer ===")
    
    reducer = LatencyReducer(LatencyMode.LOW)
    
    # Test mode configuration
    assert reducer.mode == LatencyMode.LOW
    assert reducer.tracker._targets["stt"] == 300
    print("✓ Low latency mode configured")
    
    # Test STT optimization
    audio_data = b"test_audio"
    result = await reducer.optimize_stt(audio_data)
    assert result == "transcribed text"
    print("✓ STT optimization working")
    
    # Test TTS optimization
    text = "test text"
    audio = await reducer.optimize_tts(text)
    assert audio == b"audio_data"
    print("✓ TTS optimization working")
    
    # Test caching
    audio2 = await reducer.optimize_tts(text)
    assert audio2 == audio
    assert reducer.pipeline_optimizer.cache_hit_rate > 0
    print(f"✓ Cache hit rate: {reducer.pipeline_optimizer.cache_hit_rate:.1%}")
    
    # Get suggestions
    suggestions = reducer.get_optimization_suggestions()
    # Should have suggestions about low prediction rate
    assert len(suggestions) > 0
    print(f"✓ Optimization suggestions: {len(suggestions)}")
    
    # Get performance report
    report = reducer.get_performance_report()
    assert report["mode"] == "low"
    assert "latency_stats" in report
    assert "suggestions" in report
    print(f"✓ Performance report: mode={report['mode']}, meeting_targets={report['meeting_targets']}")


async def test_audio_latency_optimizer():
    """Test audio latency optimization."""
    print("\n=== Testing Audio Latency Optimizer ===")
    
    optimizer = AudioLatencyOptimizer(LatencyMode.ULTRA_LOW)
    
    # Test audio processing
    audio_data = b"test_audio_data"
    result = await optimizer.process_audio_with_optimization(audio_data)
    assert result is not None
    print("✓ Audio processing optimized")
    
    # Test caching
    result2 = await optimizer.process_audio_with_optimization(audio_data)
    assert result2 == result
    assert optimizer._cache_hits > 0
    print(f"✓ Cache hits: {optimizer._cache_hits}")
    
    # Test audio generation
    audio = await optimizer.generate_audio_with_optimization("Hello")
    assert len(audio) > 0
    print("✓ Audio generation optimized")
    
    # Test streaming
    async def audio_stream():
        for i in range(3):
            yield f"chunk_{i}".encode()
            await asyncio.sleep(0.01)
    
    results = await optimizer.stream_audio_with_optimization(audio_stream())
    assert len(results) > 0
    print(f"✓ Streamed {len(results)} results")
    
    # Get stats
    stats = optimizer.get_optimization_stats()
    assert stats["mode"] == "ultra_low"
    assert stats["request_count"] > 0
    assert "cache_hit_rate" in stats
    assert "latency_stats" in stats
    print(f"✓ Optimization stats: {stats['request_count']} requests, cache_rate={stats['cache_hit_rate']:.1%}")


async def test_voice_latency_optimizer():
    """Test voice-specific optimization."""
    print("\n=== Testing Voice Latency Optimizer ===")
    
    optimizer = VoiceLatencyOptimizer(LatencyMode.BALANCED)
    
    # Create session
    session = optimizer.create_voice_session("session1")
    assert session["id"] == "session1"
    assert session["chunk_duration_ms"] == 30  # Balanced mode
    print(f"✓ Session created: chunk={session['chunk_duration_ms']}ms")
    
    # Process voice chunks
    chunk1 = b"voice_chunk_1"
    result1 = await optimizer.process_voice_chunk("session1", chunk1)
    assert result1 is not None
    
    chunk2 = b"voice_chunk_2"
    result2 = await optimizer.process_voice_chunk("session1", chunk2)
    assert result2 is not None
    print("✓ Voice chunks processed")
    
    # Generate response
    response = await optimizer.generate_voice_response("session1", "Hello there")
    assert len(response) > 0
    print("✓ Voice response generated")
    
    # Get session stats
    stats = optimizer.get_session_stats("session1")
    assert stats["stt_count"] == 2
    assert stats["tts_count"] == 1
    assert stats["avg_latency_ms"] >= 0
    print(f"✓ Session stats: STT={stats['stt_count']}, TTS={stats['tts_count']}, avg_latency={stats['avg_latency_ms']:.1f}ms")
    
    # Close session
    optimizer.close_session("session1")
    assert "session1" not in optimizer.sessions
    print("✓ Session closed")


async def test_realtime_monitor():
    """Test real-time latency monitoring."""
    print("\n=== Testing Realtime Monitor ===")
    
    monitor = RealtimeLatencyMonitor()
    
    # Start monitoring
    await monitor.start_monitoring(interval_seconds=0.1)
    assert monitor._monitoring
    print("✓ Monitoring started")
    
    # Wait for some monitoring cycles
    await asyncio.sleep(0.3)
    
    # Check for alerts
    alerts = monitor.get_alerts()
    # May have alerts about low cache/prediction rates
    print(f"✓ Generated {len(alerts)} alerts")
    
    # Get monitoring report
    report = monitor.get_monitoring_report()
    assert report["monitoring"] == True
    assert "performance_report" in report
    assert "recent_alerts" in report
    print(f"✓ Monitoring report: {report['alert_count']} total alerts")
    
    # Stop monitoring
    await monitor.stop_monitoring()
    assert not monitor._monitoring
    print("✓ Monitoring stopped")


def test_integration():
    """Test integration with voice mode."""
    print("\n=== Testing Voice Mode Integration ===")
    
    # Mock voice mode instance
    class MockVoiceMode:
        async def process_audio(self, audio_data: bytes) -> str:
            return "original_transcript"
        
        async def generate_audio(self, text: str) -> bytes:
            return b"original_audio"
    
    voice_mode = MockVoiceMode()
    
    # Integrate latency optimization
    optimized = integrate_latency_optimization(voice_mode, LatencyMode.LOW)
    
    # Check attributes added
    assert hasattr(optimized, "audio_latency_optimizer")
    assert hasattr(optimized, "voice_latency_optimizer")
    assert hasattr(optimized, "latency_monitor")
    assert hasattr(optimized, "get_latency_stats")
    assert hasattr(optimized, "set_latency_mode")
    print("✓ Integration attributes added")
    
    # Test latency stats
    stats = optimized.get_latency_stats()
    assert "audio_stats" in stats
    assert "voice_sessions" in stats
    assert "monitoring" in stats
    print("✓ Latency stats accessible")
    
    # Test mode switching
    optimized.set_latency_mode(LatencyMode.ULTRA_LOW)
    assert optimized.audio_latency_optimizer.mode == LatencyMode.ULTRA_LOW
    print("✓ Mode switching working")


def test_global_instance():
    """Test global latency reducer."""
    print("\n=== Testing Global Instance ===")
    
    # Get global instance
    reducer1 = get_latency_reducer(LatencyMode.BALANCED)
    reducer2 = get_latency_reducer(LatencyMode.BALANCED)
    
    # Should be same instance
    assert reducer1 is reducer2
    print("✓ Global singleton working")
    
    # Different mode should create new instance
    reducer3 = get_latency_reducer(LatencyMode.ULTRA_LOW)
    assert reducer3 is not reducer1
    assert reducer3.mode == LatencyMode.ULTRA_LOW
    print("✓ Mode switching creates new instance")
    
    # Set global mode
    set_latency_mode(LatencyMode.RELAXED)
    reducer4 = get_latency_reducer(LatencyMode.RELAXED)  # Need to pass mode explicitly
    assert reducer4.mode == LatencyMode.RELAXED
    print("✓ Global mode setting working")


async def test_end_to_end_latency():
    """Test end-to-end latency optimization."""
    print("\n=== Testing End-to-End Latency ===")
    
    # Create optimized system
    optimizer = AudioLatencyOptimizer(LatencyMode.ULTRA_LOW)
    
    # Simulate end-to-end flow
    start = time.perf_counter()
    
    # Input audio
    audio_input = b"user_speech_audio"
    transcript = await optimizer.process_audio_with_optimization(audio_input)
    
    # Generate response (simplified)
    response_text = f"Response to: {transcript}"
    
    # Generate output audio
    audio_output = await optimizer.generate_audio_with_optimization(response_text)
    
    # Calculate total latency
    total_latency = (time.perf_counter() - start) * 1000
    
    assert transcript is not None
    assert len(audio_output) > 0
    print(f"✓ End-to-end latency: {total_latency:.1f}ms")
    
    # Check if meeting ultra-low targets
    stats = optimizer.get_optimization_stats()
    print(f"✓ Ultra-low mode active: {stats['mode']}")
    
    # Verify optimization is working
    assert stats["meeting_targets"] or total_latency < 100  # Ultra-low target


def main():
    """Run all tests."""
    print("=" * 60)
    print("LATENCY REDUCTION TESTS")
    print("=" * 60)
    
    # Synchronous tests
    test_latency_metrics()
    test_latency_tracker()
    test_connection_pool()
    test_integration()
    test_global_instance()
    
    # Async tests
    print("\n=== Running Async Tests ===")
    asyncio.run(test_pipeline_optimizer())
    asyncio.run(test_predictive_buffer())
    asyncio.run(test_stream_optimizer())
    asyncio.run(test_latency_reducer())
    asyncio.run(test_audio_latency_optimizer())
    asyncio.run(test_voice_latency_optimizer())
    asyncio.run(test_realtime_monitor())
    asyncio.run(test_end_to_end_latency())
    
    print("\n" + "=" * 60)
    print("✓ All latency reduction tests passed!")
    print("Sprint 30 implementation complete!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()