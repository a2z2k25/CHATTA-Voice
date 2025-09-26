#!/usr/bin/env python3
"""Quick MCP protocol optimization tests."""

import sys
import os
import time
import json

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
    create_voice_optimized_config,
    create_high_throughput_config,
    create_low_bandwidth_config,
    get_optimizer,
    create_optimizer
)


def test_all():
    """Run all quick tests."""
    print("=" * 60)
    print("MCP PROTOCOL OPTIMIZATION QUICK TESTS")
    print("=" * 60)
    
    # Test configuration
    print("\n=== Configuration Tests ===")
    config = OptimizationConfig()
    assert config.compression_mode == CompressionMode.AUTO
    assert config.batching_strategy == BatchingStrategy.ADAPTIVE
    print("✓ Default config working")
    
    voice_config = create_voice_optimized_config()
    assert voice_config.compression_mode == CompressionMode.NONE
    assert voice_config.batching_strategy == BatchingStrategy.DISABLED
    print("✓ Voice optimized config working")
    
    throughput_config = create_high_throughput_config()
    assert throughput_config.batch_size == 50
    print("✓ High throughput config working")
    
    bandwidth_config = create_low_bandwidth_config()
    assert bandwidth_config.compression_level == 9
    print("✓ Low bandwidth config working")
    
    # Test compression
    print("\n=== Compression Tests ===")
    compressor = MessageCompressor(OptimizationConfig(
        compression_mode=CompressionMode.ZLIB,
        compression_threshold=100
    ))
    
    small_data = b"small"
    compressed, method = compressor.compress(small_data)
    assert compressed == small_data  # Below threshold
    print("✓ Small data bypass working")
    
    large_data = b"x" * 1000
    compressed, method = compressor.compress(large_data)
    assert len(compressed) < len(large_data)
    print(f"✓ Compression working: {len(large_data)} → {len(compressed)} bytes")
    
    decompressed = compressor.decompress(compressed, method)
    assert decompressed == large_data
    print("✓ Decompression working")
    
    # Test caching
    print("\n=== Cache Tests ===")
    cache = MessageCache(OptimizationConfig(cache_size=3))
    
    msg1 = {"id": 1}
    resp1 = {"data": "response1"}
    
    assert cache.get(msg1) is None
    print("✓ Cache miss returns None")
    
    cache.put(msg1, resp1)
    assert cache.get(msg1) == resp1
    print("✓ Cache hit returns stored response")
    
    # Test LRU eviction
    for i in range(2, 6):
        cache.put({"id": i}, {"data": f"response{i}"})
    
    assert cache.get(msg1) is None  # Evicted
    print("✓ LRU eviction working")
    
    # Test batching
    print("\n=== Batching Tests ===")
    batcher = MessageBatcher(OptimizationConfig(
        batching_strategy=BatchingStrategy.SIZE_BASED,
        batch_size=3
    ))
    
    for i in range(5):
        batcher.add_message({"id": i})
    
    batch = batcher.get_batch()
    assert len(batch) == 3
    print("✓ Size-based batching working")
    
    batch2 = batcher.get_batch()
    assert len(batch2) == 2
    print("✓ Batch retrieval working")
    
    batcher.shutdown()
    print("✓ Batcher shutdown working")
    
    # Test connection pool
    print("\n=== Connection Pool Tests ===")
    pool = ConnectionPool(OptimizationConfig(connection_pool_size=3))
    
    stats = pool.get_stats()
    assert stats["pool_size"] == 3
    assert stats["available"] == 3
    print("✓ Pool initialization working")
    
    conn1 = pool.acquire(timeout_ms=100)
    assert conn1 is not None
    stats = pool.get_stats()
    assert stats["available"] == 2
    print("✓ Connection acquisition working")
    
    pool.release(conn1)
    stats = pool.get_stats()
    assert stats["available"] == 3
    print("✓ Connection release working")
    
    # Test global optimizer
    print("\n=== Global Optimizer Tests ===")
    opt1 = get_optimizer()
    opt2 = get_optimizer()
    assert opt1 is opt2
    print("✓ Singleton pattern working")
    
    new_opt = create_optimizer(OptimizationConfig(cache_size=456))
    assert new_opt.config.cache_size == 456
    print("✓ Factory creation working")
    
    print("\n" + "=" * 60)
    print("✓ All quick tests passed!")
    print("Sprint 26 implementation verified!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    test_all()