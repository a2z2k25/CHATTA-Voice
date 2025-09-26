#!/usr/bin/env python3
"""Latency reduction framework for voice mode."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import threading
import numpy as np
import logging

logger = logging.getLogger(__name__)


class LatencyMode(Enum):
    """Latency optimization modes."""
    ULTRA_LOW = "ultra_low"      # <100ms target
    LOW = "low"                   # <200ms target  
    BALANCED = "balanced"         # <500ms target
    RELAXED = "relaxed"          # <1000ms target


@dataclass
class LatencyMetrics:
    """Metrics for latency tracking."""
    component: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self):
        """Mark operation as complete."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        return self.duration_ms


class LatencyTracker:
    """Tracks latency across components."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._lock = threading.RLock()
        self._targets = {
            "stt": 500,    # Speech-to-text
            "tts": 200,    # Text-to-speech
            "vad": 50,     # Voice activity detection
            "llm": 1000,   # LLM response
            "total": 2000  # End-to-end
        }
    
    def start_operation(self, component: str) -> LatencyMetrics:
        """Start tracking an operation."""
        return LatencyMetrics(
            component=component,
            start_time=time.perf_counter()
        )
    
    def complete_operation(self, metrics: LatencyMetrics):
        """Complete tracking an operation."""
        metrics.complete()
        with self._lock:
            self._metrics[metrics.component].append(metrics)
    
    def get_stats(self, component: str) -> Dict[str, float]:
        """Get statistics for a component."""
        with self._lock:
            if component not in self._metrics or not self._metrics[component]:
                return {"count": 0}
            
            durations = [m.duration_ms for m in self._metrics[component] if m.duration_ms]
            if not durations:
                return {"count": 0}
            
            return {
                "count": len(durations),
                "mean": np.mean(durations),
                "median": np.median(durations),
                "p95": np.percentile(durations, 95),
                "p99": np.percentile(durations, 99),
                "min": np.min(durations),
                "max": np.max(durations),
                "target": self._targets.get(component, 1000),
                "within_target": sum(1 for d in durations if d <= self._targets.get(component, 1000)) / len(durations)
            }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all components."""
        with self._lock:
            return {
                component: self.get_stats(component)
                for component in set(list(self._metrics.keys()) + list(self._targets.keys()))
            }
    
    def is_meeting_targets(self) -> bool:
        """Check if all components are meeting targets."""
        stats = self.get_all_stats()
        for component, target in self._targets.items():
            if component in stats and stats[component].get("count", 0) > 0:
                if stats[component].get("p95", float('inf')) > target:
                    return False
        return True


