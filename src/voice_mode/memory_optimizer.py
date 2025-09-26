#!/usr/bin/env python3
"""Memory optimization framework for CHATTA voice mode."""

import gc
import weakref
import sys
import tracemalloc
import psutil
import threading
import asyncio
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from collections import deque, OrderedDict
from contextlib import contextmanager
from enum import Enum
import logging
import time
import os

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MemoryProfile(Enum):
    """Memory usage profiles."""
    MINIMAL = "minimal"      # Minimize memory at all costs
    BALANCED = "balanced"    # Balance memory and performance
    PERFORMANCE = "performance"  # Prioritize performance over memory


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    shared_mb: float  # Shared memory
    available_mb: float  # Available system memory
    percent: float  # Memory usage percentage
    python_objects: int  # Number of Python objects
    gc_stats: Dict[str, int]  # Garbage collection stats
    largest_objects: List[Tuple[str, int]]  # Largest objects in memory
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "shared_mb": self.shared_mb,
            "available_mb": self.available_mb,
            "percent": self.percent,
            "python_objects": self.python_objects,
            "gc_stats": self.gc_stats,
            "largest_objects": [
                {"type": t, "size_mb": s / (1024 * 1024)} 
                for t, s in self.largest_objects
            ]
        }


class MemoryPool(Generic[T]):
    """Generic memory pool for object reuse."""
    
    def __init__(self, factory: callable, max_size: int = 100, 
                 reset_func: Optional[callable] = None):
        self.factory = factory
        self.reset_func = reset_func
        self.max_size = max_size
        self._pool: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()
        self._created = 0
        self._reused = 0
    
    def acquire(self) -> T:
        """Acquire an object from the pool."""
        with self._lock:
            if self._pool:
                obj = self._pool.pop()
                self._reused += 1
                if self.reset_func:
                    self.reset_func(obj)
                return obj
            else:
                self._created += 1
                return self.factory()
    
    def release(self, obj: T):
        """Release an object back to the pool."""
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(obj)
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self._pool),
                "max_size": self.max_size,
                "created": self._created,
                "reused": self._reused,
                "reuse_rate": self._reused / max(1, self._created + self._reused)
            }
    
    def clear(self):
        """Clear the pool."""
        with self._lock:
            self._pool.clear()


class BufferManager:
    """Manages audio buffers with memory optimization."""
    
    def __init__(self, profile: MemoryProfile = MemoryProfile.BALANCED):
        self.profile = profile
        self._buffers: Dict[str, np.ndarray] = {}
        self._buffer_pool = MemoryPool(
            factory=lambda: np.zeros(self._get_buffer_size(), dtype=np.int16),
            max_size=10 if profile == MemoryProfile.MINIMAL else 50,
            reset_func=lambda buf: buf.fill(0)
        )
        self._lock = threading.RLock()
    
    def _get_buffer_size(self) -> int:
        """Get buffer size based on profile."""
        if self.profile == MemoryProfile.MINIMAL:
            return 2048
        elif self.profile == MemoryProfile.BALANCED:
            return 4096
        else:  # PERFORMANCE
            return 8192
    
    def allocate_buffer(self, name: str) -> np.ndarray:
        """Allocate a named buffer."""
        with self._lock:
            if name not in self._buffers:
                self._buffers[name] = self._buffer_pool.acquire()
            return self._buffers[name]
    
    def release_buffer(self, name: str):
        """Release a named buffer."""
        with self._lock:
            if name in self._buffers:
                buf = self._buffers.pop(name)
                self._buffer_pool.release(buf)
    
    def get_buffer(self, name: str) -> Optional[np.ndarray]:
        """Get a buffer by name."""
        with self._lock:
            return self._buffers.get(name)
    
    def resize_buffer(self, name: str, size: int):
        """Resize a buffer."""
        with self._lock:
            if name in self._buffers:
                old_buf = self._buffers[name]
                new_buf = np.zeros(size, dtype=np.int16)
                # Copy old data
                copy_size = min(len(old_buf), size)
                new_buf[:copy_size] = old_buf[:copy_size]
                self._buffers[name] = new_buf
                # Don't return old buffer to pool (wrong size)
    
    @property
    def memory_usage(self) -> Dict[str, Any]:
        """Get memory usage of buffers."""
        with self._lock:
            total_size = sum(
                buf.nbytes for buf in self._buffers.values()
            )
            return {
                "buffer_count": len(self._buffers),
                "total_size_mb": total_size / (1024 * 1024),
                "pool_stats": self._buffer_pool.stats
            }
    
    def cleanup(self):
        """Clean up all buffers."""
        with self._lock:
            for name in list(self._buffers.keys()):
                self.release_buffer(name)
            self._buffer_pool.clear()


