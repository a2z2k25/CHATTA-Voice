#!/usr/bin/env python3
"""MCP Protocol Optimization for Claude Code

This module provides optimized Model Context Protocol (MCP) implementation
with enhanced performance, reliability, and efficiency for voice interactions.
"""

import os
import sys
import json
import time
import asyncio
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union, Any, Callable, AsyncIterator
from enum import Enum
import hashlib
import zlib
from collections import deque
import struct

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    STREAM = "stream"
    BATCH = "batch"


class CompressionMode(Enum):
    """Message compression modes."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZ4 = "lz4"
    AUTO = "auto"


class BatchingStrategy(Enum):
    """Message batching strategies."""
    DISABLED = "disabled"
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    ADAPTIVE = "adaptive"


@dataclass
class ProtocolMetrics:
    """Metrics for protocol performance."""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    compression_ratio: float = 1.0
    average_latency_ms: float = 0.0
    error_count: int = 0
    retry_count: int = 0
    batch_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class OptimizationConfig:
    """Configuration for MCP optimization."""
    # Compression settings
    compression_mode: CompressionMode = CompressionMode.AUTO
    compression_threshold: int = 1024  # bytes
    compression_level: int = 6  # 1-9
    
    # Batching settings
    batching_strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    batch_size: int = 10
    batch_timeout_ms: float = 100.0
    
    # Caching settings
    enable_caching: bool = True
    cache_size: int = 100
    cache_ttl_seconds: float = 300.0
    
    # Connection pooling
    connection_pool_size: int = 5
    connection_timeout_ms: float = 5000.0
    keep_alive_interval_ms: float = 30000.0
    
    # Performance settings
    async_processing: bool = True
    pipeline_depth: int = 3
    prefetch_count: int = 2
    
    # Reliability settings
    enable_retries: bool = True
    max_retries: int = 3
    retry_backoff_ms: float = 1000.0
    circuit_breaker_threshold: int = 5


class MessageCompressor:
    """Handles message compression and decompression."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.compression_stats = {
            "total_compressed": 0,
            "total_uncompressed": 0,
            "compression_time_ms": 0.0
        }
    
    def compress(self, data: bytes) -> tuple[bytes, str]:
        """Compress data using configured method."""
        if len(data) < self.config.compression_threshold:
            return data, "none"
        
        start_time = time.time()
        
        if self.config.compression_mode == CompressionMode.AUTO:
            # Choose best compression for data size
            if len(data) < 4096:
                compressed = zlib.compress(data, level=self.config.compression_level)
                method = "zlib"
            else:
                compressed = zlib.compress(data, level=self.config.compression_level)
                method = "gzip"
        elif self.config.compression_mode == CompressionMode.ZLIB:
            compressed = zlib.compress(data, level=self.config.compression_level)
            method = "zlib"
        elif self.config.compression_mode == CompressionMode.GZIP:
            import gzip
            compressed = gzip.compress(data, compresslevel=self.config.compression_level)
            method = "gzip"
        else:
            return data, "none"
        
        compression_time = (time.time() - start_time) * 1000
        self.compression_stats["compression_time_ms"] += compression_time
        self.compression_stats["total_compressed"] += len(compressed)
        self.compression_stats["total_uncompressed"] += len(data)
        
        # Only use compression if it reduces size
        if len(compressed) < len(data):
            return compressed, method
        return data, "none"
    
    def decompress(self, data: bytes, method: str) -> bytes:
        """Decompress data using specified method."""
        if method == "none":
            return data
        elif method == "zlib":
            return zlib.decompress(data)
        elif method == "gzip":
            import gzip
            return gzip.decompress(data)
        else:
            raise ValueError(f"Unknown compression method: {method}")
    
    def get_compression_ratio(self) -> float:
        """Get overall compression ratio."""
        if self.compression_stats["total_uncompressed"] == 0:
            return 1.0
        return (self.compression_stats["total_compressed"] / 
                self.compression_stats["total_uncompressed"])


