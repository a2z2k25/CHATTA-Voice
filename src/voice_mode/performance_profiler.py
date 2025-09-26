#!/usr/bin/env python3
"""Performance profiling and optimization framework for CHATTA voice mode."""

import time
import cProfile
import pstats
import io
import functools
import contextlib
import threading
import gc
import tracemalloc
import psutil
import os
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import statistics
import weakref


class ProfileMode(Enum):
    """Profiling modes."""
    DISABLED = "disabled"
    BASIC = "basic"        # Time only
    DETAILED = "detailed"  # Time + memory
    FULL = "full"         # Time + memory + CPU + I/O


class OptimizationLevel(Enum):
    """Optimization levels."""
    NONE = 0
    BASIC = 1      # Simple optimizations
    MODERATE = 2   # Balance performance/quality
    AGGRESSIVE = 3  # Maximum performance


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    name: str
    start_time: float = 0
    end_time: float = 0
    duration: float = 0
    memory_start: int = 0
    memory_end: int = 0
    memory_delta: int = 0
    cpu_percent: float = 0
    io_reads: int = 0
    io_writes: int = 0
    call_count: int = 0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": self.duration * 1000,
            "memory_delta_mb": self.memory_delta / (1024 * 1024),
            "cpu_percent": self.cpu_percent,
            "io_reads": self.io_reads,
            "io_writes": self.io_writes,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            "custom": self.custom_metrics
        }


@dataclass
class PerformanceReport:
    """Performance analysis report."""
    total_duration: float
    total_memory: int
    avg_cpu: float
    hotspots: List[Tuple[str, float]]  # (function, time)
    bottlenecks: List[str]
    recommendations: List[str]
    metrics_by_function: Dict[str, PerformanceMetrics]
    
    def to_json(self) -> str:
        """Export report as JSON."""
        return json.dumps({
            "total_duration_ms": self.total_duration * 1000,
            "total_memory_mb": self.total_memory / (1024 * 1024),
            "avg_cpu_percent": self.avg_cpu,
            "hotspots": [{"function": f, "time_ms": t * 1000} for f, t in self.hotspots],
            "bottlenecks": self.bottlenecks,
            "recommendations": self.recommendations,
            "metrics": {k: v.to_dict() for k, v in self.metrics_by_function.items()}
        }, indent=2)