class CircularBuffer:
    """Memory-efficient circular buffer for audio data."""
    
    def __init__(self, size: int, dtype=np.int16):
        self.size = size
        self.dtype = dtype
        self.buffer = np.zeros(size, dtype=dtype)
        self.write_pos = 0
        self.read_pos = 0
        self.available = 0
        self._lock = threading.RLock()
    
    def write(self, data: np.ndarray) -> int:
        """Write data to buffer. Returns number of samples written."""
        with self._lock:
            data_len = len(data)
            space = self.size - self.available
            
            if space == 0:
                return 0
            
            to_write = min(data_len, space)
            
            # Write in chunks if wrapping
            end_pos = self.write_pos + to_write
            if end_pos <= self.size:
                self.buffer[self.write_pos:end_pos] = data[:to_write]
            else:
                first_chunk = self.size - self.write_pos
                self.buffer[self.write_pos:] = data[:first_chunk]
                self.buffer[:to_write - first_chunk] = data[first_chunk:to_write]
            
            self.write_pos = (self.write_pos + to_write) % self.size
            self.available += to_write
            
            return to_write
    
    def read(self, count: int) -> np.ndarray:
        """Read data from buffer."""
        with self._lock:
            to_read = min(count, self.available)
            
            if to_read == 0:
                return np.array([], dtype=self.dtype)
            
            result = np.zeros(to_read, dtype=self.dtype)
            
            # Read in chunks if wrapping
            end_pos = self.read_pos + to_read
            if end_pos <= self.size:
                result[:] = self.buffer[self.read_pos:end_pos]
            else:
                first_chunk = self.size - self.read_pos
                result[:first_chunk] = self.buffer[self.read_pos:]
                result[first_chunk:] = self.buffer[:to_read - first_chunk]
            
            self.read_pos = (self.read_pos + to_read) % self.size
            self.available -= to_read
            
            return result
    
    def clear(self):
        """Clear the buffer."""
        with self._lock:
            self.write_pos = 0
            self.read_pos = 0
            self.available = 0
            self.buffer.fill(0)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        with self._lock:
            return {
                "size": self.size,
                "available": self.available,
                "used_percent": (self.available / self.size) * 100,
                "memory_mb": self.buffer.nbytes / (1024 * 1024)
            }


class WeakCache:
    """Cache using weak references for automatic cleanup."""
    
    def __init__(self, max_strong_refs: int = 10):
        self._weak_cache: Dict[Any, weakref.ref] = {}
        self._strong_cache: OrderedDict = OrderedDict()
        self._max_strong = max_strong_refs
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def put(self, key: Any, value: Any):
        """Store a value with weak reference."""
        with self._lock:
            # Keep strong reference for recently used items
            self._strong_cache[key] = value
            if len(self._strong_cache) > self._max_strong:
                # Move oldest to weak-only
                old_key, _ = self._strong_cache.popitem(last=False)
            
            # Try to keep weak reference if possible
            try:
                self._weak_cache[key] = weakref.ref(value)
            except TypeError:
                # Can't create weak ref for primitive types (str, int, etc.)
                # Just keep in strong cache
                pass
    
    def get(self, key: Any) -> Optional[Any]:
        """Get a value from cache."""
        with self._lock:
            # Check strong cache first
            if key in self._strong_cache:
                self._hits += 1
                # Move to end (most recent)
                self._strong_cache.move_to_end(key)
                return self._strong_cache[key]
            
            # Check weak cache
            if key in self._weak_cache:
                ref = self._weak_cache[key]
                value = ref()
                if value is not None:
                    self._hits += 1
                    # Promote to strong cache
                    self._strong_cache[key] = value
                    if len(self._strong_cache) > self._max_strong:
                        self._strong_cache.popitem(last=False)
                    return value
                else:
                    # Weak reference died
                    del self._weak_cache[key]
            
            self._misses += 1
            return None
    
    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._weak_cache.clear()
            self._strong_cache.clear()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "strong_refs": len(self._strong_cache),
                "weak_refs": len(self._weak_cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / max(1, total)
            }