class MessageCache:
    """LRU cache for message responses."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.cache = {}
        self.access_times = {}
        self.access_counts = {}
        self._lock = threading.Lock()
    
    def _generate_key(self, message: Dict[str, Any]) -> str:
        """Generate cache key for message."""
        # Create deterministic key from message content
        key_data = json.dumps(message, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached response for message."""
        if not self.config.enable_caching:
            return None
        
        key = self._generate_key(message)
        
        with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() - self.access_times[key] < self.config.cache_ttl_seconds:
                    self.access_counts[key] += 1
                    self.access_times[key] = time.time()
                    return self.cache[key].copy()
                else:
                    # Expired
                    del self.cache[key]
                    del self.access_times[key]
                    del self.access_counts[key]
        
        return None
    
    def put(self, message: Dict[str, Any], response: Dict[str, Any]):
        """Cache response for message."""
        if not self.config.enable_caching:
            return
        
        key = self._generate_key(message)
        
        with self._lock:
            # Enforce cache size limit (LRU eviction)
            if len(self.cache) >= self.config.cache_size:
                # Find least recently used
                lru_key = min(self.access_times, key=self.access_times.get)
                del self.cache[lru_key]
                del self.access_times[lru_key]
                del self.access_counts[lru_key]
            
            self.cache[key] = response.copy()
            self.access_times[key] = time.time()
            self.access_counts[key] = 0
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.access_counts.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(self.access_counts.values())
            return {
                "size": len(self.cache),
                "total_hits": total_hits,
                "avg_hits_per_entry": total_hits / max(1, len(self.cache))
            }


