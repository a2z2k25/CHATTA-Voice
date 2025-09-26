#!/usr/bin/env python3
"""Integration of performance profiling with CHATTA voice mode components."""

import asyncio
import functools
from typing import Any, Dict, Optional, Callable
from contextlib import asynccontextmanager

from .performance_profiler import (
    ProfileMode,
    OptimizationLevel,
    PerformanceProfiler,
    PerformanceOptimizer,
    get_profiler,
    get_optimizer,
    profile
)


class VoicePerformanceMonitor:
    """Performance monitoring for voice interactions."""
    
    def __init__(self):
        self.profiler = get_profiler()
        self.optimizer = get_optimizer()
        self.metrics_buffer = []
        self.realtime_metrics = {}
        
    @profile("voice.stt")
    async def profile_stt(self, audio_data: bytes) -> str:
        """Profile speech-to-text performance."""
        metrics = self.profiler.active_profiles.get(
            asyncio.current_task().get_name(), {}
        )
        
        # Track audio size
        if metrics:
            metrics.custom_metrics["audio_size_kb"] = len(audio_data) / 1024
            metrics.custom_metrics["estimated_duration_s"] = len(audio_data) / (16000 * 2)
        
        # Simulate STT (would be actual STT call)
        await asyncio.sleep(0.1)
        return "transcribed text"
    
    @profile("voice.tts")
    async def profile_tts(self, text: str) -> bytes:
        """Profile text-to-speech performance."""
        metrics = self.profiler.active_profiles.get(
            asyncio.current_task().get_name(), {}
        )
        
        # Track text complexity
        if metrics:
            metrics.custom_metrics["text_length"] = len(text)
            metrics.custom_metrics["word_count"] = len(text.split())
        
        # Simulate TTS (would be actual TTS call)
        await asyncio.sleep(0.1)
        return b"audio_data"
    
    @profile("voice.vad")
    def profile_vad(self, audio_chunk: bytes) -> bool:
        """Profile voice activity detection."""
        # Track in realtime metrics
        self.realtime_metrics["vad_calls"] = self.realtime_metrics.get("vad_calls", 0) + 1
        
        # Simulate VAD (would be actual VAD call)
        return len(audio_chunk) > 1000
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        report = self.profiler.generate_report()
        
        stats = {
            "total_duration_ms": report.total_duration * 1000,
            "total_memory_mb": report.total_memory / (1024 * 1024),
            "avg_cpu_percent": report.avg_cpu,
            "hotspots": [
                {"function": name, "time_ms": time * 1000}
                for name, time in report.hotspots[:5]
            ],
            "realtime": self.realtime_metrics,
            "recommendations": report.recommendations[:3]
        }
        
        return stats
    
    def optimize_for_latency(self):
        """Optimize settings for minimum latency."""
        self.optimizer.level = OptimizationLevel.AGGRESSIVE
        
        return {
            "chunk_size": 2048,
            "buffer_size": 8192,
            "sample_rate": 16000,
            "channels": 1,
            "vad_aggressiveness": 3,
            "streaming": True,
            "compression": "opus"
        }
    
    def optimize_for_quality(self):
        """Optimize settings for maximum quality."""
        self.optimizer.level = OptimizationLevel.BASIC
        
        return {
            "chunk_size": 8192,
            "buffer_size": 32768,
            "sample_rate": 48000,
            "channels": 2,
            "vad_aggressiveness": 1,
            "streaming": False,
            "compression": "flac"
        }
    
    def optimize_balanced(self):
        """Balanced optimization settings."""
        self.optimizer.level = OptimizationLevel.MODERATE
        
        return {
            "chunk_size": 4096,
            "buffer_size": 16384,
            "sample_rate": 24000,
            "channels": 1,
            "vad_aggressiveness": 2,
            "streaming": True,
            "compression": "aac"
        }


