#!/usr/bin/env python3
"""Test performance profiling and optimization."""

import sys
import os
import time
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.performance_profiler import (
    ProfileMode,
    OptimizationLevel,
    PerformanceMetrics,
    PerformanceProfiler,
    PerformanceOptimizer,
    MemoryOptimizer,
    get_profiler,
    get_optimizer,
    set_profile_mode,
    set_optimization_level,
    profile,
    memoize
)

from voice_mode.performance_integration import (
    VoicePerformanceMonitor,
    AsyncProfiler,
    CacheOptimizer,
    LatencyOptimizer
)


def test_basic_profiling():
    """Test basic profiling functionality."""
    print("\n=== Testing Basic Profiling ===")
    
    profiler = PerformanceProfiler(ProfileMode.BASIC)
    
    # Test context manager
    with profiler.profile_context("test_operation"):
        time.sleep(0.1)
    
    # Check metrics
    assert "test_operation" in profiler.metrics
    metrics = profiler.metrics["test_operation"][0]
    assert metrics.duration >= 0.1
    print(f"✓ Basic profiling: {metrics.duration:.3f}s")
    
    # Test decorator
    @profiler.profile("decorated_function")
    def slow_function():
        time.sleep(0.05)
        return "done"
    
    result = slow_function()
    assert result == "done"
    assert "decorated_function" in profiler.metrics
    print("✓ Decorator profiling working")


def test_detailed_profiling():
    """Test detailed profiling with memory tracking."""
    print("\n=== Testing Detailed Profiling ===")
    
    profiler = PerformanceProfiler(ProfileMode.DETAILED)
    
    with profiler.profile_context("memory_operation") as metrics:
        # Allocate some memory
        data = [i for i in range(100000)]
        time.sleep(0.05)
    
    assert metrics.memory_delta != 0
    print(f"✓ Memory tracking: {metrics.memory_delta / 1024:.1f}KB allocated")
    
    # Generate report
    report = profiler.generate_report()
    assert report.total_duration > 0
    assert len(report.hotspots) > 0
    print(f"✓ Report generation: {len(report.hotspots)} hotspots identified")


def test_performance_optimizer():
    """Test performance optimization strategies."""
    print("\n=== Testing Performance Optimizer ===")
    
    optimizer = PerformanceOptimizer(OptimizationLevel.MODERATE)
    
    # Test memoization
    call_count = 0
    
    @optimizer.memoize(maxsize=10)
    def expensive_function(x):
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)
        return x * 2
    
    # First call
    result1 = expensive_function(5)
    assert result1 == 10
    assert call_count == 1
    
    # Second call (cached)
    result2 = expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # Not incremented
    print("✓ Memoization working")
    
    # Test audio pipeline optimization
    config = {"chunk_size": 8192, "buffer_size": 32768}
    optimized = optimizer.optimize_audio_pipeline(config)
    assert optimized["chunk_size"] < config["chunk_size"]
    assert "preprocessing" in optimized
    print("✓ Audio pipeline optimization working")


def test_memory_optimizer():
    """Test memory optimization utilities."""
    print("\n=== Testing Memory Optimizer ===")
    
    # Get memory usage
    usage = MemoryOptimizer.get_memory_usage()
    assert "rss_mb" in usage
    assert "percent" in usage
    print(f"✓ Memory usage: {usage['rss_mb']:.1f}MB ({usage['percent']:.1f}%)")
    
    # Test memory optimization
    MemoryOptimizer.optimize_memory()
    print("✓ Memory optimization executed")


async def test_async_profiling():
    """Test async profiling functionality."""
    print("\n=== Testing Async Profiling ===")
    
    async_profiler = AsyncProfiler()
    
    @async_profiler.profile_async("async_operation")
    async def async_function():
        await asyncio.sleep(0.05)
        return "async_done"
    
    result = await async_function()
    assert result == "async_done"
    
    # Check metrics
    profiler = async_profiler.profiler
    assert "async_operation" in profiler.metrics
    metrics = profiler.metrics["async_operation"][0]
    assert "task_name" in metrics.custom_metrics
    print("✓ Async profiling working")
    
    # Test async context manager
    async with async_profiler.profile_async_context("async_context") as metrics:
        await asyncio.sleep(0.02)
        metrics.custom_metrics["test"] = "value"
    
    assert "async_context" in profiler.metrics
    print("✓ Async context manager working")


async def test_voice_performance_monitor():
    """Test voice performance monitoring."""
    print("\n=== Testing Voice Performance Monitor ===")
    
    monitor = VoicePerformanceMonitor()
    
    # Test STT profiling
    text = await monitor.profile_stt(b"audio_data")
    assert text == "transcribed text"
    
    # Test TTS profiling
    audio = await monitor.profile_tts("test text")
    assert audio == b"audio_data"
    
    # Test VAD profiling
    is_speech = monitor.profile_vad(b"audio_chunk")
    assert isinstance(is_speech, bool)
    
    # Get performance stats
    stats = await monitor.get_performance_stats()
    assert "total_duration_ms" in stats
    assert "realtime" in stats
    print(f"✓ Performance stats: {stats['total_duration_ms']:.1f}ms total")
    
    # Test optimization presets
    latency_config = monitor.optimize_for_latency()
    assert latency_config["chunk_size"] == 2048
    print("✓ Latency optimization preset working")
    
    quality_config = monitor.optimize_for_quality()
    assert quality_config["sample_rate"] == 48000
    print("✓ Quality optimization preset working")