class MessageBatcher:
    """Batches messages for efficient transmission."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.pending_messages = deque()
        self.batch_lock = threading.Lock()
        self.batch_event = threading.Event()
        self.total_batches = 0
        self.total_messages_batched = 0
        self._shutdown = False
        self.worker_thread = None
        
        if config.batching_strategy != BatchingStrategy.DISABLED:
            self._start_batch_worker()
    
    def add_message(self, message: Dict[str, Any]) -> Optional[asyncio.Future]:
        """Add message to batch queue."""
        if self.config.batching_strategy == BatchingStrategy.DISABLED:
            return None
        
        with self.batch_lock:
            future = None
            if self.config.async_processing:
                try:
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                except RuntimeError:
                    # No event loop running
                    future = None
            self.pending_messages.append((message, future, time.time()))
            
            # Check if batch should be sent
            if self._should_send_batch():
                self.batch_event.set()
            
            return future
    
    def get_batch(self) -> List[Dict[str, Any]]:
        """Get current batch of messages."""
        with self.batch_lock:
            if not self.pending_messages:
                return []
            
            batch = []
            futures = []
            
            # Collect messages for batch
            batch_size = min(self.config.batch_size, len(self.pending_messages))
            for _ in range(batch_size):
                msg, future, timestamp = self.pending_messages.popleft()
                batch.append(msg)
                if future:
                    futures.append(future)
            
            self.total_batches += 1
            self.total_messages_batched += len(batch)
            
            return batch
    
    def _should_send_batch(self) -> bool:
        """Determine if batch should be sent."""
        if not self.pending_messages:
            return False
        
        if self.config.batching_strategy == BatchingStrategy.SIZE_BASED:
            return len(self.pending_messages) >= self.config.batch_size
        
        elif self.config.batching_strategy == BatchingStrategy.TIME_BASED:
            oldest_timestamp = self.pending_messages[0][2]
            age_ms = (time.time() - oldest_timestamp) * 1000
            return age_ms >= self.config.batch_timeout_ms
        
        elif self.config.batching_strategy == BatchingStrategy.ADAPTIVE:
            # Adaptive strategy based on load
            if len(self.pending_messages) >= self.config.batch_size:
                return True
            if self.pending_messages:
                oldest_timestamp = self.pending_messages[0][2]
                age_ms = (time.time() - oldest_timestamp) * 1000
                # Reduce timeout under load
                adaptive_timeout = self.config.batch_timeout_ms / max(1, len(self.pending_messages))
                return age_ms >= adaptive_timeout
        
        return False
    
    def _start_batch_worker(self):
        """Start background worker for batch processing."""
        def worker():
            while not self._shutdown:
                self.batch_event.wait(timeout=self.config.batch_timeout_ms / 1000)
                if self._shutdown:
                    break
                self.batch_event.clear()
                
                if self._should_send_batch():
                    # Trigger batch send (would be handled by protocol)
                    pass
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def shutdown(self):
        """Shutdown batch worker."""
        self._shutdown = True
        self.batch_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)


class ConnectionPool:
    """Connection pooling for MCP connections."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.connections = []
        self.available = deque()
        self.in_use = set()
        self._lock = threading.Lock()
        self._create_connections()
    
    def _create_connections(self):
        """Create initial connection pool."""
        for i in range(self.config.connection_pool_size):
            conn = self._create_connection(i)
            self.connections.append(conn)
            self.available.append(conn)
    
    def _create_connection(self, conn_id: int) -> Dict[str, Any]:
        """Create a new connection."""
        return {
            "id": conn_id,
            "created": time.time(),
            "last_used": time.time(),
            "request_count": 0,
            "error_count": 0,
            "state": "ready"
        }
    
    def acquire(self, timeout_ms: float = None) -> Optional[Dict[str, Any]]:
        """Acquire connection from pool."""
        timeout_ms = timeout_ms or self.config.connection_timeout_ms
        start_time = time.time()
        
        while (time.time() - start_time) * 1000 < timeout_ms:
            with self._lock:
                if self.available:
                    conn = self.available.popleft()
                    self.in_use.add(conn["id"])
                    conn["last_used"] = time.time()
                    return conn
            
            time.sleep(0.01)  # Brief wait before retry
        
        return None  # Timeout
    
    def release(self, conn: Dict[str, Any]):
        """Release connection back to pool."""
        with self._lock:
            if conn["id"] in self.in_use:
                self.in_use.remove(conn["id"])
                
                # Check connection health
                if conn["error_count"] < self.config.circuit_breaker_threshold:
                    self.available.append(conn)
                else:
                    # Replace unhealthy connection
                    new_conn = self._create_connection(conn["id"])
                    self.connections[conn["id"]] = new_conn
                    self.available.append(new_conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            total_requests = sum(c["request_count"] for c in self.connections)
            total_errors = sum(c["error_count"] for c in self.connections)
            
            return {
                "pool_size": len(self.connections),
                "available": len(self.available),
                "in_use": len(self.in_use),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / max(1, total_requests)
            }


class ProtocolOptimizer:
    """Main MCP protocol optimizer."""
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self.compressor = MessageCompressor(self.config)
        self.cache = MessageCache(self.config)
        self.batcher = MessageBatcher(self.config)
        self.pool = ConnectionPool(self.config)
        self.metrics = ProtocolMetrics()
        self._callbacks = {}
        self._pipeline = deque()
        self._lock = threading.Lock()
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send optimized message."""
        start_time = time.time()
        
        # Check cache first
        cached_response = self.cache.get(message)
        if cached_response:
            self.metrics.cache_hits += 1
            return cached_response
        
        self.metrics.cache_misses += 1
        
        # Compression
        message_bytes = json.dumps(message).encode()
        compressed_data, compression_method = self.compressor.compress(message_bytes)
        
        # Update metrics
        self.metrics.messages_sent += 1
        self.metrics.bytes_sent += len(compressed_data)
        
        # Batching decision
        if self._should_batch(message):
            future = self.batcher.add_message(message)
            if future and self.config.async_processing:
                return await future
        
        # Get connection from pool
        conn = self.pool.acquire()
        if not conn:
            raise TimeoutError("Failed to acquire connection")
        
        try:
            # Simulate sending (would be actual protocol implementation)
            response = await self._send_via_connection(conn, compressed_data, compression_method)
            
            # Cache response
            self.cache.put(message, response)
            
            # Update metrics
            latency_ms = (time.time() - start_time) * 1000
            self._update_latency(latency_ms)
            
            return response
            
        finally:
            self.pool.release(conn)
    
    async def receive_message(self) -> Dict[str, Any]:
        """Receive optimized message."""
        # In real implementation, would receive from transport
        compressed_data = b""  # Placeholder
        compression_method = "none"
        
        # Decompress
        message_bytes = self.compressor.decompress(compressed_data, compression_method)
        message = json.loads(message_bytes)
        
        # Update metrics
        self.metrics.messages_received += 1
        self.metrics.bytes_received += len(compressed_data)
        
        return message
    
    def enable_pipelining(self):
        """Enable request pipelining."""
        self.config.pipeline_depth = max(1, self.config.pipeline_depth)
    
    def enable_prefetching(self):
        """Enable response prefetching."""
        self.config.prefetch_count = max(1, self.config.prefetch_count)
    
    def optimize_for_latency(self):
        """Optimize settings for low latency."""
        self.config.batching_strategy = BatchingStrategy.DISABLED
        self.config.compression_mode = CompressionMode.NONE
        self.config.async_processing = True
        self.config.pipeline_depth = 5
    
    def optimize_for_throughput(self):
        """Optimize settings for high throughput."""
        self.config.batching_strategy = BatchingStrategy.ADAPTIVE
        self.config.compression_mode = CompressionMode.AUTO
        self.config.batch_size = 20
        self.config.connection_pool_size = 10
    
    def optimize_for_reliability(self):
        """Optimize settings for reliability."""
        self.config.enable_retries = True
        self.config.max_retries = 5
        self.config.circuit_breaker_threshold = 3
        self.config.keep_alive_interval_ms = 10000.0
    
    def get_metrics(self) -> ProtocolMetrics:
        """Get current protocol metrics."""
        self.metrics.compression_ratio = self.compressor.get_compression_ratio()
        return self.metrics
    
    def reset_metrics(self):
        """Reset protocol metrics."""
        self.metrics = ProtocolMetrics()
    
    async def _send_via_connection(self, conn: Dict[str, Any], 
                                   data: bytes, compression: str) -> Dict[str, Any]:
        """Send data via specific connection."""
        conn["request_count"] += 1
        
        # Simulate network send with retry logic
        for attempt in range(self.config.max_retries):
            try:
                # In real implementation, would send via transport
                await asyncio.sleep(0.001)  # Simulate network delay
                
                # Simulate response
                return {"status": "success", "data": "response"}
                
            except Exception as e:
                conn["error_count"] += 1
                self.metrics.error_count += 1
                self.metrics.retry_count += 1
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(self.config.retry_backoff_ms * (2 ** attempt) / 1000)
    
    def _should_batch(self, message: Dict[str, Any]) -> bool:
        """Determine if message should be batched."""
        if self.config.batching_strategy == BatchingStrategy.DISABLED:
            return False
        
        # Don't batch high-priority or time-sensitive messages
        if message.get("priority") == "high":
            return False
        if message.get("type") == MessageType.STREAM.value:
            return False
        
        return True
    
    def _update_latency(self, latency_ms: float):
        """Update average latency metric."""
        alpha = 0.1  # Exponential moving average factor
        if self.metrics.average_latency_ms == 0:
            self.metrics.average_latency_ms = latency_ms
        else:
            self.metrics.average_latency_ms = (
                alpha * latency_ms + 
                (1 - alpha) * self.metrics.average_latency_ms
            )
    
    def shutdown(self):
        """Shutdown optimizer."""
        self.batcher.shutdown()
        self.cache.clear()


class StreamOptimizer:
    """Optimizes streaming data transmission."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.chunk_size = 4096  # Default chunk size
        self.buffer = bytearray()
        self.sequence_number = 0
    
    async def stream_data(self, data: bytes) -> AsyncIterator[bytes]:
        """Stream data in optimized chunks."""
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            
            # Add sequence header
            header = struct.pack('!HH', self.sequence_number, len(chunk))
            self.sequence_number = (self.sequence_number + 1) % 65536
            
            yield header + chunk
            
            # Flow control
            await asyncio.sleep(0)  # Yield control
    
    def reassemble_stream(self, chunks: List[bytes]) -> bytes:
        """Reassemble streamed chunks."""
        result = bytearray()
        
        for chunk in chunks:
            if len(chunk) < 4:
                continue
            
            seq_num, length = struct.unpack('!HH', chunk[:4])
            data = chunk[4:4 + length]
            result.extend(data)
        
        return bytes(result)


# Global optimizer instance
_global_optimizer = None
_optimizer_lock = threading.Lock()


def get_optimizer(config: Optional[OptimizationConfig] = None) -> ProtocolOptimizer:
    """Get global protocol optimizer."""
    global _global_optimizer
    with _optimizer_lock:
        if _global_optimizer is None:
            _global_optimizer = ProtocolOptimizer(config)
        return _global_optimizer


def create_optimizer(config: OptimizationConfig) -> ProtocolOptimizer:
    """Create new protocol optimizer."""
    return ProtocolOptimizer(config)


# Optimization presets
def create_voice_optimized_config() -> OptimizationConfig:
    """Create configuration optimized for voice interactions."""
    config = OptimizationConfig()
    config.compression_mode = CompressionMode.NONE  # Low latency
    config.batching_strategy = BatchingStrategy.DISABLED  # Real-time
    config.cache_size = 50  # Small cache for common responses
    config.async_processing = True
    config.pipeline_depth = 3
    return config


def create_high_throughput_config() -> OptimizationConfig:
    """Create configuration for high throughput."""
    config = OptimizationConfig()
    config.compression_mode = CompressionMode.AUTO
    config.batching_strategy = BatchingStrategy.ADAPTIVE
    config.batch_size = 50
    config.connection_pool_size = 20
    config.cache_size = 200
    return config


def create_low_bandwidth_config() -> OptimizationConfig:
    """Create configuration for low bandwidth scenarios."""
    config = OptimizationConfig()
    config.compression_mode = CompressionMode.ZLIB
    config.compression_level = 9  # Maximum compression
    config.batching_strategy = BatchingStrategy.SIZE_BASED
    config.batch_size = 20
    return config