class PipelineOptimizer:
    """Optimizes async pipeline execution."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.mode = mode
        self._pipelines: Dict[str, List[Callable]] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def register_pipeline(self, name: str, stages: List[Callable]):
        """Register a processing pipeline."""
        self._pipelines[name] = stages
    
    async def execute_pipeline(self, name: str, data: Any, 
                              parallel: bool = False) -> Any:
        """Execute a pipeline with optimization."""
        if name not in self._pipelines:
            raise ValueError(f"Pipeline '{name}' not registered")
        
        stages = self._pipelines[name]
        
        if parallel and len(stages) > 1:
            # Execute independent stages in parallel
            return await self._execute_parallel(stages, data)
        else:
            # Execute stages sequentially
            return await self._execute_sequential(stages, data)
    
    async def _execute_sequential(self, stages: List[Callable], data: Any) -> Any:
        """Execute stages sequentially."""
        result = data
        for stage in stages:
            if asyncio.iscoroutinefunction(stage):
                result = await stage(result)
            else:
                result = stage(result)
        return result
    
    async def _execute_parallel(self, stages: List[Callable], data: Any) -> Any:
        """Execute independent stages in parallel."""
        # Identify dependencies and parallelize where possible
        tasks = []
        for stage in stages:
            if asyncio.iscoroutinefunction(stage):
                tasks.append(asyncio.create_task(stage(data)))
            else:
                # Run sync functions in executor
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, stage, data))
        
        results = await asyncio.gather(*tasks)
        # Merge results (simplified - real implementation would be more complex)
        return results[-1] if results else data
    
    def cache_result(self, key: str, value: Any, ttl: int = 60):
        """Cache a result with TTL."""
        self._cache[key] = {
            "value": value,
            "expires": time.time() + ttl
        }
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached result if valid."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires"]:
                self._cache_hits += 1
                return entry["value"]
            else:
                del self._cache[key]
        
        self._cache_misses += 1
        return None
    
    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / max(1, total)


class PredictiveBuffer:
    """Predictive buffering for reduced latency."""
    
    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self._predictions: deque = deque(maxlen=capacity)
        self._prefetch_queue: asyncio.Queue = asyncio.Queue(maxsize=capacity)
        self._prefetch_task: Optional[asyncio.Task] = None
        self._predictor: Optional[Callable] = None
        self._hit_count = 0
        self._miss_count = 0
    
    def set_predictor(self, predictor: Callable):
        """Set prediction function."""
        self._predictor = predictor
    
    async def start_prefetching(self):
        """Start prefetch task."""
        if self._prefetch_task is None:
            self._prefetch_task = asyncio.create_task(self._prefetch_loop())
    
    async def stop_prefetching(self):
        """Stop prefetch task."""
        if self._prefetch_task:
            self._prefetch_task.cancel()
            try:
                await self._prefetch_task
            except asyncio.CancelledError:
                pass
            self._prefetch_task = None
    
    async def _prefetch_loop(self):
        """Continuous prefetching loop."""
        while True:
            try:
                if self._predictor and not self._prefetch_queue.full():
                    # Generate prediction
                    prediction = await self._predictor()
                    if prediction:
                        await self._prefetch_queue.put(prediction)
                
                await asyncio.sleep(0.1)  # Adjust based on mode
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Prefetch error: {e}")
                await asyncio.sleep(1)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get predicted value if available."""
        try:
            # Check if we have a prediction
            if not self._prefetch_queue.empty():
                item = await self._prefetch_queue.get()
                if isinstance(item, dict) and item.get("key") == key:
                    self._hit_count += 1
                    return item.get("value")
                else:
                    # Put it back if not matching
                    await self._prefetch_queue.put(item)
        except:
            pass
        
        self._miss_count += 1
        return None
    
    @property
    def hit_rate(self) -> float:
        """Get prediction hit rate."""
        total = self._hit_count + self._miss_count
        return self._hit_count / max(1, total)


class StreamOptimizer:
    """Optimizes streaming operations."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.mode = mode
        self._chunk_sizes = {
            LatencyMode.ULTRA_LOW: 512,
            LatencyMode.LOW: 1024,
            LatencyMode.BALANCED: 2048,
            LatencyMode.RELAXED: 4096
        }
        self._buffer_sizes = {
            LatencyMode.ULTRA_LOW: 2048,
            LatencyMode.LOW: 4096,
            LatencyMode.BALANCED: 8192,
            LatencyMode.RELAXED: 16384
        }
    
    @property
    def chunk_size(self) -> int:
        """Get optimal chunk size."""
        return self._chunk_sizes.get(self.mode, 2048)
    
    @property
    def buffer_size(self) -> int:
        """Get optimal buffer size."""
        return self._buffer_sizes.get(self.mode, 8192)
    
    async def stream_with_optimization(self, source, processor, sink):
        """Stream data with latency optimization."""
        buffer = []
        buffer_size = 0
        
        async for chunk in source:
            buffer.append(chunk)
            buffer_size += len(chunk) if hasattr(chunk, '__len__') else 1
            
            # Process when buffer reaches optimal size
            if buffer_size >= self.chunk_size:
                processed = await processor(buffer)
                await sink(processed)
                buffer = []
                buffer_size = 0
        
        # Process remaining
        if buffer:
            processed = await processor(buffer)
            await sink(processed)


class ConnectionPoolManager:
    """Manages connection pools for reduced latency."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.mode = mode
        self._pools: Dict[str, List[Any]] = {}
        self._pool_sizes = {
            LatencyMode.ULTRA_LOW: 10,
            LatencyMode.LOW: 5,
            LatencyMode.BALANCED: 3,
            LatencyMode.RELAXED: 2
        }
        self._lock = threading.RLock()
    
    def create_pool(self, name: str, factory: Callable, size: Optional[int] = None):
        """Create a connection pool."""
        pool_size = size or self._pool_sizes.get(self.mode, 3)
        
        with self._lock:
            self._pools[name] = []
            for _ in range(pool_size):
                conn = factory()
                self._pools[name].append({
                    "conn": conn,
                    "in_use": False,
                    "created": time.time()
                })
    
    def acquire(self, name: str, timeout: float = 5.0) -> Optional[Any]:
        """Acquire connection from pool."""
        start = time.time()
        
        while time.time() - start < timeout:
            with self._lock:
                if name in self._pools:
                    for item in self._pools[name]:
                        if not item["in_use"]:
                            item["in_use"] = True
                            return item["conn"]
            
            time.sleep(0.01)
        
        return None
    
    def release(self, name: str, conn: Any):
        """Release connection back to pool."""
        with self._lock:
            if name in self._pools:
                for item in self._pools[name]:
                    if item["conn"] is conn:
                        item["in_use"] = False
                        break


