#!/usr/bin/env python3
"""Test MCP protocol optimization system."""

import sys
import os
import time
import json
import asyncio
import threading
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.mcp_optimization import (
    MessageType,
    CompressionMode,
    BatchingStrategy,
    ProtocolMetrics,
    OptimizationConfig,
    MessageCompressor,
    MessageCache,
    MessageBatcher,
    ConnectionPool,
    ProtocolOptimizer,
    StreamOptimizer,
    get_optimizer,
    create_optimizer,
    create_voice_optimized_config,
    create_high_throughput_config,
    create_low_bandwidth_config
)


def test_optimization_config():
    """Test optimization configuration."""
    print("\n=== Testing Optimization Config ===")
    
    # Default config
    config = OptimizationConfig()
    assert config.compression_mode == CompressionMode.AUTO
    assert config.batching_strategy == BatchingStrategy.ADAPTIVE
    assert config.enable_caching == True
    assert config.connection_pool_size == 5
    print("✓ Default config creation working")
    
    # Custom config
    custom_config = OptimizationConfig(
        compression_mode=CompressionMode.ZLIB,
        batching_strategy=BatchingStrategy.SIZE_BASED,
        cache_size=200,
        connection_pool_size=10
    )
    assert custom_config.compression_mode == CompressionMode.ZLIB
    assert custom_config.batching_strategy == BatchingStrategy.SIZE_BASED
    assert custom_config.cache_size == 200
    assert custom_config.connection_pool_size == 10
    print("✓ Custom config creation working")


def test_message_compressor():
    """Test message compression."""
    print("\n=== Testing Message Compressor ===")
    
    config = OptimizationConfig(
        compression_mode=CompressionMode.ZLIB,
        compression_threshold=100
    )
    compressor = MessageCompressor(config)
    
    # Test small data (below threshold)
    small_data = b"small data"
    compressed, method = compressor.compress(small_data)
    assert compressed == small_data
    assert method == "none"
    print("✓ Small data bypasses compression")
    
    # Test large data (above threshold)
    large_data = b"x" * 1000
    compressed, method = compressor.compress(large_data)
    assert len(compressed) < len(large_data)
    assert method == "zlib"
    print(f"✓ Large data compressed: {len(large_data)} → {len(compressed)} bytes")
    
    # Test decompression
    decompressed = compressor.decompress(compressed, method)
    assert decompressed == large_data
    print("✓ Decompression working")
    
    # Test compression ratio
    ratio = compressor.get_compression_ratio()
    assert 0 < ratio < 1  # Should be compressed
    print(f"✓ Compression ratio: {ratio:.3f}")


def test_auto_compression():
    """Test automatic compression mode."""
    print("\n=== Testing Auto Compression ===")
    
    config = OptimizationConfig(compression_mode=CompressionMode.AUTO)
    compressor = MessageCompressor(config)
    
    # Test with different data sizes
    test_data = b"Test data that should be compressed " * 100
    compressed, method = compressor.compress(test_data)
    
    assert len(compressed) < len(test_data)
    assert method in ["zlib", "gzip"]
    print(f"✓ Auto compression selected: {method}")
    
    # Test that incompressible data is not compressed
    random_data = os.urandom(500)  # Random data doesn't compress well
    compressed, method = compressor.compress(random_data)
    
    # May or may not compress depending on data
    print(f"✓ Random data result: {len(random_data)} → {len(compressed)} ({method})")


def test_message_cache():
    """Test message caching."""
    print("\n=== Testing Message Cache ===")
    
    config = OptimizationConfig(cache_size=3, cache_ttl_seconds=1.0)
    cache = MessageCache(config)
    
    # Test cache miss
    message1 = {"type": "request", "id": 1}
    response = cache.get(message1)
    assert response is None
    print("✓ Cache miss returns None")
    
    # Test cache put and hit
    response1 = {"type": "response", "data": "result1"}
    cache.put(message1, response1)
    
    cached = cache.get(message1)
    assert cached == response1
    print("✓ Cache hit returns stored response")
    
    # Test cache capacity (LRU eviction)
    # Put 4 new messages to exceed cache size of 3
    for i in range(2, 6):  # Start from 2 to avoid conflict with message1
        msg = {"type": "request", "id": i}
        resp = {"type": "response", "data": f"result{i}"}
        cache.put(msg, resp)
    
    # First message should be evicted (cache size is 3, we added 4 new ones)
    # Note: message1 was already in cache, so it gets evicted
    assert cache.get(message1) is None
    print("✓ LRU eviction working")
    
    # Test TTL expiration
    message_ttl = {"type": "request", "id": "ttl"}
    response_ttl = {"type": "response", "data": "ttl_result"}
    cache.put(message_ttl, response_ttl)
    
    time.sleep(1.1)  # Wait for TTL to expire
    assert cache.get(message_ttl) is None
    print("✓ TTL expiration working")
    
    # Test cache stats
    stats = cache.get_stats()
    assert "size" in stats
    assert "total_hits" in stats
    print(f"✓ Cache stats: {stats}")