class AsyncProfiler:
    """Async-aware performance profiler."""
    
    def __init__(self, profiler: Optional[PerformanceProfiler] = None):
        self.profiler = profiler or get_profiler()
    
    def profile_async(self, name: str = None):
        """Decorator for profiling async functions."""
        def decorator(func: Callable) -> Callable:
            profile_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if self.profiler.mode == ProfileMode.DISABLED:
                    return await func(*args, **kwargs)
                
                with self.profiler.profile_context(profile_name) as metrics:
                    # Track async-specific metrics
                    metrics.custom_metrics["task_name"] = asyncio.current_task().get_name()
                    
                    result = await func(*args, **kwargs)
                    
                    # Check for event loop lag
                    loop = asyncio.get_event_loop()
                    if hasattr(loop, 'time'):
                        metrics.custom_metrics["loop_time"] = loop.time()
                    
                    return result
            
            return wrapper
        return decorator
    
    @asynccontextmanager
    async def profile_async_context(self, name: str):
        """Async context manager for profiling."""
        with self.profiler.profile_context(name) as metrics:
            # Track async context entry
            metrics.custom_metrics["context_type"] = "async"
            
            try:
                yield metrics
            finally:
                # Track async context exit
                metrics.custom_metrics["pending_tasks"] = len(asyncio.all_tasks())


class CacheOptimizer:
    """Cache optimization for voice mode."""
    
    def __init__(self, optimizer: Optional[PerformanceOptimizer] = None):
        self.optimizer = optimizer or get_optimizer()
        self._tts_cache = {}
        self._stt_cache = {}
        self._provider_cache = {}
    
    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "tts_entries": len(self._tts_cache),
            "stt_entries": len(self._stt_cache),
            "provider_entries": len(self._provider_cache),
            "total_size_mb": self._estimate_cache_size() / (1024 * 1024)
        }
    
    def _estimate_cache_size(self) -> int:
        """Estimate total cache size in bytes."""
        size = 0
        
        for cache in [self._tts_cache, self._stt_cache, self._provider_cache]:
            for key, value in cache.items():
                size += len(str(key)) + len(str(value))
        
        return size
    
    def cache_tts(self, text: str, voice: str, audio: bytes):
        """Cache TTS result."""
        if self.optimizer.level.value >= OptimizationLevel.MODERATE.value:
            key = (text, voice)
            self._tts_cache[key] = audio
            
            # Limit cache size
            max_size = 100 if self.optimizer.level == OptimizationLevel.AGGRESSIVE else 50
            if len(self._tts_cache) > max_size:
                # Remove oldest (simple FIFO for now)
                self._tts_cache.pop(next(iter(self._tts_cache)))
    
    def get_cached_tts(self, text: str, voice: str) -> Optional[bytes]:
        """Get cached TTS result."""
        if self.optimizer.level.value >= OptimizationLevel.MODERATE.value:
            return self._tts_cache.get((text, voice))
        return None
    
    def cache_stt(self, audio_hash: str, text: str):
        """Cache STT result."""
        if self.optimizer.level.value >= OptimizationLevel.MODERATE.value:
            self._stt_cache[audio_hash] = text
            
            # Limit cache size
            max_size = 50 if self.optimizer.level == OptimizationLevel.AGGRESSIVE else 25
            if len(self._stt_cache) > max_size:
                self._stt_cache.pop(next(iter(self._stt_cache)))
    
    def get_cached_stt(self, audio_hash: str) -> Optional[str]:
        """Get cached STT result."""
        if self.optimizer.level.value >= OptimizationLevel.MODERATE.value:
            return self._stt_cache.get(audio_hash)
        return None
    
    def clear_caches(self):
        """Clear all caches."""
        self._tts_cache.clear()
        self._stt_cache.clear()
        self._provider_cache.clear()