class MemoryMonitor:
    """Monitor and track memory usage."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self._baseline: Optional[MemoryStats] = None
        self._snapshots: deque = deque(maxlen=100)
        self._tracemalloc_started = False
    
    def start_tracking(self):
        """Start memory tracking."""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._tracemalloc_started = True
        self._baseline = self.get_current_stats()
    
    def stop_tracking(self) -> Dict[str, Any]:
        """Stop tracking and get summary."""
        current = self.get_current_stats()
        
        if self._tracemalloc_started:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            tracemalloc.stop()
            self._tracemalloc_started = False
        else:
            top_stats = []
        
        summary = {
            "baseline": self._baseline.to_dict() if self._baseline else None,
            "current": current.to_dict(),
            "delta_mb": current.rss_mb - (self._baseline.rss_mb if self._baseline else 0),
            "top_allocations": [
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size / (1024 * 1024),
                    "count": stat.count
                }
                for stat in top_stats[:10]
            ]
        }
        
        return summary
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        mem_info = self.process.memory_info()
        sys_mem = psutil.virtual_memory()
        
        # Get GC stats
        gc_stats = {
            f"gen{i}_objects": len(gc.get_objects(i))
            for i in range(gc.get_count().__len__())
        }
        gc_stats["total_objects"] = len(gc.get_objects())
        
        # Get largest objects (simplified)
        largest = []
        if self._tracemalloc_started and tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            for stat in snapshot.statistics('traceback')[:5]:
                largest.append((str(stat.traceback), stat.size))
        
        return MemoryStats(
            rss_mb=mem_info.rss / (1024 * 1024),
            vms_mb=mem_info.vms / (1024 * 1024),
            shared_mb=getattr(mem_info, 'shared', 0) / (1024 * 1024),
            available_mb=sys_mem.available / (1024 * 1024),
            percent=self.process.memory_percent(),
            python_objects=len(gc.get_objects()),
            gc_stats=gc_stats,
            largest_objects=largest
        )
    
    def take_snapshot(self) -> MemoryStats:
        """Take a memory snapshot."""
        stats = self.get_current_stats()
        self._snapshots.append((time.time(), stats))
        return stats
    
    def get_trend(self) -> Dict[str, Any]:
        """Get memory usage trend."""
        if len(self._snapshots) < 2:
            return {"status": "insufficient_data"}
        
        times = [s[0] for s in self._snapshots]
        rss_values = [s[1].rss_mb for s in self._snapshots]
        
        # Simple linear regression for trend
        n = len(times)
        if n > 1:
            x_mean = sum(times) / n
            y_mean = sum(rss_values) / n
            
            numerator = sum((x - x_mean) * (y - y_mean) 
                          for x, y in zip(times, rss_values))
            denominator = sum((x - x_mean) ** 2 for x in times)
            
            if denominator > 0:
                slope = numerator / denominator
                trend = "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable"
            else:
                trend = "stable"
        else:
            trend = "unknown"
        
        return {
            "trend": trend,
            "samples": n,
            "current_mb": rss_values[-1] if rss_values else 0,
            "min_mb": min(rss_values) if rss_values else 0,
            "max_mb": max(rss_values) if rss_values else 0,
            "avg_mb": sum(rss_values) / n if n > 0 else 0
        }


class MemoryOptimizer:
    """Main memory optimization coordinator."""
    
    def __init__(self, profile: MemoryProfile = MemoryProfile.BALANCED):
        self.profile = profile
        self.buffer_manager = BufferManager(profile)
        self.monitor = MemoryMonitor()
        self._pools: Dict[str, MemoryPool] = {}
        self._caches: Dict[str, WeakCache] = {}
        self._gc_threshold = self._get_gc_threshold()
        self._configure_gc()
    
    def _get_gc_threshold(self) -> int:
        """Get GC threshold based on profile."""
        if self.profile == MemoryProfile.MINIMAL:
            return 100  # Aggressive GC
        elif self.profile == MemoryProfile.BALANCED:
            return 700  # Default
        else:  # PERFORMANCE
            return 2000  # Less frequent GC
    
    def _configure_gc(self):
        """Configure garbage collection."""
        # Set thresholds for each generation
        if self.profile == MemoryProfile.MINIMAL:
            gc.set_threshold(100, 10, 10)
        elif self.profile == MemoryProfile.BALANCED:
            gc.set_threshold(700, 10, 10)
        else:  # PERFORMANCE
            gc.set_threshold(2000, 20, 20)
    
    def create_pool(self, name: str, factory: callable, 
                   max_size: Optional[int] = None) -> MemoryPool:
        """Create a named memory pool."""
        if max_size is None:
            max_size = 10 if self.profile == MemoryProfile.MINIMAL else 100
        
        pool = MemoryPool(factory, max_size)
        self._pools[name] = pool
        return pool
    
    def get_pool(self, name: str) -> Optional[MemoryPool]:
        """Get a pool by name."""
        return self._pools.get(name)
    
    def create_cache(self, name: str, max_strong_refs: Optional[int] = None) -> WeakCache:
        """Create a named weak cache."""
        if max_strong_refs is None:
            max_strong_refs = 5 if self.profile == MemoryProfile.MINIMAL else 20
        
        cache = WeakCache(max_strong_refs)
        self._caches[name] = cache
        return cache
    
    def get_cache(self, name: str) -> Optional[WeakCache]:
        """Get a cache by name."""
        return self._caches.get(name)
    
    def optimize_memory(self):
        """Run memory optimization."""
        # Force garbage collection
        gc.collect()
        
        # Trim pools if needed
        if self.profile == MemoryProfile.MINIMAL:
            for pool in self._pools.values():
                pool.clear()
        
        # Clear weak references
        for cache in self._caches.values():
            # This doesn't clear, just triggers cleanup of dead refs
            _ = cache.stats
    
    @contextmanager
    def memory_limit(self, max_mb: int):
        """Context manager to limit memory usage."""
        import resource
        
        if sys.platform != 'win32':
            # Get current limits
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            
            # Set new limit
            max_bytes = max_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_bytes, hard))
            
            try:
                yield
            finally:
                # Restore original limits
                resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
        else:
            # Windows doesn't support resource limits
            yield
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get memory optimization suggestions."""
        suggestions = []
        stats = self.monitor.get_current_stats()
        
        # Check memory usage
        if stats.percent > 80:
            suggestions.append("Critical: Memory usage above 80%")
            suggestions.append("Consider switching to MINIMAL profile")
        elif stats.percent > 60:
            suggestions.append("Warning: Memory usage above 60%")
        
        # Check pool efficiency
        for name, pool in self._pools.items():
            pool_stats = pool.stats
            if pool_stats["reuse_rate"] < 0.5:
                suggestions.append(f"Pool '{name}' has low reuse rate")
        
        # Check cache efficiency
        for name, cache in self._caches.items():
            cache_stats = cache.stats
            if cache_stats["hit_rate"] < 0.3:
                suggestions.append(f"Cache '{name}' has low hit rate")
        
        # Check GC pressure
        if stats.gc_stats.get("total_objects", 0) > 100000:
            suggestions.append("High object count - consider more aggressive GC")
        
        return suggestions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return {
            "profile": self.profile.value,
            "memory": self.monitor.get_current_stats().to_dict(),
            "buffers": self.buffer_manager.memory_usage,
            "pools": {
                name: pool.stats for name, pool in self._pools.items()
            },
            "caches": {
                name: cache.stats for name, cache in self._caches.items()
            },
            "suggestions": self.get_optimization_suggestions()
        }
    
    def cleanup(self):
        """Clean up all resources."""
        self.buffer_manager.cleanup()
        for pool in self._pools.values():
            pool.clear()
        for cache in self._caches.values():
            cache.clear()
        gc.collect()


# Global optimizer instance
_global_optimizer: Optional[MemoryOptimizer] = None


def get_memory_optimizer(profile: Optional[MemoryProfile] = None) -> MemoryOptimizer:
    """Get or create global memory optimizer."""
    global _global_optimizer
    
    if _global_optimizer is None or (profile and _global_optimizer.profile != profile):
        _global_optimizer = MemoryOptimizer(profile or MemoryProfile.BALANCED)
    
    return _global_optimizer


def set_memory_profile(profile: MemoryProfile):
    """Set global memory profile."""
    global _global_optimizer
    _global_optimizer = MemoryOptimizer(profile)