class LatencyReducer:
    """Main latency reduction coordinator."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.mode = mode
        self.tracker = LatencyTracker()
        self.pipeline_optimizer = PipelineOptimizer(mode)
        self.predictive_buffer = PredictiveBuffer()
        self.stream_optimizer = StreamOptimizer(mode)
        self.connection_pool = ConnectionPoolManager(mode)
        
        # Configure based on mode
        self._configure_for_mode()
    
    def _configure_for_mode(self):
        """Configure components based on latency mode."""
        if self.mode == LatencyMode.ULTRA_LOW:
            # Ultra-low latency configuration
            self.tracker._targets = {
                "stt": 200,
                "tts": 100,
                "vad": 20,
                "llm": 500,
                "total": 1000
            }
        elif self.mode == LatencyMode.LOW:
            # Low latency configuration
            self.tracker._targets = {
                "stt": 300,
                "tts": 150,
                "vad": 30,
                "llm": 750,
                "total": 1500
            }
    
    def track(self, component: str) -> LatencyMetrics:
        """Start tracking latency for a component."""
        return self.tracker.start_operation(component)
    
    def complete(self, metrics: LatencyMetrics):
        """Complete latency tracking."""
        self.tracker.complete_operation(metrics)
    
    async def optimize_stt(self, audio_data: bytes) -> str:
        """Optimize speech-to-text with latency reduction."""
        metrics = self.track("stt")
        
        try:
            # Check predictive buffer
            predicted = await self.predictive_buffer.get(str(hash(audio_data)))
            if predicted:
                return predicted
            
            # Process with optimization
            # (Simplified - would call actual STT)
            result = "transcribed text"
            
            # Cache for future
            self.pipeline_optimizer.cache_result(
                str(hash(audio_data)), 
                result,
                ttl=30
            )
            
            return result
            
        finally:
            self.complete(metrics)
    
    async def optimize_tts(self, text: str) -> bytes:
        """Optimize text-to-speech with latency reduction."""
        metrics = self.track("tts")
        
        try:
            # Check cache
            cached = self.pipeline_optimizer.get_cached(text)
            if cached:
                return cached
            
            # Process with optimization
            # (Simplified - would call actual TTS)
            result = b"audio_data"
            
            # Cache result
            self.pipeline_optimizer.cache_result(text, result, ttl=60)
            
            return result
            
        finally:
            self.complete(metrics)
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get suggestions for latency optimization."""
        suggestions = []
        stats = self.tracker.get_all_stats()
        
        for component, data in stats.items():
            if data.get("count", 0) > 0:
                p95 = data.get("p95", 0)
                target = data.get("target", 1000)
                
                if p95 > target * 1.5:
                    suggestions.append(
                        f"{component}: P95 latency ({p95:.1f}ms) exceeds target ({target}ms) by >50%"
                    )
                elif p95 > target:
                    suggestions.append(
                        f"{component}: P95 latency ({p95:.1f}ms) exceeds target ({target}ms)"
                    )
        
        # Check cache performance
        if self.pipeline_optimizer.cache_hit_rate < 0.3:
            suggestions.append("Cache hit rate is low - consider increasing cache size")
        
        # Check prediction performance
        if self.predictive_buffer.hit_rate < 0.2:
            suggestions.append("Prediction hit rate is low - consider improving predictor")
        
        return suggestions
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            "mode": self.mode.value,
            "latency_stats": self.tracker.get_all_stats(),
            "meeting_targets": self.tracker.is_meeting_targets(),
            "cache_hit_rate": self.pipeline_optimizer.cache_hit_rate,
            "prediction_hit_rate": self.predictive_buffer.hit_rate,
            "suggestions": self.get_optimization_suggestions()
        }


# Global instance
_global_reducer: Optional[LatencyReducer] = None


def get_latency_reducer(mode: LatencyMode = LatencyMode.BALANCED) -> LatencyReducer:
    """Get global latency reducer instance."""
    global _global_reducer
    if _global_reducer is None or _global_reducer.mode != mode:
        _global_reducer = LatencyReducer(mode)
    return _global_reducer


def set_latency_mode(mode: LatencyMode):
    """Set global latency mode."""
    global _global_reducer
    _global_reducer = LatencyReducer(mode)