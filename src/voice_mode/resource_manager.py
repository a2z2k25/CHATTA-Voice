#!/usr/bin/env python3
"""Resource management and cleanup framework for voice mode."""

import asyncio
import threading
import weakref
import gc
import psutil
import tracemalloc
import time
import logging
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager, contextmanager
import atexit
import signal
import sys

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources to manage."""
    AUDIO_BUFFER = "audio_buffer"
    NETWORK_CONNECTION = "network_connection"
    FILE_HANDLE = "file_handle"
    THREAD_POOL = "thread_pool"
    PROCESS = "process"
    MEMORY_CACHE = "memory_cache"
    TEMP_FILE = "temp_file"
    LOCK = "lock"
    SEMAPHORE = "semaphore"
    EVENT_LOOP = "event_loop"


@dataclass
class ResourceMetrics:
    """Metrics for resource usage."""
    type: ResourceType
    count: int = 0
    bytes_used: int = 0
    peak_count: int = 0
    peak_bytes: int = 0
    total_allocated: int = 0
    total_freed: int = 0
    leaked: int = 0
    avg_lifetime: float = 0
    last_cleanup: float = field(default_factory=time.time)


@dataclass
class Resource:
    """Individual resource tracking."""
    id: str
    type: ResourceType
    ref: Any  # Weak reference to the actual resource
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    cleanup_callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceTracker:
    """Track and monitor resource usage."""
    
    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._metrics: Dict[ResourceType, ResourceMetrics] = {
            rtype: ResourceMetrics(type=rtype) for rtype in ResourceType
        }
        self._lock = threading.RLock()
        self._resource_id_counter = 0
        
        # Weak references for automatic cleanup
        self._weak_refs: Dict[str, weakref.ref] = {}
        
        # Track resource relationships
        self._dependencies: Dict[str, Set[str]] = {}
    
    def register_resource(self,
                          resource: Any,
                          resource_type: ResourceType,
                          size_bytes: int = 0,
                          cleanup_callback: Optional[Callable] = None,
                          metadata: Optional[Dict] = None) -> str:
        """Register a resource for tracking."""
        with self._lock:
            resource_id = f"{resource_type.value}_{self._resource_id_counter}"
            self._resource_id_counter += 1
            
            # Create weak reference
            try:
                weak_ref = weakref.ref(resource, 
                                       lambda ref: self._on_resource_deleted(resource_id))
                self._weak_refs[resource_id] = weak_ref
            except TypeError:
                # Some objects don't support weak references
                weak_ref = resource
            
            # Create resource entry
            res = Resource(
                id=resource_id,
                type=resource_type,
                ref=weak_ref,
                size_bytes=size_bytes,
                cleanup_callback=cleanup_callback,
                metadata=metadata or {}
            )
            
            self._resources[resource_id] = res
            
            # Update metrics
            metrics = self._metrics[resource_type]
            metrics.count += 1
            metrics.bytes_used += size_bytes
            metrics.total_allocated += 1
            metrics.peak_count = max(metrics.peak_count, metrics.count)
            metrics.peak_bytes = max(metrics.peak_bytes, metrics.bytes_used)
            
            logger.debug(f"Registered resource {resource_id}: {resource_type.value}")
            return resource_id
    
    def unregister_resource(self, resource_id: str):
        """Unregister a resource."""
        with self._lock:
            if resource_id not in self._resources:
                return
            
            res = self._resources[resource_id]
            
            # Update metrics
            metrics = self._metrics[res.type]
            metrics.count -= 1
            metrics.bytes_used -= res.size_bytes
            metrics.total_freed += 1
            
            # Update average lifetime
            lifetime = time.time() - res.created_at
            metrics.avg_lifetime = (
                (metrics.avg_lifetime * (metrics.total_freed - 1) + lifetime) /
                metrics.total_freed
            ) if metrics.total_freed > 0 else lifetime
            
            # Remove from tracking
            del self._resources[resource_id]
            self._weak_refs.pop(resource_id, None)
            self._dependencies.pop(resource_id, None)
            
            # Remove from other dependencies
            for deps in self._dependencies.values():
                deps.discard(resource_id)
            
            logger.debug(f"Unregistered resource {resource_id}")
    
    def _on_resource_deleted(self, resource_id: str):
        """Handle resource deletion by garbage collector."""
        logger.debug(f"Resource {resource_id} was garbage collected")
        self.unregister_resource(resource_id)
    
    def add_dependency(self, resource_id: str, depends_on: str):
        """Add resource dependency."""
        with self._lock:
            if resource_id not in self._dependencies:
                self._dependencies[resource_id] = set()
            self._dependencies[resource_id].add(depends_on)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get resource metrics."""
        with self._lock:
            return {
                rtype.value: {
                    "count": metrics.count,
                    "bytes_used": metrics.bytes_used,
                    "peak_count": metrics.peak_count,
                    "peak_bytes": metrics.peak_bytes,
                    "total_allocated": metrics.total_allocated,
                    "total_freed": metrics.total_freed,
                    "leaked": metrics.total_allocated - metrics.total_freed - metrics.count,
                    "avg_lifetime": metrics.avg_lifetime
                }
                for rtype, metrics in self._metrics.items()
                if metrics.total_allocated > 0
            }
    
    def find_leaks(self) -> List[str]:
        """Find potential resource leaks."""
        with self._lock:
            leaks = []
            current_time = time.time()
            
            for resource_id, res in self._resources.items():
                # Check if resource is old and unused
                age = current_time - res.created_at
                idle_time = current_time - res.last_accessed
                
                if age > 300 and idle_time > 60:  # 5 min old, 1 min idle
                    leaks.append(resource_id)
                    logger.warning(f"Potential leak: {resource_id} "
                                 f"(age: {age:.1f}s, idle: {idle_time:.1f}s)")
            
            return leaks