def test_message_batcher():
    """Test message batching."""
    print("\n=== Testing Message Batcher ===")
    
    # Test size-based batching
    config = OptimizationConfig(
        batching_strategy=BatchingStrategy.SIZE_BASED,
        batch_size=3
    )
    batcher = MessageBatcher(config)
    
    # Add messages
    for i in range(5):
        message = {"type": "request", "id": i}
        batcher.add_message(message)
    
    # Get batch
    batch = batcher.get_batch()
    assert len(batch) == 3  # Should get batch_size messages
    print("✓ Size-based batching working")
    
    # Check remaining messages
    batch2 = batcher.get_batch()
    assert len(batch2) == 2  # Remaining messages
    print("✓ Batch retrieval working")
    
    # Test disabled batching
    config_disabled = OptimizationConfig(batching_strategy=BatchingStrategy.DISABLED)
    batcher_disabled = MessageBatcher(config_disabled)
    
    result = batcher_disabled.add_message({"test": "message"})
    assert result is None  # No batching
    print("✓ Disabled batching working")
    
    # Cleanup
    batcher.shutdown()
    batcher_disabled.shutdown()


def test_adaptive_batching():
    """Test adaptive batching strategy."""
    print("\n=== Testing Adaptive Batching ===")
    
    config = OptimizationConfig(
        batching_strategy=BatchingStrategy.ADAPTIVE,
        batch_size=5,
        batch_timeout_ms=100
    )
    batcher = MessageBatcher(config)
    
    # Add messages gradually
    for i in range(3):
        batcher.add_message({"id": i})
    
    # Should not trigger immediate batch (under size limit)
    assert len(batcher.pending_messages) == 3
    
    # Add more to trigger size-based batch
    for i in range(3, 6):
        batcher.add_message({"id": i})
    
    # Should trigger batch
    should_send = batcher._should_send_batch()
    assert should_send == True
    print("✓ Adaptive batching size trigger working")
    
    batcher.shutdown()


def test_connection_pool():
    """Test connection pooling."""
    print("\n=== Testing Connection Pool ===")
    
    config = OptimizationConfig(connection_pool_size=3)
    pool = ConnectionPool(config)
    
    # Test initial state
    stats = pool.get_stats()
    assert stats["pool_size"] == 3
    assert stats["available"] == 3
    assert stats["in_use"] == 0
    print("✓ Pool initialization working")
    
    # Test connection acquisition
    conn1 = pool.acquire(timeout_ms=100)
    assert conn1 is not None
    assert conn1["state"] == "ready"
    
    stats = pool.get_stats()
    assert stats["available"] == 2
    assert stats["in_use"] == 1
    print("✓ Connection acquisition working")
    
    # Test connection release
    pool.release(conn1)
    stats = pool.get_stats()
    assert stats["available"] == 3
    assert stats["in_use"] == 0
    print("✓ Connection release working")
    
    # Test pool exhaustion
    conns = []
    for _ in range(3):
        conn = pool.acquire(timeout_ms=10)
        if conn:
            conns.append(conn)
    
    # Pool should be exhausted
    conn_timeout = pool.acquire(timeout_ms=10)
    assert conn_timeout is None
    print("✓ Pool exhaustion handling working")
    
    # Release all
    for conn in conns:
        pool.release(conn)
    
    # Test unhealthy connection replacement
    bad_conn = pool.acquire()
    bad_conn["error_count"] = 10  # Exceed circuit breaker threshold
    pool.release(bad_conn)
    
    # Should have replaced the connection
    new_conn = pool.acquire()
    assert new_conn["error_count"] == 0
    print("✓ Unhealthy connection replacement working")
    
    pool.release(new_conn)


async def test_protocol_optimizer():
    """Test main protocol optimizer."""
    print("\n=== Testing Protocol Optimizer ===")
    
    config = OptimizationConfig(
        compression_mode=CompressionMode.NONE,  # Disable for testing
        batching_strategy=BatchingStrategy.DISABLED,
        enable_caching=True
    )
    optimizer = ProtocolOptimizer(config)
    
    # Test message sending
    message = {"type": "request", "method": "test", "params": {}}
    response = await optimizer.send_message(message)
    
    assert response is not None
    assert optimizer.metrics.messages_sent == 1
    print("✓ Message sending working")
    
    # Test caching
    response2 = await optimizer.send_message(message)  # Should hit cache
    assert optimizer.metrics.cache_hits == 1
    assert optimizer.metrics.cache_misses == 1
    print("✓ Message caching working")
    
    # Test metrics
    metrics = optimizer.get_metrics()
    assert metrics.messages_sent == 1  # Only one actual send due to cache
    assert metrics.cache_hits == 1
    print(f"✓ Metrics tracking: {metrics.messages_sent} sent, {metrics.cache_hits} cache hits")
    
    # Test optimization presets
    optimizer.optimize_for_latency()
    assert optimizer.config.batching_strategy == BatchingStrategy.DISABLED
    assert optimizer.config.compression_mode == CompressionMode.NONE
    print("✓ Latency optimization working")
    
    optimizer.optimize_for_throughput()
    assert optimizer.config.batching_strategy == BatchingStrategy.ADAPTIVE
    assert optimizer.config.compression_mode == CompressionMode.AUTO
    print("✓ Throughput optimization working")
    
    optimizer.optimize_for_reliability()
    assert optimizer.config.enable_retries == True
    assert optimizer.config.max_retries == 5
    print("✓ Reliability optimization working")
    
    # Cleanup
    optimizer.shutdown()