class PerformanceProfiler:
    """Main performance profiling system."""
    
    def __init__(self, mode: ProfileMode = ProfileMode.BASIC):
        self.mode = mode
        self.metrics: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        self.active_profiles: Dict[int, PerformanceMetrics] = {}
        self.cprofile = None
        self.memory_tracker = None
        self.process = psutil.Process(os.getpid())
        self._lock = threading.RLock()
        
    def profile(self, name: str = None):
        """Decorator for profiling functions."""
        def decorator(func: Callable) -> Callable:
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if self.mode == ProfileMode.DISABLED:
                    return func(*args, **kwargs)
                
                with self.profile_context(profile_name):
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    @contextlib.contextmanager
    def profile_context(self, name: str):
        """Context manager for profiling code blocks."""
        if self.mode == ProfileMode.DISABLED:
            yield
            return
        
        metrics = PerformanceMetrics(name=name)
        thread_id = threading.get_ident()
        
        # Start profiling
        with self._lock:
            self.active_profiles[thread_id] = metrics
            metrics.start_time = time.perf_counter()
            
            if self.mode in [ProfileMode.DETAILED, ProfileMode.FULL]:
                metrics.memory_start = self.process.memory_info().rss
            
            if self.mode == ProfileMode.FULL:
                io_start = self.process.io_counters()
        
        try:
            yield metrics
            
        except Exception as e:
            metrics.error_count += 1
            raise
            
        finally:
            # End profiling
            metrics.end_time = time.perf_counter()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.call_count += 1
            
            if self.mode in [ProfileMode.DETAILED, ProfileMode.FULL]:
                metrics.memory_end = self.process.memory_info().rss
                metrics.memory_delta = metrics.memory_end - metrics.memory_start
            
            if self.mode == ProfileMode.FULL:
                metrics.cpu_percent = self.process.cpu_percent()
                io_end = self.process.io_counters()
                metrics.io_reads = io_end.read_count - io_start.read_count
                metrics.io_writes = io_end.write_count - io_start.write_count
            
            with self._lock:
                del self.active_profiles[thread_id]
                self.metrics[name].append(metrics)
    
    def start_profiling(self):
        """Start detailed profiling."""
        if self.mode == ProfileMode.FULL:
            self.cprofile = cProfile.Profile()
            self.cprofile.enable()
            
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                self.memory_tracker = True
    
    def stop_profiling(self) -> PerformanceReport:
        """Stop profiling and generate report."""
        if self.cprofile:
            self.cprofile.disable()
        
        if self.memory_tracker:
            snapshot = tracemalloc.take_snapshot()
            tracemalloc.stop()
        
        return self.generate_report()
    
    def generate_report(self) -> PerformanceReport:
        """Generate performance analysis report."""
        all_metrics = []
        metrics_by_function = {}
        
        # Aggregate metrics
        for name, metrics_list in self.metrics.items():
            if metrics_list:
                combined = PerformanceMetrics(name=name)
                combined.duration = sum(m.duration for m in metrics_list)
                combined.memory_delta = sum(m.memory_delta for m in metrics_list)
                combined.call_count = sum(m.call_count for m in metrics_list)
                combined.error_count = sum(m.error_count for m in metrics_list)
                combined.cache_hits = sum(m.cache_hits for m in metrics_list)
                combined.cache_misses = sum(m.cache_misses for m in metrics_list)
                
                if any(m.cpu_percent for m in metrics_list):
                    combined.cpu_percent = statistics.mean(
                        m.cpu_percent for m in metrics_list if m.cpu_percent
                    )
                
                metrics_by_function[name] = combined
                all_metrics.extend(metrics_list)
        
        # Calculate totals
        total_duration = sum(m.duration for m in all_metrics)
        total_memory = sum(abs(m.memory_delta) for m in all_metrics)
        avg_cpu = statistics.mean(
            m.cpu_percent for m in all_metrics if m.cpu_percent
        ) if any(m.cpu_percent for m in all_metrics) else 0
        
        # Find hotspots
        hotspots = sorted(
            [(name, m.duration) for name, m in metrics_by_function.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(metrics_by_function)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            metrics_by_function, bottlenecks
        )
        
        return PerformanceReport(
            total_duration=total_duration,
            total_memory=total_memory,
            avg_cpu=avg_cpu,
            hotspots=hotspots,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            metrics_by_function=metrics_by_function
        )
    
    def _identify_bottlenecks(self, metrics: Dict[str, PerformanceMetrics]) -> List[str]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        
        for name, m in metrics.items():
            # High duration
            if m.duration > 1.0:  # More than 1 second
                bottlenecks.append(f"{name}: Long execution time ({m.duration:.2f}s)")
            
            # High memory usage
            if m.memory_delta > 100 * 1024 * 1024:  # More than 100MB
                mb = m.memory_delta / (1024 * 1024)
                bottlenecks.append(f"{name}: High memory usage ({mb:.1f}MB)")
            
            # Poor cache performance
            if m.cache_misses > m.cache_hits * 2:  # Less than 33% hit rate
                rate = m.cache_hits / max(1, m.cache_hits + m.cache_misses)
                bottlenecks.append(f"{name}: Poor cache hit rate ({rate:.1%})")
            
            # High error rate
            if m.error_count > m.call_count * 0.1:  # More than 10% errors
                rate = m.error_count / max(1, m.call_count)
                bottlenecks.append(f"{name}: High error rate ({rate:.1%})")
        
        return bottlenecks
    
    def _generate_recommendations(
        self,
        metrics: Dict[str, PerformanceMetrics],
        bottlenecks: List[str]
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Analyze patterns
        total_time = sum(m.duration for m in metrics.values())
        
        for name, m in metrics.items():
            time_percent = (m.duration / max(0.001, total_time)) * 100
            
            if time_percent > 20:
                recommendations.append(
                    f"Optimize {name} - consuming {time_percent:.1f}% of total time"
                )
            
            if m.call_count > 1000:
                recommendations.append(
                    f"Consider caching {name} - called {m.call_count} times"
                )
            
            if m.memory_delta > 50 * 1024 * 1024:
                recommendations.append(
                    f"Reduce memory allocation in {name}"
                )
        
        # General recommendations based on bottlenecks
        if any("cache hit rate" in b for b in bottlenecks):
            recommendations.append("Improve caching strategy")
        
        if any("memory usage" in b for b in bottlenecks):
            recommendations.append("Implement memory pooling or streaming")
        
        if any("execution time" in b for b in bottlenecks):
            recommendations.append("Consider async/parallel processing")
        
        return recommendations
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics.clear()
            self.active_profiles.clear()


class PerformanceOptimizer:
    """Performance optimization strategies."""
    
    def __init__(self, level: OptimizationLevel = OptimizationLevel.MODERATE):
        self.level = level
        self._cache = {}
        self._cache_size = 1000 if level.value >= OptimizationLevel.MODERATE.value else 100
        self._pool = {}
        
    def memoize(self, maxsize: int = None):
        """Memoization decorator with size limit."""
        if self.level == OptimizationLevel.NONE:
            return lambda func: func
        
        cache_size = maxsize or self._cache_size
        
        def decorator(func: Callable) -> Callable:
            cache = {}
            cache_queue = deque(maxlen=cache_size)
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Create cache key
                key = (args, tuple(sorted(kwargs.items())))
                
                if key in cache:
                    return cache[key]
                
                result = func(*args, **kwargs)
                
                # Update cache
                if len(cache) >= cache_size:
                    # Remove oldest
                    if cache_queue:
                        old_key = cache_queue.popleft()
                        cache.pop(old_key, None)
                
                cache[key] = result
                cache_queue.append(key)
                
                return result
            
            wrapper.cache_clear = lambda: cache.clear()
            return wrapper
        
        return decorator
    
    def batch_processor(self, batch_size: int = None):
        """Batch processing decorator."""
        if self.level.value < OptimizationLevel.MODERATE.value:
            return lambda func: func
        
        size = batch_size or (50 if self.level == OptimizationLevel.AGGRESSIVE else 20)
        
        def decorator(func: Callable) -> Callable:
            batch_queue = []
            
            @functools.wraps(func)
            def wrapper(item):
                batch_queue.append(item)
                
                if len(batch_queue) >= size:
                    # Process batch
                    results = [func(i) for i in batch_queue]
                    batch_queue.clear()
                    return results[-1]
                
                return None
            
            wrapper.flush = lambda: [func(i) for i in batch_queue]
            return wrapper
        
        return decorator
    
    def lazy_property(self, func: Callable) -> property:
        """Lazy evaluation property decorator."""
        if self.level == OptimizationLevel.NONE:
            return property(func)
        
        attr_name = f'_lazy_{func.__name__}'
        
        @property
        @functools.wraps(func)
        def wrapper(self):
            if not hasattr(self, attr_name):
                setattr(self, attr_name, func(self))
            return getattr(self, attr_name)
        
        return wrapper
    
    def resource_pool(self, factory: Callable, max_size: int = 10):
        """Resource pooling context manager."""
        if self.level.value < OptimizationLevel.MODERATE.value:
            @contextlib.contextmanager
            def simple_manager():
                resource = factory()
                try:
                    yield resource
                finally:
                    if hasattr(resource, 'close'):
                        resource.close()
            return simple_manager
        
        pool = deque(maxlen=max_size)
        lock = threading.Lock()
        
        @contextlib.contextmanager
        def pool_manager():
            resource = None
            
            with lock:
                if pool:
                    resource = pool.pop()
            
            if resource is None:
                resource = factory()
            
            try:
                yield resource
            finally:
                with lock:
                    if len(pool) < max_size:
                        pool.append(resource)
                    elif hasattr(resource, 'close'):
                        resource.close()
        
        return pool_manager
    
    def optimize_audio_pipeline(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize audio processing pipeline configuration."""
        optimized = config.copy()
        
        if self.level.value >= OptimizationLevel.BASIC.value:
            # Reduce buffer sizes for lower latency
            optimized["chunk_size"] = 2048 if self.level == OptimizationLevel.AGGRESSIVE else 4096
            optimized["buffer_size"] = 8192 if self.level == OptimizationLevel.AGGRESSIVE else 16384
        
        if self.level.value >= OptimizationLevel.MODERATE.value:
            # Enable audio preprocessing
            optimized["preprocessing"] = {
                "noise_reduction": True,
                "echo_cancellation": True,
                "gain_control": True
            }
            
            # Optimize VAD settings
            optimized["vad"] = {
                "aggressiveness": 2 if self.level == OptimizationLevel.AGGRESSIVE else 1,
                "frame_duration": 10 if self.level == OptimizationLevel.AGGRESSIVE else 20
            }
        
        if self.level == OptimizationLevel.AGGRESSIVE:
            # Maximum performance settings
            optimized["sample_rate"] = 16000  # Lower sample rate
            optimized["channels"] = 1  # Mono
            optimized["compression"] = "opus"  # Efficient codec
            optimized["parallel_processing"] = True
            optimized["gpu_acceleration"] = True
        
        return optimized


class MemoryOptimizer:
    """Memory optimization utilities."""
    
    @staticmethod
    def optimize_memory():
        """Run memory optimization."""
        # Force garbage collection
        gc.collect()
        
        # Trim memory pools
        if hasattr(gc, 'freeze'):
            gc.freeze()
            gc.collect()
            gc.unfreeze()
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics."""
        process = psutil.Process()
        info = process.memory_info()
        
        return {
            "rss_mb": info.rss / (1024 * 1024),
            "vms_mb": info.vms / (1024 * 1024),
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024)
        }
    
    @staticmethod
    @contextlib.contextmanager
    def memory_limit(max_mb: int):
        """Context manager to limit memory usage."""
        import resource
        
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


# Global profiler instance
_global_profiler = PerformanceProfiler(ProfileMode.BASIC)
_global_optimizer = PerformanceOptimizer(OptimizationLevel.MODERATE)


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance."""
    return _global_profiler


def get_optimizer() -> PerformanceOptimizer:
    """Get global optimizer instance."""
    return _global_optimizer


def set_profile_mode(mode: ProfileMode):
    """Set global profiling mode."""
    global _global_profiler
    _global_profiler.mode = mode


def set_optimization_level(level: OptimizationLevel):
    """Set global optimization level."""
    global _global_optimizer
    _global_optimizer.level = level


# Convenience decorators
profile = _global_profiler.profile
memoize = _global_optimizer.memoize
batch_processor = _global_optimizer.batch_processor
lazy_property = _global_optimizer.lazy_property