class LatencyOptimizer:
    """Latency optimization strategies."""
    
    def __init__(self):
        self.measurements = []
        self.targets = {
            "stt_latency_ms": 500,
            "tts_latency_ms": 200,
            "vad_latency_ms": 50,
            "total_latency_ms": 1000
        }
    
    def measure_latency(self, component: str, latency_ms: float):
        """Record latency measurement."""
        self.measurements.append({
            "component": component,
            "latency_ms": latency_ms,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        # Keep only recent measurements
        if len(self.measurements) > 1000:
            self.measurements = self.measurements[-500:]
    
    def get_optimization_suggestions(self) -> Dict[str, Any]:
        """Get latency optimization suggestions."""
        suggestions = {}
        
        # Analyze recent measurements
        if not self.measurements:
            return {"status": "no_data"}
        
        # Group by component
        by_component = {}
        for m in self.measurements:
            comp = m["component"]
            if comp not in by_component:
                by_component[comp] = []
            by_component[comp].append(m["latency_ms"])
        
        # Generate suggestions
        for component, latencies in by_component.items():
            avg_latency = sum(latencies) / len(latencies)
            target = self.targets.get(f"{component}_latency_ms", 100)
            
            if avg_latency > target * 1.5:
                suggestions[component] = {
                    "status": "critical",
                    "avg_ms": avg_latency,
                    "target_ms": target,
                    "suggestion": f"Optimize {component} - latency {avg_latency:.0f}ms exceeds target {target}ms"
                }
            elif avg_latency > target:
                suggestions[component] = {
                    "status": "warning",
                    "avg_ms": avg_latency,
                    "target_ms": target,
                    "suggestion": f"Monitor {component} - latency {avg_latency:.0f}ms above target {target}ms"
                }
            else:
                suggestions[component] = {
                    "status": "good",
                    "avg_ms": avg_latency,
                    "target_ms": target
                }
        
        return suggestions
    
    def apply_optimizations(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply latency optimizations to configuration."""
        optimized = config.copy()
        suggestions = self.get_optimization_suggestions()
        
        for component, info in suggestions.items():
            if info.get("status") == "critical":
                if component == "stt":
                    optimized["stt_streaming"] = True
                    optimized["stt_chunk_size"] = 2048
                elif component == "tts":
                    optimized["tts_streaming"] = True
                    optimized["tts_buffer_size"] = 4096
                elif component == "vad":
                    optimized["vad_mode"] = "aggressive"
                    optimized["vad_frame_ms"] = 10
        
        return optimized


# Integration with existing voice mode
def integrate_profiling(voice_mode_instance):
    """Integrate profiling with voice mode instance."""
    monitor = VoicePerformanceMonitor()
    async_profiler = AsyncProfiler()
    cache_optimizer = CacheOptimizer()
    latency_optimizer = LatencyOptimizer()
    
    # Wrap key methods
    original_stt = voice_mode_instance.speech_to_text
    original_tts = voice_mode_instance.text_to_speech
    
    @async_profiler.profile_async("voice.full_stt")
    async def profiled_stt(audio_data: bytes) -> str:
        # Check cache
        import hashlib
        audio_hash = hashlib.md5(audio_data).hexdigest()
        cached = cache_optimizer.get_cached_stt(audio_hash)
        if cached:
            return cached
        
        # Profile and execute
        start = asyncio.get_event_loop().time()
        result = await original_stt(audio_data)
        latency = (asyncio.get_event_loop().time() - start) * 1000
        
        # Record metrics
        latency_optimizer.measure_latency("stt", latency)
        cache_optimizer.cache_stt(audio_hash, result)
        
        return result
    
    @async_profiler.profile_async("voice.full_tts")
    async def profiled_tts(text: str, voice: str = "default") -> bytes:
        # Check cache
        cached = cache_optimizer.get_cached_tts(text, voice)
        if cached:
            return cached
        
        # Profile and execute
        start = asyncio.get_event_loop().time()
        result = await original_tts(text, voice)
        latency = (asyncio.get_event_loop().time() - start) * 1000
        
        # Record metrics
        latency_optimizer.measure_latency("tts", latency)
        cache_optimizer.cache_tts(text, voice, result)
        
        return result
    
    # Replace methods
    voice_mode_instance.speech_to_text = profiled_stt
    voice_mode_instance.text_to_speech = profiled_tts
    
    # Add performance tools
    voice_mode_instance.performance_monitor = monitor
    voice_mode_instance.cache_optimizer = cache_optimizer
    voice_mode_instance.latency_optimizer = latency_optimizer
    
    return voice_mode_instance