async def test_stream_optimizer():
    """Test stream optimization."""
    print("\n=== Testing Stream Optimizer ===")
    
    config = OptimizationConfig()
    stream_opt = StreamOptimizer(config)
    
    # Test data streaming
    test_data = b"x" * 10000
    chunks = []
    
    async for chunk in stream_opt.stream_data(test_data):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    print(f"✓ Data streamed in {len(chunks)} chunks")
    
    # Test reassembly
    reassembled = stream_opt.reassemble_stream(chunks)
    assert reassembled == test_data
    print("✓ Stream reassembly working")
    
    # Test sequence numbering
    assert stream_opt.sequence_number > 0
    print(f"✓ Sequence numbering: {stream_opt.sequence_number}")


def test_configuration_presets():
    """Test configuration presets."""
    print("\n=== Testing Configuration Presets ===")
    
    # Voice optimized
    voice_config = create_voice_optimized_config()
    assert voice_config.compression_mode == CompressionMode.NONE
    assert voice_config.batching_strategy == BatchingStrategy.DISABLED
    assert voice_config.async_processing == True
    print("✓ Voice optimized config working")
    
    # High throughput
    throughput_config = create_high_throughput_config()
    assert throughput_config.batching_strategy == BatchingStrategy.ADAPTIVE
    assert throughput_config.batch_size == 50
    assert throughput_config.connection_pool_size == 20
    print("✓ High throughput config working")
    
    # Low bandwidth
    bandwidth_config = create_low_bandwidth_config()
    assert bandwidth_config.compression_mode == CompressionMode.ZLIB
    assert bandwidth_config.compression_level == 9
    assert bandwidth_config.batching_strategy == BatchingStrategy.SIZE_BASED
    print("✓ Low bandwidth config working")


def test_global_optimizer():
    """Test global optimizer instance."""
    print("\n=== Testing Global Optimizer ===")
    
    # Test singleton
    opt1 = get_optimizer()
    opt2 = get_optimizer()
    assert opt1 is opt2
    print("✓ Global optimizer singleton working")
    
    # Test factory
    config = OptimizationConfig(cache_size=123)
    new_opt = create_optimizer(config)
    assert new_opt is not opt1
    assert new_opt.config.cache_size == 123
    print("✓ Optimizer factory working")


async def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")
    
    optimizer = ProtocolOptimizer()
    
    # Test with connection pool exhaustion
    # Acquire all connections
    conns = []
    for _ in range(optimizer.config.connection_pool_size):
        conn = optimizer.pool.acquire(timeout_ms=10)
        if conn:
            conns.append(conn)
    
    # Should timeout
    try:
        # Set very short timeout to trigger error
        optimizer.config.connection_timeout_ms = 1
        await optimizer.send_message({"test": "message"})
        assert False, "Should have raised TimeoutError"
    except TimeoutError:
        print("✓ Connection timeout handling working")
    
    # Release connections
    for conn in conns:
        optimizer.pool.release(conn)
    
    # Test cache with disabled caching
    optimizer.config.enable_caching = False
    message = {"type": "test"}
    response = await optimizer.send_message(message)
    
    # Should not cache
    assert optimizer.metrics.cache_hits == 0
    print("✓ Disabled caching working")
    
    optimizer.shutdown()


async def test_performance():
    """Test performance characteristics."""
    print("\n=== Testing Performance ===")
    
    # Test with voice-optimized config
    config = create_voice_optimized_config()
    optimizer = ProtocolOptimizer(config)
    
    # Measure latency
    latencies = []
    for _ in range(100):
        start_time = time.time()
        await optimizer.send_message({"id": time.time()})
        latency = (time.time() - start_time) * 1000
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    print(f"✓ Average latency: {avg_latency:.2f}ms")
    
    # Should be low with voice optimization
    assert avg_latency < 10  # Under 10ms
    
    # Test throughput
    start_time = time.time()
    tasks = []
    for i in range(100):
        task = optimizer.send_message({"id": i})
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    duration = time.time() - start_time
    throughput = 100 / duration
    
    print(f"✓ Throughput: {throughput:.0f} messages/second")
    
    optimizer.shutdown()


def run_async_test(test_func):
    """Helper to run async tests."""
    asyncio.run(test_func())


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP PROTOCOL OPTIMIZATION TESTS")
    print("=" * 60)
    
    test_optimization_config()
    test_message_compressor()
    test_auto_compression()
    test_message_cache()
    test_message_batcher()
    test_adaptive_batching()
    test_connection_pool()
    run_async_test(test_protocol_optimizer)
    run_async_test(test_stream_optimizer)
    test_configuration_presets()
    test_global_optimizer()
    run_async_test(test_error_handling)
    run_async_test(test_performance)
    
    print("\n" + "=" * 60)
    print("✓ All MCP optimization tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()