class ResourceCleaner:
    """Clean up resources automatically."""
    
    def __init__(self, tracker: ResourceTracker):
        self.tracker = tracker
        self._cleanup_tasks: List[asyncio.Task] = []
        self._cleanup_interval = 60  # seconds
        self._running = False
        self._lock = threading.Lock()
        
        # Cleanup strategies
        self._strategies: Dict[ResourceType, Callable] = {
            ResourceType.AUDIO_BUFFER: self._cleanup_audio_buffers,
            ResourceType.MEMORY_CACHE: self._cleanup_memory_cache,
            ResourceType.TEMP_FILE: self._cleanup_temp_files,
            ResourceType.NETWORK_CONNECTION: self._cleanup_connections,
        }
    
    async def start(self):
        """Start automatic cleanup."""
        self._running = True
        task = asyncio.create_task(self._cleanup_loop())
        self._cleanup_tasks.append(task)
        logger.info("Started resource cleaner")
    
    async def stop(self):
        """Stop automatic cleanup."""
        self._running = False
        for task in self._cleanup_tasks:
            task.cancel()
        await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)
        self._cleanup_tasks.clear()
        logger.info("Stopped resource cleaner")
    
    async def _cleanup_loop(self):
        """Main cleanup loop."""
        while self._running:
            try:
                await self.cleanup()
                await asyncio.sleep(self._cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(5)
    
    async def cleanup(self, force: bool = False):
        """Perform cleanup."""
        logger.debug("Starting resource cleanup")
        
        with self._lock:
            # Find and clean up leaks
            leaks = self.tracker.find_leaks()
            for resource_id in leaks:
                await self._cleanup_resource(resource_id, force)
            
            # Run type-specific cleanup strategies
            for resource_type, strategy in self._strategies.items():
                try:
                    await strategy(force)
                except Exception as e:
                    logger.error(f"Cleanup strategy failed for {resource_type}: {e}")
            
            # Force garbage collection if needed
            if force or self._should_gc():
                gc.collect()
                logger.debug(f"Forced GC, collected {gc.collect()} objects")
    
    async def _cleanup_resource(self, resource_id: str, force: bool = False):
        """Clean up a specific resource."""
        if resource_id not in self.tracker._resources:
            return
        
        res = self.tracker._resources[resource_id]
        
        # Check dependencies
        if not force and resource_id in self.tracker._dependencies:
            deps = self.tracker._dependencies[resource_id]
            if any(d in self.tracker._resources for d in deps):
                logger.debug(f"Skipping {resource_id}, has active dependencies")
                return
        
        # Run cleanup callback
        if res.cleanup_callback:
            try:
                if asyncio.iscoroutinefunction(res.cleanup_callback):
                    await res.cleanup_callback()
                else:
                    res.cleanup_callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed for {resource_id}: {e}")
        
        # Unregister resource
        self.tracker.unregister_resource(resource_id)
    
    async def _cleanup_audio_buffers(self, force: bool = False):
        """Clean up audio buffers."""
        threshold = 10 * 1024 * 1024  # 10MB
        metrics = self.tracker._metrics[ResourceType.AUDIO_BUFFER]
        
        if not force and metrics.bytes_used < threshold:
            return
        
        # Find old audio buffers
        current_time = time.time()
        to_clean = []
        
        for resource_id, res in self.tracker._resources.items():
            if res.type != ResourceType.AUDIO_BUFFER:
                continue
            
            age = current_time - res.last_accessed
            if force or age > 30:  # 30 seconds old
                to_clean.append(resource_id)
        
        for resource_id in to_clean:
            await self._cleanup_resource(resource_id, force)
        
        if to_clean:
            logger.info(f"Cleaned {len(to_clean)} audio buffers")
    
    async def _cleanup_memory_cache(self, force: bool = False):
        """Clean up memory caches."""
        threshold = 50 * 1024 * 1024  # 50MB
        metrics = self.tracker._metrics[ResourceType.MEMORY_CACHE]
        
        if not force and metrics.bytes_used < threshold:
            return
        
        # Find least recently used caches
        caches = [
            (res.last_accessed, res.id, res)
            for res in self.tracker._resources.values()
            if res.type == ResourceType.MEMORY_CACHE
        ]
        caches.sort()
        
        # Clean up oldest 20%
        to_clean = int(len(caches) * 0.2) if not force else len(caches)
        
        for _, resource_id, _ in caches[:to_clean]:
            await self._cleanup_resource(resource_id, force)
        
        if to_clean:
            logger.info(f"Cleaned {to_clean} cache entries")
    
    async def _cleanup_temp_files(self, force: bool = False):
        """Clean up temporary files."""
        import os
        import tempfile
        
        for resource_id, res in list(self.tracker._resources.items()):
            if res.type != ResourceType.TEMP_FILE:
                continue
            
            filepath = res.metadata.get("path")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.debug(f"Removed temp file: {filepath}")
                except Exception as e:
                    logger.error(f"Failed to remove temp file {filepath}: {e}")
            
            await self._cleanup_resource(resource_id, force)
    
    async def _cleanup_connections(self, force: bool = False):
        """Clean up network connections."""
        current_time = time.time()
        
        for resource_id, res in list(self.tracker._resources.items()):
            if res.type != ResourceType.NETWORK_CONNECTION:
                continue
            
            idle_time = current_time - res.last_accessed
            if force or idle_time > 120:  # 2 minutes idle
                await self._cleanup_resource(resource_id, force)
    
    def _should_gc(self) -> bool:
        """Check if garbage collection should run."""
        # Get memory usage
        process = psutil.Process()
        mem_info = process.memory_info()
        
        # Run GC if memory usage is high
        return mem_info.rss > 500 * 1024 * 1024  # 500MB


class ResourceManager:
    """Main resource management system."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.tracker = ResourceTracker()
        self.cleaner = ResourceCleaner(self.tracker)
        self._pools: Dict[str, Any] = {}
        self._shutdown_handlers: List[Callable] = []
        self._initialized = True
        
        # Register shutdown handlers
        atexit.register(self.shutdown)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    @contextmanager
    def managed_resource(self,
                        resource: Any,
                        resource_type: ResourceType,
                        size_bytes: int = 0,
                        cleanup: Optional[Callable] = None):
        """Context manager for resource management."""
        resource_id = self.tracker.register_resource(
            resource, resource_type, size_bytes, cleanup
        )
        try:
            yield resource
        finally:
            self.tracker.unregister_resource(resource_id)
            if cleanup:
                try:
                    cleanup()
                except Exception as e:
                    logger.error(f"Cleanup failed: {e}")
    
    @asynccontextmanager
    async def async_managed_resource(self,
                                    resource: Any,
                                    resource_type: ResourceType,
                                    size_bytes: int = 0,
                                    cleanup: Optional[Callable] = None):
        """Async context manager for resource management."""
        resource_id = self.tracker.register_resource(
            resource, resource_type, size_bytes, cleanup
        )
        try:
            yield resource
        finally:
            if cleanup:
                try:
                    if asyncio.iscoroutinefunction(cleanup):
                        await cleanup()
                    else:
                        cleanup()
                except Exception as e:
                    logger.error(f"Cleanup failed: {e}")
            self.tracker.unregister_resource(resource_id)
    
    async def start(self):
        """Start resource management."""
        await self.cleaner.start()
        logger.info("Resource manager started")
    
    async def stop(self):
        """Stop resource management."""
        await self.cleaner.stop()
        logger.info("Resource manager stopped")
    
    def register_shutdown_handler(self, handler: Callable):
        """Register shutdown handler."""
        self._shutdown_handlers.append(handler)
    
    def shutdown(self):
        """Shutdown and clean up all resources."""
        logger.info("Shutting down resource manager")
        
        # Run shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Shutdown handler failed: {e}")
        
        # Force cleanup
        asyncio.run(self.cleaner.cleanup(force=True))
        
        # Clear all resources
        self.tracker._resources.clear()
        self.tracker._weak_refs.clear()
        self.tracker._dependencies.clear()
        
        # Stop memory tracking
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        
        logger.info("Resource manager shutdown complete")
    
    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get memory usage snapshot."""
        process = psutil.Process()
        mem_info = process.memory_info()
        
        # Only take tracemalloc snapshot if it's tracing
        top_allocations = []
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')[:10]
            top_allocations = [
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size": stat.size,
                    "count": stat.count
                }
                for stat in top_stats
            ]
        
        return {
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "percent": process.memory_percent(),
            "top_allocations": top_allocations,
            "resource_metrics": self.tracker.get_metrics()
        }
    
    def optimize_memory(self):
        """Optimize memory usage."""
        # Force garbage collection
        gc.collect(2)  # Full collection
        
        # Compact memory if possible
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
        except:
            pass  # Not available on all platforms
        
        logger.info("Memory optimization complete")


# Global instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# Decorators for automatic resource management
def with_resource_tracking(resource_type: ResourceType, 
                          size_bytes: int = 0,
                          cleanup: Optional[Callable] = None):
    """Decorator for automatic resource tracking."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_resource_manager()
            result = func(*args, **kwargs)
            
            if result is not None:
                manager.tracker.register_resource(
                    result, resource_type, size_bytes, cleanup
                )
            
            return result
        return wrapper
    return decorator


def with_async_resource_tracking(resource_type: ResourceType,
                                size_bytes: int = 0,
                                cleanup: Optional[Callable] = None):
    """Async decorator for automatic resource tracking."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_resource_manager()
            result = await func(*args, **kwargs)
            
            if result is not None:
                manager.tracker.register_resource(
                    result, resource_type, size_bytes, cleanup
                )
            
            return result
        return wrapper
    return decorator


# Export main components
__all__ = [
    "ResourceType",
    "ResourceMetrics",
    "Resource",
    "ResourceTracker",
    "ResourceCleaner",
    "ResourceManager",
    "get_resource_manager",
    "with_resource_tracking",
    "with_async_resource_tracking"
]