def test_cache_optimizer():
    """Test cache optimization."""
    print("\n=== Testing Cache Optimizer ===")
    
    optimizer = PerformanceOptimizer(OptimizationLevel.MODERATE)
    cache_opt = CacheOptimizer(optimizer)
    
    # Test TTS cache
    cache_opt.cache_tts("hello", "voice1", b"audio1")
    cached = cache_opt.get_cached_tts("hello", "voice1")
    assert cached == b"audio1"
    print("✓ TTS cache working")
    
    # Test STT cache
    cache_opt.cache_stt("hash1", "text1")
    cached = cache_opt.get_cached_stt("hash1")
    assert cached == "text1"
    print("✓ STT cache working")
    
    # Test cache stats
    stats = cache_opt.cache_stats
    assert stats["tts_entries"] == 1
    assert stats["stt_entries"] == 1
    print(f"✓ Cache stats: {stats}")
    
    # Test cache clear
    cache_opt.clear_caches()
    stats = cache_opt.cache_stats
    assert stats["tts_entries"] == 0
    print("✓ Cache clearing working")


def test_latency_optimizer():
    """Test latency optimization."""
    print("\n=== Testing Latency Optimizer ===")
    
    latency_opt = LatencyOptimizer()
    
    # Record measurements
    latency_opt.measure_latency("stt", 600)
    latency_opt.measure_latency("stt", 550)
    latency_opt.measure_latency("tts", 150)
    latency_opt.measure_latency("vad", 30)
    
    # Get suggestions
    suggestions = latency_opt.get_optimization_suggestions()
    assert "stt" in suggestions
    assert suggestions["stt"]["status"] in ["warning", "critical"]
    print(f"✓ Latency analysis: STT status = {suggestions['stt']['status']}")
    
    # Apply optimizations
    config = {}
    optimized = latency_opt.apply_optimizations(config)
    if suggestions["stt"]["status"] == "critical":
        assert optimized.get("stt_streaming") == True
    print("✓ Latency optimizations applied")


def test_report_generation():
    """Test performance report generation."""
    print("\n=== Testing Report Generation ===")
    
    import threading  # Import here
    
    profiler = PerformanceProfiler(ProfileMode.DETAILED)
    
    # Generate some test data
    with profiler.profile_context("operation1"):
        time.sleep(0.05)
        
    with profiler.profile_context("operation2") as metrics:
        time.sleep(0.1)
        # Simulate cache miss
        metrics.cache_misses = 10
        metrics.cache_hits = 2
    
    # Generate report
    report = profiler.generate_report()
    
    # Check report contents
    assert report.total_duration >= 0.1  # Lower threshold
    assert len(report.hotspots) == 2
    assert report.hotspots[0][0] == "operation2"  # Slowest first
    
    # Check bottlenecks
    assert len(report.bottlenecks) > 0
    assert any("cache hit rate" in b for b in report.bottlenecks)
    print(f"✓ Bottlenecks identified: {len(report.bottlenecks)}")
    
    # Check recommendations
    assert len(report.recommendations) > 0
    print(f"✓ Recommendations: {report.recommendations[0]}")
    
    # Export as JSON
    json_report = report.to_json()
    data = json.loads(json_report)
    assert "total_duration_ms" in data
    assert "hotspots" in data
    print("✓ JSON export working")


def test_global_instances():
    """Test global profiler and optimizer instances."""
    print("\n=== Testing Global Instances ===")
    
    # Test global profiler
    set_profile_mode(ProfileMode.DETAILED)
    profiler1 = get_profiler()
    profiler2 = get_profiler()
    assert profiler1 is profiler2
    assert profiler1.mode == ProfileMode.DETAILED
    print("✓ Global profiler singleton working")
    
    # Test global optimizer
    set_optimization_level(OptimizationLevel.AGGRESSIVE)
    optimizer1 = get_optimizer()
    optimizer2 = get_optimizer()
    assert optimizer1 is optimizer2
    assert optimizer1.level == OptimizationLevel.AGGRESSIVE
    print("✓ Global optimizer singleton working")
    
    # Test convenience decorators
    @profile("global_test")
    def test_func():
        return 42
    
    result = test_func()
    assert result == 42
    assert "global_test" in get_profiler().metrics
    print("✓ Global decorators working")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PERFORMANCE PROFILING TESTS")
    print("=" * 60)
    
    import threading
    
    test_basic_profiling()
    test_detailed_profiling()
    test_performance_optimizer()
    test_memory_optimizer()
    
    # Run async tests
    print("\n=== Running Async Tests ===")
    asyncio.run(test_async_profiling())
    asyncio.run(test_voice_performance_monitor())
    
    test_cache_optimizer()
    test_latency_optimizer()
    test_report_generation()
    test_global_instances()
    
    print("\n" + "=" * 60)
    print("✓ All performance profiling tests passed!")
    print("Sprint 28 implementation verified!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()